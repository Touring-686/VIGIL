#!/bin/bash
# Workspace | type_iii_b | Parameter Override
# 运行所有 workspace type_iii_b 注入任务

# 设置工作目录为脚本所在目录
cd "$(dirname "$0")"

# 设置 PYTHONPATH
export PYTHONPATH="${PWD}/src:${PWD}:${PYTHONPATH}"

echo "=========================================="
echo "Running Workspace Type III-B Benchmark"
echo "=========================================="
echo "Suite: workspace"
echo "Attack Vector: type_iii_b"
echo "Attack Type: sop_parameter_override"
echo "Model: QWEN3_MAX"
echo "=========================================="

# 运行 benchmark（不指定 injection-task-id 会运行所有任务）
python -m agentdojo.scripts.benchmark \
  --suite workspace \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type type_iii_b \
  --attack-type sop_parameter_override \
  --model QWEN3_MAX \
  --max-workers 1 \
  --force-rerun \
  --logdir "${PWD}/runs/workspace/type_iii_b_param"

echo ""
echo "=========================================="
echo "Benchmark completed!"
echo "Results saved to: runs/workspace/type_iii_b_param/"
echo "=========================================="
