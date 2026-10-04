#!/usr/bin/env bash
# Serve the base model plus every saved epoch adapter of a run, with the same flags as the baseline runs plus LoRA.
#   bash scripts/serve_adapters.sh runs/ft1
# Optional extra vLLM flags through EXTRA, e.g. EXTRA='--speculative-config {"method":"ngram","num_speculative_tokens":5,"prompt_lookup_max":4,"prompt_lookup_min":2}'
# Names: the base model stays `gemma` (the judge uses it); the adapters are ft1, ft2, ft3 = epoch_1, epoch_2, epoch_3.
set -e
RUN="$(realpath "${1:?path to a run folder, e.g. runs/ft1}")"
MODULES=""
for e in 1 2 3; do
  if [ -f "$RUN/epoch_$e/adapter_config.json" ]; then MODULES="$MODULES ft$e=$RUN/epoch_$e"; fi
done
[ -n "$MODULES" ] || { echo "no epoch_N/adapter_config.json under $RUN"; exit 1; }
echo "serving adapters:$MODULES"
source /workspace/venv-vllm/bin/activate
export VLLM_USE_FLASHINFER_SAMPLER=0
vllm serve /workspace/models/gemma-4-12B-qat-w4a16-ct --served-model-name gemma \
  --enable-lora --lora-modules $MODULES --max-lora-rank 16 \
  --max-model-len 16384 --gpu-memory-utilization 0.90 --port 8000 $EXTRA
