#!/usr/bin/env bash
# Run the frozen evaluation pipeline on one served adapter and on the base model with the same settings, then compare them.
#   bash scripts/eval_adapter.sh ft2 _s2        # adapter name (ft1|ft2|ft3), tag appended to the system names
# Systems: base_v4<TAG> (model gemma) and finetuned_epoch<N><TAG> (model ft<N>). The base run is skipped if its judge file already exists.
# Pipeline folder: /workspace/pipeline/pipeline (set PIPE=... if elsewhere). The judge is always the base model `gemma`.
set -e
AD="${1:?adapter name: ft1, ft2 or ft3}"
TAG="${2:-}"
PIPE="${PIPE:-/workspace/pipeline/pipeline}"
BASE="base_v4${TAG}"
SYS="finetuned_epoch${AD#ft}${TAG}"
URL=http://localhost:8000/v1
cd "$PIPE"
run() {  # system model
  python3 run_pipeline.py generate --system "$1" --prompt prompts/system_v4.md --url $URL --model "$2" --latency-n 0
  python3 run_pipeline.py validate --system "$1"
  python3 run_pipeline.py judge    --system "$1" --workers 16 --url $URL --model gemma
}
if [ -f "outputs/$BASE/judge.jsonl" ]; then echo "base run $BASE already done, skipping"; else run "$BASE" gemma; fi
run "$SYS" "$AD"
python3 run_pipeline.py matrix --systems "$BASE" "$SYS"
