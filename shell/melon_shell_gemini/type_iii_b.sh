#!/bin/bash
export PYTHONPATH="${PWD}/src"
export PROGENT_LOG_LEVEL="INFO"
export PROGENT_VERBOSE="False"
export SECAGENT_POLICY_MODEL="GEMINI_2_5_PRO_PREVIEW_05_06"
export OPENAI_API_KEY="sk-fea1a3667df94b538703ebe57d96aa35"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export SECAGENT_GENERATE="False"
export SECAGENT_UPDATE="False"
export SECAGENT_IGNORE_UPDATE_ERROR="False"
export SECAGENT_SUITE="False"
export USE_SECAGENT="False"
export PYTHONPATH="${PWD}/src"

export GOOGLE_API_KEY="sk-LY0rPYNkASdjCORsTUYku4FsryuagkjTolgVosbfv4xawSwi"
export GOOGLE_BASE_URL="https://api.chatanywhere.tech/v1"  # 默认值，可不设置

mkdir -p logs/melon-gemini

# python -m agentdojo.scripts.benchmark --suite banking --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense melon --model GEMINI_2_5_PRO_PREVIEW_05_06 --max-workers 1 --force-rerun --logdir runs/melon-gemini/type_iii_b_sop > logs/melon-gemini/banking_type_iii_b_sop.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite slack --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense melon --model GEMINI_2_5_PRO_PREVIEW_05_06 --max-workers 1 --force-rerun --logdir runs/melon-gemini/type_iii_b_sop > logs/melon-gemini/slack_type_iii_b_sop.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite workspace --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense melon --model GEMINI_2_5_PRO_PREVIEW_05_06 --max-workers 1 --force-rerun --logdir runs/melon-gemini/type_iii_b_sop > logs/melon-gemini/workspace_type_iii_b_sop.log 2>&1 &

# python -m agentdojo.scripts.benchmark --suite travel --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_b --attack-type sop_parameter_override --defense melon --model GEMINI_2_5_PRO_PREVIEW_05_06 --max-workers 1 --force-rerun --logdir runs/melon-gemini/type_iii_b_sop > logs/melon-gemini/travel_type_iii_b_sop.log 2>&1 &

# ========================================
# Process Mapping for Banking Suite (Progent)
# ========================================
# Command 1: type_i_a (parameter_override)
#            Log: logs/melon-gemini/banking_type_i_a.log
#            Rundir: runs/melon-gemini/type_i_a
#
# Command 2: type_i_b (prerequisite_dependency)
#            Log: logs/melon-gemini/banking_type_i_b_prereq.log
#            Rundir: runs/melon-gemini/type_i_b_prereq
#
# Command 3: type_i_b (postaction_dependency)
#            Log: logs/melon-gemini/banking_type_i_b_post.log
#            Rundir: runs/melon-gemini/type_i_b_post
#
# Command 4: type_ii_a (reasoning_shortcircuit)
#            Log: logs/melon-gemini/banking_type_ii_a.log
#            Rundir: runs/melon-gemini/type_ii_a
#
# Command 5: type_ii_b (induced_parameter)
#            Log: logs/melon-gemini/banking_type_ii_b.log
#            Rundir: runs/melon-gemini/type_ii_b
#
# Command 6: type_iii_b (sop_injection)
#            Log: logs/melon-gemini/banking_type_iii_b_sop.log
#            Rundir: runs/melon-gemini/type_iii_b_sop
# ========================================
