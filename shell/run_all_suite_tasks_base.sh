#!/bin/bash

# Environment Setup
# export WORKSPACE_FOLDER="${WORKSPACE_FOLDER:-$(cd "$(dirname "$0")" && pwd)}"
# export PYTHONPATH="${WORKSPACE_FOLDER}/src"
MODEL=${MODEL:-QWEN3_MAX}
MAX_WORKERS=${MAX_WORKERS:-1}

export PYTHONPATH="${PWD}/src"
# Create directory for console output logs
mkdir -p console_logs

# === Workspace Tasks (6) ===

# python -m agentdojo.scripts.benchmark \
#     --suite workspace \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_a \
#     --attack-type parameter_override \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/workspace/type_i_a_parameter_override \
#     > console_logs/workspace_type_i_a_parameter_override.log 2>&1 &

python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type prerequisite_dependency \
    --model "$MODEL" \
    --max-workers "$MAX_WORKERS" \
    --force-rerun \
    --logdir runs/base-qwen3-max/workspace/type_i_b_prerequisite_dependency \
    > logs/console_logs/workspace_type_i_b_prerequisite_dependency.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite workspace \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_b \
#     --attack-type postaction_dependency \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/workspace/type_i_b_postaction_dependency \
#     > logs/console_logs/workspace_type_i_b_postaction_dependency.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite workspace \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_ii_a \
#     --attack-type short_circuit_reasoning \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/workspace/type_ii_a_short_circuit_reasoning \
#     > console_logs/workspace_type_ii_a_short_circuit_reasoning.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite workspace \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_ii_b \
#     --attack-type induced_parameter \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/workspace/type_ii_b_induced_parameter \
#     > console_logs/workspace_type_ii_b_induced_parameter.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite workspace \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_iii_a \
#     --attack-type sop_exfiltration \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/workspace/type_iii_a_sop_exfiltration \
#     > console_logs/workspace_type_iii_a_sop_exfiltration.log 2>&1 &

# # === Travel Tasks (6) ===

# python -m agentdojo.scripts.benchmark \
#     --suite travel \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_a \
#     --attack-type parameter_override \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/travel/type_i_a_parameter_override \
#     > console_logs/travel_type_i_a_parameter_override.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite travel \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_b \
#     --attack-type prerequisite_dependency \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/travel/type_i_b_prerequisite_dependency \
#     > console_logs/travel_type_i_b_prerequisite_dependency.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite travel \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_b \
#     --attack-type postaction_dependency \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/travel/type_i_b_postaction_dependency \
#     > console_logs/travel_type_i_b_postaction_dependency.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite travel \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_ii_a \
#     --attack-type short_circuit_reasoning \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/travel/type_ii_a_short_circuit_reasoning \
#     > console_logs/travel_type_ii_a_short_circuit_reasoning.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite travel \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_ii_b \
#     --attack-type induced_parameter \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/travel/type_ii_b_induced_parameter \
#     > console_logs/travel_type_ii_b_induced_parameter.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite travel \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_iii_a \
#     --attack-type sop_exfiltration \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/travel/type_iii_a_sop_exfiltration \
#     > console_logs/travel_type_iii_a_sop_exfiltration.log 2>&1 &

# # === Banking Tasks (6) ===

# python -m agentdojo.scripts.benchmark \
#     --suite banking \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_a \
#     --attack-type parameter_override \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/banking/type_i_a_parameter_override \
#     > console_logs/banking_type_i_a_parameter_override.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite banking \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_b \
#     --attack-type prerequisite_dependency \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/banking/type_i_b_prerequisite_dependency \
#     > console_logs/banking_type_i_b_prerequisite_dependency.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite banking \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_b \
#     --attack-type postaction_dependency \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/banking/type_i_b_postaction_dependency \
#     > logs/console_logs/banking_type_i_b_postaction_dependency.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite banking \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_ii_a \
#     --attack-type short_circuit_reasoning \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/banking/type_ii_a_short_circuit_reasoning \
#     > console_logs/banking_type_ii_a_short_circuit_reasoning.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite banking \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_ii_b \
#     --attack-type induced_parameter \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/banking/type_ii_b_induced_parameter \
#     > console_logs/banking_type_ii_b_induced_parameter.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite banking \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_iii_a \
#     --attack-type sop_exfiltration \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/banking/type_iii_a_sop_exfiltration \
#     > console_logs/banking_type_iii_a_sop_exfiltration.log 2>&1 &

# # === Slack Tasks (6) ===

# python -m agentdojo.scripts.benchmark \
#     --suite slack \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_a \
#     --attack-type parameter_override \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/slack/type_i_a_parameter_override \
#     > console_logs/slack_type_i_a_parameter_override.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite slack \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_b \
#     --attack-type prerequisite_dependency \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/slack/type_i_b_prerequisite_dependency \
#     > console_logs/slack_type_i_b_prerequisite_dependency.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite slack \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_i_b \
#     --attack-type postaction_dependency \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/slack/type_i_b_postaction_dependency \
#     > console_logs/slack_type_i_b_postaction_dependency.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite slack \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_ii_a \
#     --attack-type short_circuit_reasoning \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/slack/type_ii_a_short_circuit_reasoning \
#     > console_logs/slack_type_ii_a_short_circuit_reasoning.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite slack \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_ii_b \
#     --attack-type induced_parameter \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/slack/type_ii_b_induced_parameter \
#     > console_logs/slack_type_ii_b_induced_parameter.log 2>&1 &

# python -m agentdojo.scripts.benchmark \
#     --suite slack \
#     --benchmark-version adversarial \
#     --attack tool_attack \
#     --attack-vector-type type_iii_a \
#     --attack-type sop_exfiltration \
#     --model "$MODEL" \
#     --max-workers "$MAX_WORKERS" \
#     --force-rerun \
#     --logdir runs/base-qwen3-max/slack/type_iii_a_sop_exfiltration \
#     > console_logs/slack_type_iii_a_sop_exfiltration.log 2>&1 &