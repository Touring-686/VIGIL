#!/bin/bash

# Create log directory if not exists
mkdir -p "/Users/justin/BDAA/agent + 安全/code/agentdojo/runs/workspace/type_ii_a"

# Run benchmark with output redirected to log file
PYTHONPATH="/Users/justin/BDAA/agent + 安全/code/agentdojo/src" \
python -m agentdojo.scripts.benchmark \
  --suite workspace \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type type_ii_a \
  --model QWEN3_MAX \
  --max-workers 1 \
  --force-rerun \
  --logdir "/Users/justin/BDAA/agent + 安全/code/agentdojo/runs/workspace/type_ii_a" \
  2>&1 | tee "/Users/justin/BDAA/agent + 安全/code/agentdojo/runs/workspace/type_ii_a/benchmark.log"
