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

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut  user_task_0 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task0.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut  user_task_1 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task1.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut  user_task_2 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task2.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut  user_task_3 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task3.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut  user_task_4 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task4.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut  user_task_5 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task5.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut  user_task_6 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task6.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_7 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task7.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_8 --logdir uns/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task8.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_9 --logdir uns/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task9.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_10 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task10.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_11 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task11.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_12 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task12.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_13 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task13.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_14 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task14.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_15 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task15.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_16 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task16.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_17 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task17.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_18 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task18.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_19 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task19.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --defense vigil --model QWEN3_MAX --max-workers 1 --force-rerun --use-tool-cache -ut user_task_20 --logdir runs/vigil-qwen/travel-bu/ > logs/vigil-qwen/travel_user_task20.log 2>&1 &
