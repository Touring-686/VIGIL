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
mkdir -p logs/vigil-qwen-bu/travel

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_0 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_0.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_1 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_1.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_2 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_2.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_3 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_3.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_4 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_4.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_5 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_5.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_6 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_6.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_7 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_7.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_8 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_8.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_9 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_9.log 2>&1 &
python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_10 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_10.log 2>&1 &
python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_11 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_11.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_12 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_12.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_13 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_13.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_14 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_14.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_15 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_15.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_16 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_16.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_17 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_17.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --benchmark-version adversarial \
    --defense vigil \
    --model QWEN3_MAX \
    -s travel \
    -ut user_task_18 \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs/vigil/travel/user_tasks_only > logs/vigil-qwen-bu/travel/user_task_18.log 2>&1 &
    