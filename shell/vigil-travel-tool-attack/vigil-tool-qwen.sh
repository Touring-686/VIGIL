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
mkdir -p logs/vigil-qwen-tool

python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_a --attack-type parameter_override --defense vigil --enable-path-cache --model QWEN3_MAX --max-workers 1 --logdir runs/vigil-qwen-tool/travel/type_i_a > logs/vigil-qwen-tool/travel_type_i_a.log 2>&1 &


python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_b --attack-type prerequisite_dependency --defense vigil --enable-path-cache --model QWEN3_MAX --max-workers 1 --logdir runs/vigil-qwen-tool/travel/type_i_b_prereq > logs/vigil-qwen-tool/travel_type_i_b_prereq.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_b --attack-type postaction_dependency --defense vigil --enable-path-cache --model QWEN3_MAX --max-workers 1 --logdir runs/vigil-qwen-tool/travel/type_i_b_post > logs/vigil-qwen-tool/travel_type_i_b_post.log 2>&1 &  

python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_ii_a --attack-type short_circuit_reasoning --defense vigil --enable-path-cache --model QWEN3_MAX --max-workers 1 --logdir runs/vigil-qwen-tool/travel/type_ii_a > logs/vigil-qwen-tool/travel_type_ii_a.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_ii_b --attack-type induced_parameter --defense vigil --enable-path-cache --model QWEN3_MAX --max-workers 1 --logdir runs/vigil-qwen-tool/travel/type_ii_b > logs/vigil-qwen-tool/travel_type_ii_b.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_a --attack-type sop_exfiltration --defense vigil --enable-path-cache --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/vigil-qwen-tool/travel/type_iii_a_sop > logs/vigil-qwen-tool/travel_type_iii_a_sop.log 2>&1 &   

python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense vigil --enable-path-cache --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/vigil-qwen-tool/travel/type_iii_b_sop > logs/vigil-qwen-tool/travel_type_iii_b_sop.log 2>&1 &
