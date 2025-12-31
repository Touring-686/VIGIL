#!/bin/bash

export PYTHONPATH="${PWD}/src"
mkdir -p logs/spotlight

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

python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_a \
    --attack-type parameter_override \
    --defense spotlighting_with_delimiting \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir runs/spotlight/workspace/type_i_a > logs/spotlight/workspace_type_i_a.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type prerequisite_dependency \
    --defense spotlighting_with_delimiting \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir runs/spotlight/workspace/type_i_b_prereq > logs/spotlight/workspace_type_i_b_prereq.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type postaction_dependency \
    --defense spotlighting_with_delimiting \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir runs/spotlight/workspace/type_i_b_post > logs/spotlight/workspace_type_i_b_post.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_a \
    --attack-type short_circuit_reasoning \
    --defense spotlighting_with_delimiting \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir runs/spotlight/workspace/type_ii_a > logs/spotlight/workspace_type_ii_a.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_b \
    --attack-type induced_parameter \
    --defense spotlighting_with_delimiting \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir runs/spotlight/workspace/type_ii_b > logs/spotlight/workspace_type_ii_b.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_iii_a \
    --attack-type sop_exfiltration \
    --defense spotlighting_with_delimiting \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir runs/spotlight/workspace/type_iii_a_sop > logs/spotlight/workspace_type_iii_a_sop.log 2>&1 &

# ========================================
# Process Mapping for Workspace Suite (Progent)
# ========================================
# Command 1: type_i_a (parameter_override)
#            Log: logs/spotlight/workspace_type_i_a.log
#            Rundir: runs/spotlight/workspace/type_i_a
#
# Command 2: type_i_b (prerequisite_dependency)
#            Log: logs/spotlight/workspace_type_i_b_prereq.log
#            Rundir: runs/spotlight/workspace/type_i_b_prereq
#
# Command 3: type_i_b (postaction_dependency)
#            Log: logs/spotlight/workspace_type_i_b_post.log
#            Rundir: runs/spotlight/workspace/type_i_b_post
#
# Command 4: type_ii_a (reasoning_shortcircuit)
#            Log: logs/spotlight/workspace_type_ii_a.log
#            Rundir: runs/spotlight/workspace/type_ii_a
#
# Command 5: type_ii_b (induced_parameter)
#            Log: logs/spotlight/workspace_type_ii_b.log
#            Rundir: runs/spotlight/workspace/type_ii_b
#
# Command 6: type_iii_a (sop_exfiltration)
#            Log: logs/spotlight/workspace_type_iii_a_sop.log
#            Rundir: runs/spotlight/workspace/type_iii_a_sop
# ========================================
