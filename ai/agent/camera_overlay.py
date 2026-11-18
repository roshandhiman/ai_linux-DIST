"""Bounded, offline object labels and pose estimation for the camera preview."""

from dataclasses import dataclass
import logging

import cv2
import numpy as np

from camera_vision import (DETAIL_MODEL, MODEL, PALM_MODEL, DetailDetector,
                           Detector, PalmDetector, add_hand_objects, palm_regions)

POSE_MODEL = MODEL.with_name("pose.onnx")
LOG = logging.getLogger(__name__)
POSE_LINKS = (
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28),
    (27, 31), (28, 32),
)


@dataclass
class Overlay:
    boxes: list
    poses: list
    size: tuple


class PoseDetector:
    size = 256

    def __init__(self):
        self.network = cv2.dnn.readNet(str(POSE_MODEL))
        self.layers = self.network.getUnconnectedOutLayersNames()

    def detect(self, frame, box):
        x, y, w, h = box
        side = max(w, h) * 1.3
        origin = np.array([x + w / 2 - side / 2, y + h / 2 - side / 2])
        scale = self.size / side
        transform = np.column_stack((np.eye(2) * scale, -origin * scale))
        crop = cv2.warpAffine(frame, transform, (self.size, self.size))
        blob = crop[None, :, :, ::-1].astype(np.float32) / 255
        self.network.setInput(blob)
        outputs = {layer.size: layer for layer in self.network.forward(self.layers)}
        if outputs[1].item() < .6:
            return None
        landmarks = outputs[195].reshape(39, 5)[:33].copy()
        points = landmarks[:, :2] / scale + origin
        visible = (landmarks[:, 3:] >= 0).all(axis=1)
        visible &= ((points >= 0) & (points < frame.shape[1::-1])).all(axis=1)
        return [(float(px), float(py)) if valid else None
                for (px, py), valid in zip(points, visible)]


class LiveVision:
    def __init__(self):
        self.detector = None
        self.pose = None
        self.palm = None
        self.detail = None
        self.pose_failed = False
        self.palm_failed = False

    def inspect(self, frame):
        if self.detector is None:
            self.detector = Detector()
        boxes = self.detector.detect(frame)
        people = sorted([box for label, box in boxes if label == "person"],
                        key=lambda box: box[2] * box[3], reverse=True)
        poses = self.person_poses(frame, people[:3])
        self.look_near_hands(frame, boxes, poses)
        return Overlay(boxes, poses, frame.shape[1::-1])

    def person_poses(self, frame, people):
        if not people or self.pose_failed or not POSE_MODEL.is_file():
            return []
        try:
            if self.pose is None:
                self.pose = PoseDetector()
            return [points for box in people if min(box[2:]) >= 36
                    if (points := self.pose.detect(frame, box))]
        except cv2.error:
            LOG.exception("Could not run the pose model")
            self.pose_failed = True
            return []

    def look_near_hands(self, frame, boxes, poses):
        regions = []
        if not self.palm_failed and PALM_MODEL.is_file():
            try:
                if self.palm is None:
                    self.palm = PalmDetector()
                regions.extend(palm_regions(self.palm.detect(frame)))
            except cv2.error:
                LOG.exception("Could not run the palm model")
                self.palm_failed = True
        for points in poses:
            for shoulder, elbow, wrist in ((11, 13, 15), (12, 14, 16)):
                if points[wrist] and (points[elbow] or points[shoulder]):
                    x, y = points[wrist]
                    joint_x, joint_y = points[elbow] or points[shoulder]
                    reach = max(39, min(135, np.hypot(x - joint_x, y - joint_y) * 1.25))
                    regions.append((x, y, reach))

        if regions:
            if self.detail is None and DETAIL_MODEL.is_file():
                self.detail = DetailDetector()
            add_hand_objects(self.detail or self.detector, frame, boxes, regions)
