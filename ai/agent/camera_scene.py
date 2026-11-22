"""Run Florence-2 object detection on a local frame using pinned ONNX weights."""

import json
from pathlib import Path
import re

import cv2
import numpy as np

MODEL_DIR = Path("/usr/share/mineos/models/camera/florence")
MODEL_PARTS = (
    "vision_encoder_uint8.onnx", "embed_tokens_int8.onnx",
    "encoder_model_int8.onnx", "decoder_model_merged_int8.onnx",
)
TOKENIZER_FILE = "tokenizer.json"
# BART tokens for "Locate the objects in the image, with their descriptions."
TASK_IDS = np.array([[0, 574, 22486, 5, 8720, 11, 5, 2274, 6, 19, 49, 24173, 4, 2]], dtype=np.int64)
SPECIAL = {0, 1, 2}
COLORS = {"black", "blue", "brown", "gray", "green", "grey", "orange", "pink", "purple", "red", "white", "yellow"}
IMAGE_MEAN = np.array([.485, .456, .406], dtype=np.float32)
IMAGE_STD = np.array([.229, .224, .225], dtype=np.float32)


def available(directory=MODEL_DIR):
    return ((directory / TOKENIZER_FILE).is_file()
            and all((directory / part).is_file() for part in MODEL_PARTS))


class Labels:
    def __init__(self, directory):
        tokenizer = json.loads((directory / TOKENIZER_FILE).read_text())
        self.tokens = {index: token for token, index in tokenizer["model"]["vocab"].items()}
        self.locations = {
            token["id"]: int(token["content"][5:-1])
            for token in tokenizer["added_tokens"] if token["content"].startswith("<loc_")
        }
        # The model's byte-level BPE represents whitespace and UTF-8 with reversible characters.
        ascii_bytes = [*range(33, 127), *range(161, 173), *range(174, 256)]
        remaining = sorted(set(range(256)) - set(ascii_bytes))
        self.bytes = {chr(code): byte for code, byte in
                      zip(ascii_bytes + list(range(256, 256 + len(remaining))), ascii_bytes + remaining)}

    def decode(self, tokens):
        def as_bytes(token):
            return bytes(self.bytes[c] for c in token if c in self.bytes)

        pieces = [as_bytes(token) for token in tokens]
        if len(pieces) > 2 and pieces[0].strip().decode("ascii", "ignore").lower() in COLORS:
            if pieces[1].islower() and not pieces[1].startswith(b" "):
                pieces.insert(1, b" ")
        return b"".join(pieces).decode("utf-8", "replace").strip()

    def boxes(self, tokens, size):
        width, height = size
        text, coordinates, boxes = [], [], []
        label = ""
        for token in tokens:
            if token in SPECIAL:
                continue
            if token not in self.locations:
                text.append(self.tokens.get(token, ""))
                coordinates.clear()
                continue
            if text:
                label = self.decode(text)
                text.clear()
            coordinates.append(self.locations[token])
            if len(coordinates) != 4:
                continue
            x0, y0, x1, y1 = ((coord + .5) / 1000 * axis
                              for coord, axis in zip(coordinates, (width, height, width, height)))
            coordinates.clear()
            if label and x1 - x0 >= 6 and y1 - y0 >= 6:
                if label.casefold() in {"man", "woman", "boy", "girl", "people"}:
                    label = "person"
                elif label.casefold() in {"phone", "mobile phone", "smartphone", "cellphone"}:
                    label = "cell phone"
                boxes.append((label[:64], (x0, y0, x1 - x0, y1 - y0)))
        return boxes


class SceneDetector:
    def __init__(self, directory=MODEL_DIR):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 3
        opts.inter_op_num_threads = 1
        opts.log_severity_level = 3
        opts.add_session_config_entry("session.intra_op.allow_spinning", "0")
        self.vision, self.embed, self.encoder, self.decoder = (
            ort.InferenceSession(str(directory / part), opts, providers=["CPUExecutionProvider"])
            for part in MODEL_PARTS
        )
        self.labels = Labels(directory)
        self.text = self.embed.run(None, {"input_ids": TASK_IDS})[0]
        self.cache_inputs = {item.name: item.shape for item in self.decoder.get_inputs()
                             if item.name.startswith("past_key_values.")}
        self.cache_outputs = [item.name for item in self.decoder.get_outputs() if item.name.startswith("present.")]
        self.outputs = ["logits", *self.cache_outputs]

    def detect(self, frame):
        height, width = frame.shape[:2]
        rgb = cv2.resize(frame, (768, 768), interpolation=cv2.INTER_CUBIC)[:, :, ::-1]
        pixels = ((rgb.astype(np.float32) / 255 - IMAGE_MEAN) / IMAGE_STD).transpose(2, 0, 1)
        vision = self.vision.run(None, {"pixel_values": np.ascontiguousarray(pixels[None])})[0]
        embeds = np.concatenate((vision, self.text), axis=1)
        mask = np.ones(embeds.shape[:2], dtype=np.int64)
        encoded = self.encoder.run(None, {"inputs_embeds": embeds, "attention_mask": mask})[0]

        cache = {
            name: np.empty((1, int(shape[1]), 0, int(shape[3])), dtype=np.float32)
            for name, shape in self.cache_inputs.items()
        }
        tokens = []
        last = 2
        for step in range(96):
            embedding = self.embed.run(None, {"input_ids": np.array([[last]], dtype=np.int64)})[0]
            inputs = {"inputs_embeds": embedding, "encoder_attention_mask": mask,
                      "encoder_hidden_states": encoded, "use_cache_branch": np.array([step > 0])}
            result = self.decoder.run(self.outputs, inputs | cache)
            last = int(result[0][0, -1].argmax())
            if last == 2:
                break
            tokens.append(last)
            for name, value in zip(self.cache_outputs, result[1:]):
                if step == 0 or ".decoder." in name:
                    cache[name.replace("present.", "past_key_values.", 1)] = value
        return self.labels.boxes(tokens, (width, height))


def fingerprint(frame):
    return cv2.resize(frame, (48, 32), interpolation=cv2.INTER_AREA)


def scene_distance(before, after):
    return cv2.absdiff(before, after).mean()


def box_iou(a, b):
    x1, y1, w1, h1 = a
    x2, y2, w2, h2 = b
    width = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
    height = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
    intersection = width * height
    return intersection / max(1, w1 * h1 + w2 * h2 - intersection)


def merge_boxes(quick, detailed):
    merged = list(quick)
    matched = set()
    for label, box in detailed:
        if label.casefold() in {"object", "thing", "item", "background"}:
            continue
        overlap, index = max(((box_iou(old_box, box), i) for i, (_, old_box) in enumerate(quick)),
                             default=(0, -1))
        if overlap >= .55:
            if index not in matched:
                current, current_box = merged[index]
                if current != "person" and re.search(rf"\b{re.escape(current)}\b", label, re.IGNORECASE):
                    merged[index] = (label, current_box)
                matched.add(index)
        elif not any(other.casefold() == label.casefold() and box_iou(box, other_box) >= .4
                     for other, other_box in merged):
            merged.append((label, box))
    return merged
