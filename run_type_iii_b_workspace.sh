#!/bin/bash
# Travel | type_iii_b | Parameter Override
# 对应 VS Code launch 配置的执行脚本

# 设置工作目录为脚本所在目录
cd "$(dirname "$0")"

# 设置 PYTHONPATH
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

mkdir -p logs/type_iii_b/workspace

# 运行 benchmark
python -m agentdojo.scripts.benchmark \
  --suite workspace \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type type_iii_b \
  --attack-type sop_parameter_override \
  --model qwen3-max \
  --max-workers 1 \
  --force-rerun \
  --logdir "${PWD}/runs/workspace/type_iii_b_param" > "${PWD}/logs/type_iii_b/workspace/run.log" 2>&1 &
