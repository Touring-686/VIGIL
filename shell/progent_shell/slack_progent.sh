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
export SECAGENT_SUITE="slack"
export USE_SECAGENT="True"

python -m agentdojo.scripts.benchmark --suite slack --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_a --attack-type parameter_override --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/slack/type_i_a > logs/progent-llm-generate-policy/slack_type_i_a.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite slack --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_b --attack-type prerequisite_dependency --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/slack/type_i_b_prereq > logs/progent-llm-generate-policy/slack_type_i_b_prereq.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite slack --benchmark-version adversarial --attack tool_attack --attack-vector-type type_i_b --attack-type postaction_dependency --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/slack/type_i_b_post > logs/progent-llm-generate-policy/slack_type_i_b_post.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite slack --benchmark-version adversarial --attack tool_attack --attack-vector-type type_ii_a --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/slack/type_ii_a > logs/progent-llm-generate-policy/slack_type_ii_a.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite slack --benchmark-version adversarial --attack tool_attack --attack-vector-type type_ii_b --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/slack/type_ii_b > logs/progent-llm-generate-policy/slack_type_ii_b.log 2>&1 &

python -m agentdojo.scripts.benchmark --suite slack --benchmark-version adversarial --attack tool_attack --attack-vector-type type_iii_a --attack-type sop_exfiltration --model QWEN3_MAX --max-workers 1 --force-rerun --logdir runs/progent-llm-generate-policy/slack/type_iii_a_sop > logs/progent-llm-generate-policy/slack_type_iii_a_sop.log 2>&1 &

# ========================================
# Process Mapping for Slack Suite (Progent)
# ========================================
# Command 1: type_i_a (parameter_override)
#            Log: logs/progent-llm-generate-policy/slack_type_i_a.log
#            Rundir: runs/progent-llm-generate-policy/slack/type_i_a
#
# Command 2: type_i_b (prerequisite_dependency)
#            Log: logs/progent-llm-generate-policy/slack_type_i_b_prereq.log
#            Rundir: runs/progent-llm-generate-policy/slack/type_i_b_prereq
#
# Command 3: type_i_b (postaction_dependency)
#            Log: logs/progent-llm-generate-policy/slack_type_i_b_post.log
#            Rundir: runs/progent-llm-generate-policy/slack/type_i_b_post
#
# Command 4: type_ii_a (reasoning_shortcircuit)
#            Log: logs/progent-llm-generate-policy/slack_type_ii_a.log
#            Rundir: runs/progent-llm-generate-policy/slack/type_ii_a
#
# Command 5: type_ii_b (induced_parameter)
#            Log: logs/progent-llm-generate-policy/slack_type_ii_b.log
#            Rundir: runs/progent-llm-generate-policy/slack/type_ii_b
#
# Command 6: type_iii_a (sop_exfiltration)
#            Log: logs/progent-llm-generate-policy/slack_type_iii_a_sop.log
#            Rundir: runs/progent-llm-generate-policy/slack/type_iii_a_sop
# ========================================

#   3. 使用 ps aux | grep agentdojo.scripts.benchmark 找到对应的进程
#   4. 根据命令行参数（如 --attack-vector-type type_ii_b）匹配进程
#   5. 使用 kill <PID> 停止特定进程