#!/bin/bash
export PYTHONPATH="${PWD}/src"
export PROGENT_LOG_LEVEL="INFO"
export PROGENT_VERBOSE="False"
export SECAGENT_POLICY_MODEL="qwen3-max"
export OPENAI_API_KEY="sk-f8174fa268764faead0a51756f6b1e43"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
# export GOOGLE_API_KEY="sk-SFzBy6tGKaTwvDaWhKfykughR1KPLMDrHZ1ub7SDglDfKiYZ"
# export GOOGLE_BASE_URL="https://api.chatanywhere.tech/v1"  # 默认值，可不设置

export SECAGENT_GENERATE="False"
export SECAGENT_UPDATE="False"
export SECAGENT_IGNORE_UPDATE_ERROR="False"
export SECAGENT_SUITE="False"
export USE_SECAGENT="False"
export PYTHONPATH="${PWD}/src"
mkdir -p logs/vigil-qwen

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s workspace \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/workspace/user_tasks_only > logs/vigil-qwen-bu/workspace_bu3.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --benchmark-version adversarial \
#     --defense vigil \
#     --model QWEN3_MAX \
#     -s banking \
#     --max-workers 1 \
#     --force-rerun \
#     --logdir ./runs/vigil/workspace/user_tasks_only > logs/vigil-qwen-bu/banking_bu3.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --benchmark-version adversarial \
#     --defense vigil \
#     --model QWEN3_MAX \
#     -s travel \
#     --max-workers 1 \
#     --force-rerun \
#     --logdir ./runs/vigil/workspace/user_tasks_only > logs/vigil-qwen-bu/travel_bu3.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --benchmark-version adversarial \
#     --defense vigil \
#     --model QWEN3_MAX \
#     -s slack \
#     --max-workers 1 \
#     --force-rerun \
#     --logdir ./runs/vigil/workspace/user_tasks_only > logs/vigil-qwen-bu/slack_bu3.log 2>&1 &
