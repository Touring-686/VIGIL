#!/bin/bash

WORKSPACE="/Users/justin/BDAA/agent + 安全/code/agentdojo"
export PYTHONPATH="${WORKSPACE}/src"

LOG_FILE="${WORKSPACE}/runs/workspace/type_iii_a_sop_exfiltration/run_injectiontask1500.log"

# 创建日志目录（如果不存在）
mkdir -p "$(dirname "$LOG_FILE")"

# 执行并重定向输出到日志文件
python -m agentdojo.scripts.benchmark \
  --suite workspace \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type type_iii_a \
  --attack-type sop_exfiltration \
  --model QWEN3_MAX \
  --max-workers 1 \
  --force-rerun \
  --logdir "${WORKSPACE}/runs/workspace/type_iii_a_sop_exfiltration" \
  2>&1 | tee "$LOG_FILE"

echo "Log saved to: $LOG_FILE"