#!/bin/bash
export PYTHONPATH="${PWD}/src"
export PROGENT_LOG_LEVEL="INFO"
export PROGENT_VERBOSE="False"
export SECAGENT_POLICY_MODEL="qwen3-max"
export OPENAI_API_KEY="sk-fea1a3667df94b538703ebe57d96aa35"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

export SECAGENT_GENERATE="False"
export SECAGENT_UPDATE="False"
export SECAGENT_IGNORE_UPDATE_ERROR="False"
export SECAGENT_SUITE="False"
export USE_SECAGENT="False"
export PYTHONPATH="${PWD}/src"
mkdir -p logs/detector-qwen

# python -m agentdojo.scripts.benchmark --suite banking --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense transformers_pi_detector --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/detector-qwen/type_iii_b_sop > logs/detector-qwen/banking_type_iii_b_sop.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite slack --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense transformers_pi_detector --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/detector-qwen/type_iii_b_sop > logs/detector-qwen/slack_type_iii_b_sop.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite workspace --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense transformers_pi_detector --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/detector-qwen/type_iii_b_sop > logs/detector-qwen/workspace_type_iii_b_sop.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense transformers_pi_detector --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/detector-qwen/type_iii_b_sop > logs/detector-qwen/travel_type_iii_b_sop.log 2>&1 &

# ========================================
# Process Mapping for Banking Suite (Progent)
# ========================================
# Command 1: type_i_a (parameter_override)
#            Log: logs/detector-gemini/banking_type_i_a.log
#            Rundir: runs/detector-gemini/type_i_a
#
# Command 2: type_i_b (prerequisite_dependency)
#            Log: logs/detector-gemini/banking_type_i_b_prereq.log
#            Rundir: runs/detector-gemini/type_i_b_prereq
#
# Command 3: type_i_b (postaction_dependency)
#            Log: logs/detector-gemini/banking_type_i_b_post.log
#            Rundir: runs/detector-gemini/type_i_b_post
#
# Command 4: type_ii_a (reasoning_shortcircuit)
#            Log: logs/detector-gemini/banking_type_ii_a.log
#            Rundir: runs/detector-gemini/type_ii_a
#
# Command 5: type_ii_b (induced_parameter)
#            Log: logs/detector-gemini/banking_type_ii_b.log
#            Rundir: runs/detector-gemini/type_ii_b
#
# Command 6: type_iii_b (sop_injection)
#            Log: logs/detector-gemini/banking_type_iii_b_sop.log
#            Rundir: runs/detector-gemini/type_iii_b_sop
# ========================================
