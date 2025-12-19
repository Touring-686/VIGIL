#!/bin/bash

# Script to run all benchmark tasks WITH MELON defense
# This tests the MELON defense framework's ability to defend against attacks

# Create directories for logs and outputs
mkdir -p logs_melon
mkdir -p outputs_melon

# Base command template (WITH --defense melon parameter)
PYTHON_CMD="python -m agentdojo.scripts.benchmark"
BASE_ARGS="--benchmark-version adversarial --attack tool_attack --defense melon --model QWEN3_MAX --max-workers 1 --force-rerun --logdir ./runs_melon"

# Define suites
SUITES=("travel" "workspace" "banking" "slack")

echo "Starting all benchmark tasks (MELON DEFENSE)..."
echo "Total tasks: 24 (4 suites × 6 attack combinations)"
echo "Logs will be saved to: ./logs_melon/"
echo "Outputs will be saved to: ./outputs_melon/"
echo "Results will be saved to: ./runs_melon/"
echo ""

# Function to run a benchmark task
run_task() {
    local suite=$1
    local attack_vector=$2
    local attack_type=$3
    local task_name="${suite}_${attack_vector}"

    if [ -n "$attack_type" ]; then
        task_name="${task_name}_${attack_type}"
        ATTACK_TYPE_ARG="--attack-type ${attack_type}"
    else
        ATTACK_TYPE_ARG=""
    fi

    local log_file="logs_melon/${task_name}.log"
    local output_file="outputs_melon/${task_name}.out"

    echo "Starting: $task_name (MELON defense)"

    $PYTHON_CMD \
        --suite "$suite" \
        --attack-vector-type "$attack_vector" \
        $ATTACK_TYPE_ARG \
        $BASE_ARGS \
        > "$output_file" 2> "$log_file" &

    echo "  PID: $! | Log: $log_file | Output: $output_file"
}

# ============================================================================
# Type I-A: parameter_override (4 tasks)
# ============================================================================
echo "=== Launching Type I-A (parameter_override) tasks ==="
for suite in "${SUITES[@]}"; do
    run_task "$suite" "type_i_a" "parameter_override"
done
echo ""

# ============================================================================
# Type I-B: prerequisite_dependency (4 tasks)
# ============================================================================
echo "=== Launching Type I-B (prerequisite_dependency) tasks ==="
for suite in "${SUITES[@]}"; do
    run_task "$suite" "type_i_b" "prerequisite_dependency"
done
echo ""

# ============================================================================
# Type I-B: postaction_dependency (4 tasks)
# ============================================================================
echo "=== Launching Type I-B (postaction_dependency) tasks ==="
for suite in "${SUITES[@]}"; do
    run_task "$suite" "type_i_b" "postaction_dependency"
done
echo ""

# ============================================================================
# Type II-A: no attack-type needed (4 tasks)
# ============================================================================
echo "=== Launching Type II-A tasks ==="
for suite in "${SUITES[@]}"; do
    run_task "$suite" "type_ii_a" ""
done
echo ""

# ============================================================================
# Type II-B: no attack-type needed (4 tasks)
# ============================================================================
echo "=== Launching Type II-B tasks ==="
for suite in "${SUITES[@]}"; do
    run_task "$suite" "type_ii_b" ""
done
echo ""

# ============================================================================
# Type III-A: sop_exfiltration (4 tasks)
# ============================================================================
echo "=== Launching Type III-A (sop_exfiltration) tasks ==="
for suite in "${SUITES[@]}"; do
    run_task "$suite" "type_iii_a" "sop_exfiltration"
done
echo ""

# ============================================================================
# Wait for all tasks to complete
# ============================================================================
echo "=== All 24 MELON DEFENSE tasks have been launched ==="
echo "Waiting for all tasks to complete..."
echo "You can monitor progress with: tail -f logs_melon/<task_name>.log"
echo ""
echo "To check running tasks: ps aux | grep benchmark"
echo "To kill all tasks: pkill -f 'agentdojo.scripts.benchmark'"
echo ""

# Wait for all background jobs
wait

echo ""
echo "=== All MELON DEFENSE tasks completed ==="
echo "Check outputs_melon/ directory for results"
echo "Check logs_melon/ directory for error logs"
echo "Check runs_melon/ directory for benchmark results"
