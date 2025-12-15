#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATTACK_VECTOR_TYPE="${ATTACK_VECTOR_TYPE:-type_i_a}"
LOGDIR="${SCRIPT_DIR}/runs/${ATTACK_VECTOR_TYPE}"

# Run travel suite with tool_attack; logdir keyed by attack vector type
PYTHONPATH="${SCRIPT_DIR}/src" \
python -m agentdojo.scripts.benchmark \
  --suite travel \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type "${ATTACK_VECTOR_TYPE}" \
  --model QWEN3_MAX \
  --max-workers 1 \
  --force-rerun \
  --logdir "${LOGDIR}" \
  "$@"
