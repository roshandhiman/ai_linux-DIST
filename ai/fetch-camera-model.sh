#!/usr/bin/env bash
# Fetch verified OpenCV Zoo and Megvii camera models (Apache-2.0).
set -euo pipefail
dest="$(realpath -m -- "${1:?Usage: fetch-camera-model.sh <new-directory>}")"
[[ ! -e "$dest" ]] || { printf '%s already exists\n' "$dest" >&2; exit 1; }
stage="$(mktemp -d "$(dirname -- "$dest")/.mineos-camera.XXXXXXXX")"
trap 'rm -rf -- "$stage"' EXIT
repo=opencv/opencv_zoo
revision=48b10fa505aeb51fbd127fc60a5c660040e823b7
path=models/object_detection_nanodet
curl -fsSL --retry 2 --connect-timeout 15 --max-time 120 \
    "https://media.githubusercontent.com/media/$repo/$revision/$path/object_detection_nanodet_2022nov.onnx" \
    -o "$stage/nanodet.onnx"
curl -fsSL --retry 2 --connect-timeout 15 --max-time 120 \
    "https://media.githubusercontent.com/media/$repo/$revision/models/palm_detection_mediapipe/palm_detection_mediapipe_2023feb.onnx" \
    -o "$stage/palm.onnx"
curl -fsSL --retry 2 --connect-timeout 15 --max-time 120 \
    "https://media.githubusercontent.com/media/$repo/$revision/models/pose_estimation_mediapipe/pose_estimation_mediapipe_2023mar.onnx" \
    -o "$stage/pose.onnx"
curl -fsSL --retry 2 --connect-timeout 15 --max-time 120 \
    "https://raw.githubusercontent.com/$repo/$revision/models/pose_estimation_mediapipe/LICENSE" \
    -o "$stage/MediaPipe-Pose-LICENSE"
curl -fsSL --retry 2 --connect-timeout 15 --max-time 120 \
    "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx" \
    -o "$stage/yolox-nano.onnx"
curl -fsSL --retry 2 --connect-timeout 15 --max-time 120 \
    "https://raw.githubusercontent.com/Megvii-BaseDetection/YOLOX/0.1.1rc0/LICENSE" \
    -o "$stage/YOLOX-LICENSE"
curl -fsSL --retry 2 --connect-timeout 15 --max-time 120 \
    "https://raw.githubusercontent.com/$repo/$revision/$path/LICENSE" -o "$stage/NanoDet-LICENSE"
(
    cd -- "$stage"
    sha256sum -c <<'SUMS'
4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186  nanodet.onnx
78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c  palm.onnx
9d89c599319a18fb7d2e28451a883476164543182bafca5f09eb2cf767ed2f3f  pose.onnx
58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd  MediaPipe-Pose-LICENSE
c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d  yolox-nano.onnx
577c03d505ec80f667ebf96ebd0cc4f6825c817ca1088ee348c48aaabd51bd92  YOLOX-LICENSE
cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30  NanoDet-LICENSE
SUMS
)
mv -T --no-clobber "$stage" "$dest"
test ! -d "$stage"
