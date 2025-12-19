#!/bin/bash

# Script to monitor the status of all benchmark tasks
# Usage: ./monitor_tasks.sh [base|melon|all]

MODE=${1:-all}  # Default to monitoring all

# Validate mode parameter
if [ "$MODE" != "base" ] && [ "$MODE" != "melon" ] && [ "$MODE" != "all" ]; then
    echo "Usage: $0 [base|melon|all]"
    echo "  base  - Monitor only base model tasks"
    echo "  melon - Monitor only MELON defense tasks"
    echo "  all   - Monitor both (default)"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "==================================="
echo "  Benchmark Tasks Monitor"
echo "==================================="
echo ""

# Count running processes
RUNNING_COUNT=$(ps aux | grep -c '[a]gentdojo.scripts.benchmark')
echo -e "${BLUE}Running tasks:${NC} $RUNNING_COUNT"
echo ""

# Define all 24 tasks
declare -a TASKS=(
    "travel_type_i_a_parameter_override"
    "workspace_type_i_a_parameter_override"
    "banking_type_i_a_parameter_override"
    "slack_type_i_a_parameter_override"
    "travel_type_i_b_prerequisite_dependency"
    "workspace_type_i_b_prerequisite_dependency"
    "banking_type_i_b_prerequisite_dependency"
    "slack_type_i_b_prerequisite_dependency"
    "travel_type_i_b_postaction_dependency"
    "workspace_type_i_b_postaction_dependency"
    "banking_type_i_b_postaction_dependency"
    "slack_type_i_b_postaction_dependency"
    "travel_type_ii_a"
    "workspace_type_ii_a"
    "banking_type_ii_a"
    "slack_type_ii_a"
    "travel_type_ii_b"
    "workspace_type_ii_b"
    "banking_type_ii_b"
    "slack_type_ii_b"
    "travel_type_iii_a_sop_exfiltration"
    "workspace_type_iii_a_sop_exfiltration"
    "banking_type_iii_a_sop_exfiltration"
    "slack_type_iii_a_sop_exfiltration"
)

# Function to check task status for a given mode
check_mode_status() {
    local mode=$1
    local outputs_dir=$2
    local logs_dir=$3
    local label=$4

    echo "==================================="
    echo "  $label"
    echo "==================================="
    echo ""

    local COMPLETED=0
    local IN_PROGRESS=0
    local NOT_STARTED=0
    local FAILED=0

    if [ ! -d "$outputs_dir" ] && [ ! -d "$logs_dir" ]; then
        echo -e "${YELLOW}No tasks found for this mode${NC}"
        echo ""
        return
    fi

    for task in "${TASKS[@]}"; do
        OUTPUT_FILE="$outputs_dir/${task}.out"
        LOG_FILE="$logs_dir/${task}.log"

        # Check if output file exists and has content
        if [ -f "$OUTPUT_FILE" ]; then
            # Check if process is still running
            if ps aux | grep -q "[a]gentdojo.scripts.benchmark.*${task}.*${mode}"; then
                echo -e "${YELLOW}⏳ IN PROGRESS:${NC} $task"
                IN_PROGRESS=$((IN_PROGRESS + 1))
            else
                # Check for errors in log
                if [ -f "$LOG_FILE" ] && grep -qi "error\|exception\|failed" "$LOG_FILE"; then
                    echo -e "${RED}✗ FAILED:${NC} $task"
                    FAILED=$((FAILED + 1))
                else
                    echo -e "${GREEN}✓ COMPLETED:${NC} $task"
                    COMPLETED=$((COMPLETED + 1))
                fi
            fi
        else
            echo -e "○ NOT STARTED: $task"
            NOT_STARTED=$((NOT_STARTED + 1))
        fi
    done

    echo ""
    echo "--- Summary ---"
    echo -e "${GREEN}Completed:${NC}    $COMPLETED / 24"
    echo -e "${YELLOW}In Progress:${NC}  $IN_PROGRESS / 24"
    echo -e "${RED}Failed:${NC}       $FAILED / 24"
    echo -e "Not Started:  $NOT_STARTED / 24"

    # Progress percentage
    TOTAL_DONE=$((COMPLETED + FAILED))
    PROGRESS=$((TOTAL_DONE * 100 / 24))
    echo -e "Overall Progress: ${PROGRESS}%"
    echo ""

    # Disk usage
    if [ -d "$outputs_dir" ]; then
        OUTPUTS_SIZE=$(du -sh "$outputs_dir" 2>/dev/null | cut -f1)
        echo "Outputs: $OUTPUTS_SIZE"
    fi
    if [ -d "$logs_dir" ]; then
        LOGS_SIZE=$(du -sh "$logs_dir" 2>/dev/null | cut -f1)
        echo "Logs: $LOGS_SIZE"
    fi
    echo ""
}

# Monitor based on mode
if [ "$MODE" = "base" ] || [ "$MODE" = "all" ]; then
    check_mode_status "base" "outputs_base" "logs_base" "BASE MODEL (No Defense)"
fi

if [ "$MODE" = "melon" ] || [ "$MODE" = "all" ]; then
    check_mode_status "melon" "outputs_melon" "logs_melon" "MELON DEFENSE"
fi

# Show currently running tasks with PIDs
if [ $RUNNING_COUNT -gt 0 ]; then
    echo "==================================="
    echo "  Running Processes"
    echo "==================================="
    ps aux | grep '[a]gentdojo.scripts.benchmark' | awk '{print "PID: " $2 " | CPU: " $3 "% | MEM: " $4 "% | " $11 " " $12 " " $13 " " $14 " " $15}'
    echo ""
fi

# Offer options
echo "==================================="
echo "  Quick Commands"
echo "==================================="
echo ""

if [ $RUNNING_COUNT -eq 0 ]; then
    echo -e "${BLUE}Start tasks:${NC}"
    echo "  ./run_all_benchmarks_base.sh   # Base model"
    echo "  ./run_all_benchmarks_melon.sh  # MELON defense"
    echo ""
fi

if [ $RUNNING_COUNT -gt 0 ]; then
    echo -e "${BLUE}Stop all running tasks:${NC}"
    echo "  pkill -f 'agentdojo.scripts.benchmark'"
    echo ""
fi

echo -e "${BLUE}Monitor logs:${NC}"
echo "  tail -f logs_base/<task_name>.log"
echo "  tail -f logs_melon/<task_name>.log"
echo ""

echo -e "${BLUE}Compare results:${NC}"
echo "  diff -r runs_base runs_melon"
echo ""
