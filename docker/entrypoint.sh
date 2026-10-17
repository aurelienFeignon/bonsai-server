#!/bin/sh
set -eu
# Arguments supplémentaires transmis comme tableau, sans eval ni shell splitting.
set -- --model "/models/${MODEL_FILE:-Ternary-Bonsai-2-27B-PQ2_0.gguf}" \
 --alias "${BONSAI_MODEL_ALIAS:-bonsai2-27b-pq2}" --host 0.0.0.0 --port 53110 \
 --ctx-size "${BONSAI_CTX_SIZE:-4096}" --parallel "${BONSAI_PARALLEL:-1}" \
 --n-gpu-layers "${BONSAI_GPU_LAYERS:-999}" \
 --batch-size "${BONSAI_BATCH_SIZE:-128}" --ubatch-size "${BONSAI_UBATCH_SIZE:-128}" \
 --threads "${BONSAI_THREADS:-4}" --flash-attn "${BONSAI_FLASH_ATTN:-on}" \
 --cache-type-k "${BONSAI_CACHE_TYPE_K:-f16}" --cache-type-v "${BONSAI_CACHE_TYPE_V:-f16}" \
 --reasoning "${BONSAI_REASONING:-off}" --reasoning-budget "${BONSAI_REASONING_BUDGET:-0}" \
 --reasoning-format "${BONSAI_REASONING_FORMAT:-deepseek}" \
 --temp "${BONSAI_TEMPERATURE:-0.1}" --top-p "${BONSAI_TOP_P:-0.95}" \
 --top-k "${BONSAI_TOP_K:-20}" --min-p "${BONSAI_MIN_P:-0.05}" \
 --n-predict "${BONSAI_MAX_TOKENS:-600}" \
 --cors-origins "${BONSAI_CORS_ORIGINS:-localhost}" --no-ui "$@"
# auto uses the GGUF's native template. Explicit templates remain selectable.
if [ "${BONSAI_CHAT_TEMPLATE:-auto}" != auto ]; then
 set -- --chat-template "$BONSAI_CHAT_TEMPLATE" "$@"
fi
if [ -n "${BONSAI_CHAT_TEMPLATE_KWARGS:-}" ]; then
 set -- --chat-template-kwargs "$BONSAI_CHAT_TEMPLATE_KWARGS" "$@"
fi
case "${BONSAI_JINJA:-true}" in
 true) set -- --jinja "$@";; false) set -- --no-jinja "$@";;
 *) echo 'BONSAI_JINJA must be true or false' >&2; exit 2;;
esac
case "${BONSAI_CONTEXT_SHIFT:-false}" in
 true) set -- --context-shift "$@";; false) set -- --no-context-shift "$@";;
 *) echo 'BONSAI_CONTEXT_SHIFT must be true or false' >&2; exit 2;;
esac
: "${LLAMA_API_KEY:?A non-empty BONSAI_API_KEY is required}"
exec /opt/bonsai/llama-server "$@"
