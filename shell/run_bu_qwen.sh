#!/bin/bash
export PYTHONPATH="${PWD}/src"
export PROGENT_LOG_LEVEL="INFO"
export PROGENT_VERBOSE="False"
export SECAGENT_POLICY_MODEL="qwen3-max"
# export OPENAI_API_KEY="sk-fea1a3667df94b538703ebe57d96aa35"
# export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export GOOGLE_API_KEY="sk-SFzBy6tGKaTwvDaWhKfykughR1KPLMDrHZ1ub7SDglDfKiYZ"
export GOOGLE_BASE_URL="https://api.chatanywhere.tech/v1"  # 默认值，可不设置

export SECAGENT_GENERATE="False"
export SECAGENT_UPDATE="False"
export SECAGENT_IGNORE_UPDATE_ERROR="False"
export SECAGENT_SUITE="False"
export USE_SECAGENT="False"
export PYTHONPATH="${PWD}/src"
mkdir -p logs/base-gemini

python -m agentdojo.scripts.benchmark --benchmark-version adversarial  --model QWEN3_MAX --max-workers 1  --logdir runs/base-bu/ > logs/benigh-utility/base-qwen.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite banking --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_b --attack-type prerequisite_dependency  --model QWEN3_MAX --max-workers 1  --logdir runs/base-gemini/type_i_b_prereq > logs/base-gemini/banking_type_i_b_prereq.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite banking --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_b --attack-type postaction_dependency  --model QWEN3_MAX --max-workers 1  --logdir runs/base-gemini/type_i_b_post > logs/base-gemini/banking_type_i_b_post.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite banking --benchmark-version adversarial --attack tool_attack --attack-vector-type type_ii_a --attack-type short_circuit_reasoning  --model QWEN3_MAX --max-workers 1  --logdir runs/base-gemini/type_ii_a > logs/base-gemini/banking_type_ii_a.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite banking --benchmark-version adversarial --attack tool_attack --attack-vector-type type_ii_b --attack-type induced_parameter  --model QWEN3_MAX --max-workers 1  --logdir runs/base-gemini/type_ii_b > logs/base-gemini/banking_type_ii_b.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite banking --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_a --attack-type sop_exfiltration  --model QWEN3_MAX --max-workers 1  --logdir runs/base-gemini/type_iii_a_sop > logs/base-gemini/banking_type_iii_a_sop.log 2>&1 &

# ========================================
# Process Mapping for Banking Suite (Progent)
# ========================================
# Command 1: type_i_a (parameter_override)
#            Log: logs/base-gemini/banking_type_i_a.log
#            Rundir: runs/base-gemini/type_i_a
#
# Command 2: type_i_b (prerequisite_dependency)
#            Log: logs/base-gemini/banking_type_i_b_prereq.log
#            Rundir: runs/base-gemini/type_i_b_prereq
#
# Command 3: type_i_b (postaction_dependency)
#            Log: logs/base-gemini/banking_type_i_b_post.log
#            Rundir: runs/base-gemini/type_i_b_post
#
# Command 4: type_ii_a (reasoning_shortcircuit)
#            Log: logs/base-gemini/banking_type_ii_a.log
#            Rundir: runs/base-gemini/type_ii_a
#
# Command 5: type_ii_b (induced_parameter)
#            Log: logs/base-gemini/banking_type_ii_b.log
#            Rundir: runs/base-gemini/type_ii_b
#
# Command 6: type_iii_a (sop_injection)
#            Log: logs/base-gemini/banking_type_iii_a_sop.log
#            Rundir: runs/base-gemini/type_iii_a_sop
# ========================================
