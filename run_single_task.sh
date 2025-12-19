#!/bin/bash

# Script to run a single benchmark task with optional defense
# Usage: ./run_single_task.sh <suite> <attack_vector> [attack_type] [defense]
# Example: ./run_single_task.sh travel type_i_a parameter_override melon
# Example: ./run_single_task.sh travel type_i_a parameter_override base

if [ $# -lt 2 ]; then
    echo "Usage: $0 <suite> <attack_vector> [attack_type] [defense]"
    echo ""
    echo "Suites: travel, workspace, banking, slack"
    echo ""
    echo "Attack vectors and types:"
    echo "  type_i_a parameter_override"
    echo "  type_i_b prerequisite_dependency"
    echo "  type_i_b postaction_dependency"
    echo "  type_ii_a (no attack_type)"
    echo "  type_ii_b (no attack_type)"
    echo "  type_iii_a sop_exfiltration"
    echo ""
    echo "Defense: melon, base (default: base)"
    echo ""
    echo "Examples:"
    echo "  $0 travel type_i_a parameter_override melon"
    echo "  $0 travel type_i_a parameter_override base"
    echo "  $0 workspace type_ii_a \"\" melon"
    echo "  $0 banking type_iii_a sop_exfiltration base"
    exit 1
fi

SUITE=$1
ATTACK_VECTOR=$2
ATTACK_TYPE=$3
DEFENSE=${4:-base}  # Default to base if not specified

# Validate defense parameter
if [ "$DEFENSE" != "melon" ] && [ "$DEFENSE" != "base" ]; then
    echo "Error: Defense must be 'melon' or 'base'"
    exit 1
fi

# Create directories based on defense type
if [ "$DEFENSE" = "melon" ]; then
    LOGS_DIR="logs_melon"
    OUTPUTS_DIR="outputs_melon"
    RUNS_DIR="./runs_melon"
    DEFENSE_ARG="--defense melon"
    DEFENSE_LABEL="MELON defense"
else
    LOGS_DIR="logs_base"
    OUTPUTS_DIR="outputs_base"
    RUNS_DIR="./runs_base"
    DEFENSE_ARG=""
    DEFENSE_LABEL="base model (no defense)"
fi

mkdir -p "$LOGS_DIR"
mkdir -p "$OUTPUTS_DIR"

# Build task name
TASK_NAME="${SUITE}_${ATTACK_VECTOR}"
if [ -n "$ATTACK_TYPE" ]; then
    TASK_NAME="${TASK_NAME}_${ATTACK_TYPE}"
    ATTACK_TYPE_ARG="--attack-type ${ATTACK_TYPE}"
else
    ATTACK_TYPE_ARG=""
fi

LOG_FILE="${LOGS_DIR}/${TASK_NAME}.log"
OUTPUT_FILE="${OUTPUTS_DIR}/${TASK_NAME}.out"

echo "=== Running Benchmark Task ==="
echo "Suite: $SUITE"
echo "Attack Vector: $ATTACK_VECTOR"
echo "Attack Type: ${ATTACK_TYPE:-N/A}"
echo "Defense: $DEFENSE_LABEL"
echo "Task Name: $TASK_NAME"
echo "Log file: $LOG_FILE"
echo "Output file: $OUTPUT_FILE"
echo "Results dir: $RUNS_DIR"
echo ""

# Run the command
python -m agentdojo.scripts.benchmark \
    --suite "$SUITE" \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type "$ATTACK_VECTOR" \
    $ATTACK_TYPE_ARG \
    $DEFENSE_ARG \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir "$RUNS_DIR" \
    > "$OUTPUT_FILE" 2> "$LOG_FILE"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Task completed successfully"
else
    echo "✗ Task failed with exit code $EXIT_CODE"
    echo "Check log file: $LOG_FILE"
fi

echo "Output saved to: $OUTPUT_FILE"
echo "Log saved to: $LOG_FILE"

exit $EXIT_CODE
