#!/usr/bin/env bash
set -euo pipefail

MODELS_DIR="${HOME}/.local/share/ai/models"
mkdir -p "${MODELS_DIR}"

MODEL_NAME="${1:-qwen2.5-1.5b}"

case "${MODEL_NAME}" in
    "qwen2.5-1.5b"|"default")
        URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
        FILE="${MODELS_DIR}/qwen2.5-1.5b-instruct-q4_k_m.gguf"
        ;;
    "qwen2.5-0.5b"|"nano")
        URL="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
        FILE="${MODELS_DIR}/qwen2.5-0.5b-instruct-q4_k_m.gguf"
        ;;
    "llama3.2-1b")
        URL="https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
        FILE="${MODELS_DIR}/llama-3.2-1b-instruct-q4_k_m.gguf"
        ;;
    *)
        exit 1
        ;;
esac

if [[ ! -f "${FILE}" ]]; then
    curl -L --progress-bar -o "${FILE}" "${URL}"
fi

ln -sf "${FILE}" "${MODELS_DIR}/active.gguf"
