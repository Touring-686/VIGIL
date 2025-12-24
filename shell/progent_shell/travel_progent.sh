#!/bin/bash

export PYTHONPATH="${PWD}/src"
export PROGENT_LOG_LEVEL="INFO"
export PROGENT_VERBOSE="True"
export SECAGENT_POLICY_MODEL="qwen3-max"
export OPENAI_API_KEY="sk-fea1a3667df94b538703ebe57d96aa35"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export SECAGENT_GENERATE="True"
export SECAGENT_UPDATE="True"
export SECAGENT_IGNORE_UPDATE_ERROR="True"
export SECAGENT_SUITE="travel"
export USE_SECAGENT="True"

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_a --attack-type parameter_override --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/travel/type_i_a > logs/progent-llm-generate-policy/travel_type_i_a.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_b --attack-type prerequisite_dependency --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/travel/type_i_b_prereq > logs/progent-llm-generate-policy/travel_type_i_b_prereq.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_b --attack-type postaction_dependency --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/travel/type_i_b_post > logs/progent-llm-generate-policy/travel_type_i_b_post.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_ii_a --attack-type short_circuit_reasoning --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/travel/type_ii_a > logs/progent-llm-generate-policy/travel_type_ii_a.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_ii_b --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/travel/type_ii_b > logs/progent-llm-generate-policy/travel_type_ii_b.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_a --attack-type sop_exfiltration --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/travel/type_iii_a_sop > logs/progent-llm-generate-policy/travel_type_iii_a_sop.log 2>&1 &
# ========================================
# Process Mapping for Travel Suite (Progent)
# ========================================
# Command 1: type_i_a (parameter_override)
#            Log: logs/progent-llm-generate/travel_type_i_a.log
#            Rundir: runs/progent-llm-generate/travel/type_i_a
#
# Command 2: type_i_b (prerequisite_dependency)
#            Log: logs/progent-llm-generate/travel_type_i_b_prereq.log
#            Rundir: runs/progent-llm-generate/travel/type_i_b_prereq
#
# Command 3: type_i_b (postaction_dependency)
#            Log: logs/progent-llm-generate/travel_type_i_b_post.log
#            Rundir: runs/progent-llm-generate/travel/type_i_b_post
#
# Command 4: type_ii_a (reasoning_shortcircuit)
#            Log: logs/progent-llm-generate/travel_type_ii_a.log
#            Rundir: runs/progent-llm-generate/travel/type_ii_a
#
# Command 5: type_ii_b (induced_parameter)
#            Log: logs/progent-llm-generate/travel_type_ii_b.log
#            Rundir: runs/progent-llm-generate/travel/type_ii_b
#
# Command 6: type_iii_a (sop_injection)
#            Log: logs/progent-llm-generate/travel_type_iii_a_sop.log
#            Rundir: runs/progent-llm-generate/travel/type_iii_a_sop
# ========================================
