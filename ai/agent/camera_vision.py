"""Fast object and hand detection for MineOS Camera."""

from pathlib import Path

import cv2
import numpy as np

COCO = (
    "person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,"
    "fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,"
    "elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,"
    "skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,"
    "tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,"
    "sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,"
    "potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,"
    "cell phone,microwave,oven,toaster,sink,refrigerator,book,clock,vase,scissors,"
    "teddy bear,hair drier,toothbrush"
).split(",")
MODEL = Path("/usr/share/mineos/models/camera/nanodet.onnx")
PALM_MODEL = MODEL.with_name("palm.onnx")
DETAIL_MODEL = MODEL.with_name("yolox-nano.onnx")
MEAN = np.array([103.53, 116.28, 123.675], dtype=np.float32)
STD = np.array([57.375, 57.12, 58.395], dtype=np.float32)
SIZE = 416


class Detector:
    """Decode the OpenCV Zoo NanoDet Plus model's anchor and distance outputs."""

    def __init__(self):
        self.network = cv2.dnn.readNet(str(MODEL))
        self.layers = self.network.getUnconnectedOutLayersNames()
        self.anchors = {}
        for stride in (8, 16, 32, 64):
            coordinates = np.arange(SIZE // stride) * stride + (stride - 1) / 2
            grid = np.column_stack([axis.ravel() for axis in np.meshgrid(coordinates, coordinates)])
            self.anchors[len(grid)] = (stride, grid)

    def detect(self, frame, threshold=.35):
        height, width = frame.shape[:2]
        scale = SIZE / max(width, height)
        w, h = max(1, round(width * scale)), max(1, round(height * scale))
        x, y = (SIZE - w) // 2, (SIZE - h) // 2
        image = np.empty((SIZE, SIZE, 3), dtype=np.float32)
        image[:] = MEAN
        image[y:y + h, x:x + w] = cv2.resize(frame, (w, h))
        self.network.setInput(cv2.dnn.blobFromImage((image - MEAN) / STD))
        outputs = [np.asarray(layer).reshape(-1, layer.shape[-1])
                   for layer in self.network.forward(self.layers)]
        scores = {len(layer): layer for layer in outputs if layer.shape[-1] == len(COCO)}
        boxes, confidences, labels = [], [], []
        for regression in (layer for layer in outputs if layer.shape[-1] == 32):
            stride, grid = self.anchors[len(regression)]
            score = scores[len(regression)]
            best = score.max(axis=1)
            keep = best >= threshold
            if not keep.any():
                continue
            distances = regression[keep].reshape(-1, 4, 8)
            weights = np.exp(distances - distances.max(axis=2, keepdims=True))
            offsets = (weights @ np.arange(8) / weights.sum(axis=2)) * stride
            centers = grid[keep]
            corner1 = np.maximum(centers - offsets[:, :2], (x, y))
            corner2 = np.minimum(centers + offsets[:, 2:], (x + w, y + h))
            rects = np.column_stack(((corner1 - (x, y)) / scale, (corner2 - corner1) / scale))
            valid = (rects[:, 2:] >= 2).all(axis=1)
            boxes.extend(rects[valid].tolist())
            confidences.extend(best[keep][valid].tolist())
            labels.extend(score[keep][valid].argmax(axis=1).tolist())
        if not boxes:
            return []
        chosen = cv2.dnn.NMSBoxesBatched(boxes, confidences, labels, threshold, 0.5)
        return [(COCO[labels[i]], boxes[i]) for i in chosen]


class DetailDetector:
    """YOLOX-Nano refines object labels in a crop around a hand."""

    def __init__(self):
        self.network = cv2.dnn.readNet(str(DETAIL_MODEL))
        grids, strides = [], []
        for stride in (8, 16, 32):
            axis = np.arange(SIZE // stride)
            grid = np.column_stack([values.ravel() for values in np.meshgrid(axis, axis)])
            grids.append(grid)
            strides.append(np.full((len(grid), 1), stride))
        self.grid = np.concatenate(grids)
        self.strides = np.concatenate(strides)

    def detect(self, frame, threshold=.4):
        height, width = frame.shape[:2]
        scale = SIZE / max(width, height)
        w, h = max(1, int(width * scale)), max(1, int(height * scale))
        canvas = np.full((SIZE, SIZE, 3), 114, dtype=np.uint8)
        canvas[:h, :w] = cv2.resize(frame, (w, h))
        self.network.setInput(cv2.dnn.blobFromImage(canvas))
        output = self.network.forward()[0]
        scores = output[:, 4:5] * output[:, 5:]
        best = scores.max(axis=1)
        mask = best >= threshold
        centers = (output[mask, :2] + self.grid[mask]) * self.strides[mask]
        dimensions = np.exp(output[mask, 2:4]) * self.strides[mask]
        xy1 = np.maximum(0, centers - dimensions / 2)
        xy2 = np.minimum((w, h), centers + dimensions / 2)
        boxes = np.column_stack((xy1, xy2 - xy1)) / scale
        valid = (boxes[:, 2:] >= 2).all(axis=1)
        boxes = boxes[valid].tolist()
        labels = scores[mask][valid].argmax(axis=1)
        selected = cv2.dnn.NMSBoxesBatched(boxes, best[mask][valid].tolist(), labels.tolist(), threshold, .45)
        return [(COCO[labels[i]], boxes[i]) for i in selected]


class PalmDetector:
    """Find hand regions with OpenCV Zoo's MediaPipe palm detector."""

    size = 192

    def __init__(self):
        self.network = cv2.dnn.readNet(str(PALM_MODEL))
        self.layers = self.network.getUnconnectedOutLayersNames()
        anchors = []
        for cells, repeats in ((24, 2), (12, 6)):
            points = (np.arange(cells) + .5) * self.size / cells
            grid = np.column_stack([axis.ravel() for axis in np.meshgrid(points, points)])
            anchors.append(np.repeat(grid, repeats, axis=0))
        self.anchors = np.concatenate(anchors)

    def detect(self, frame):
        height, width = frame.shape[:2]
        scale = self.size / max(width, height)
        w, h = max(1, round(width * scale)), max(1, round(height * scale))
        x, y = (self.size - w) // 2, (self.size - h) // 2
        image = np.zeros((1, self.size, self.size, 3), dtype=np.float32)
        image[0, y:y + h, x:x + w] = cv2.resize(frame, (w, h))[:, :, ::-1] / 255
        self.network.setInput(image)
        outputs = {layer.shape[-1]: layer[0] for layer in self.network.forward(self.layers)}
        scores = 1 / (1 + np.exp(-np.clip(outputs[1][:, 0], -30, 30)))
        mask = scores >= .65
        delta = outputs[18][mask]
        dimensions = delta[:, 2:4]
        corner = self.anchors[mask] + delta[:, :2] - dimensions / 2 - (x, y)
        boxes = np.column_stack((corner, dimensions)) / scale
        selected = cv2.dnn.NMSBoxes(boxes.tolist(), scores[mask].tolist(), .65, .3)
        return [boxes[i] for i in selected]


PORTABLE_OBJECTS = {
    "apple", "banana", "baseball bat", "baseball glove", "book", "bottle", "bowl",
    "carrot", "cell phone", "cup", "donut", "fork", "frisbee", "hair drier", "knife",
    "mouse", "orange", "remote", "sandwich", "scissors", "sports ball", "spoon",
    "teddy bear", "tennis racket", "toothbrush", "umbrella", "wine glass",
}


def overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    area = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))
    return area / max(1, min(aw * ah, bw * bh))


def palm_regions(hands):
    return [(x + w / 2, y + h / 3, max(36, min(130, 1.35 * max(w, h))))
            for x, y, w, h in hands]


def add_hand_objects(detector, frame, boxes, regions):
    height, width = frame.shape[:2]
    tried = []
    for x, y, reach in regions[:3]:
        x0, y0 = max(0, int(x - reach)), max(0, int(y - 2.05 * reach))
        x1, y1 = min(width, int(x + reach * .8)), min(height, int(y + reach))
        rect = (x0, y0, x1 - x0, y1 - y0)
        if min(rect[2:]) < 32 or any(overlaps(rect, other) > .75 for other in tried):
            continue
        tried.append(rect)
        if any(label in PORTABLE_OBJECTS and overlaps(rect, box) > .65 for label, box in boxes):
            continue
        details = detector.detect(frame[y0:y1, x0:x1], threshold=.4)
        details.sort(key=lambda detection: detection[1][2] * detection[1][3], reverse=True)
        for label, (bx, by, bw, bh) in details:
            if label not in PORTABLE_OBJECTS:
                continue
            box = (x0 + bx, y0 + by, bw, bh)
            dx = max(box[0] - x, 0, x - box[0] - bw)
            dy = max(box[1] - y, 0, y - box[1] - bh)
            if np.hypot(dx, dy) > reach * .65:
                continue
            if not any(other_label in PORTABLE_OBJECTS and overlaps(box, other_box) > .55
                       for other_label, other_box in boxes):
                boxes.append((label, box))
