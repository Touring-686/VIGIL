#!/bin/bash

WORKSPACE="/Users/justin/BDAA/agent + 安全/code/agentdojo"
export PYTHONPATH="${WORKSPACE}/src"

# 定义所有 suites
SUITES=("banking" "slack" "travel" "workspace")

# 存储所有后台进程的PID
declare -a PIDS=()
declare -a JOB_NAMES=()

# 函数：运行单个测试（后台执行）
run_test() {
    local suite=$1
    local attack_vector_type=$2
    local attack_type=$3
    
    # 构建日志目录和文件名
    if [ -z "$attack_type" ]; then
        LOG_DIR="${WORKSPACE}/runs/melon/${suite}/${attack_vector_type}"
        LOG_FILE="${LOG_DIR}/run.log"
        JOB_NAME="${suite}/${attack_vector_type}"
    else
        LOG_DIR="${WORKSPACE}/runs/melon/${suite}/${attack_vector_type}_${attack_type}"
        LOG_FILE="${LOG_DIR}/run.log"
        JOB_NAME="${suite}/${attack_vector_type}_${attack_type}"
    fi
    
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting: $JOB_NAME"
    echo "  Log: $LOG_FILE"
    
    # 构建并执行命令（后台运行）
    if [ -z "$attack_type" ]; then
        # type_ii_a 和 type_ii_b 不需要 attack_type
        (
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Started: $JOB_NAME" >> "$LOG_FILE"
            python -m agentdojo.scripts.benchmark \
              --suite "$suite" \
              --benchmark-version adversarial \
              --attack tool_attack \
              --attack-vector-type "$attack_vector_type" \
              --model QWEN3_MAX \
              --max-workers 1 \
              --force-rerun \
              --defense melon \
              --logdir "$LOG_DIR" \
              2>&1 | tee -a "$LOG_FILE"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Completed: $JOB_NAME" >> "$LOG_FILE"
        ) &
    else
        (
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Started: $JOB_NAME" >> "$LOG_FILE"
            python -m agentdojo.scripts.benchmark \
              --suite "$suite" \
              --benchmark-version adversarial \
              --attack tool_attack \
              --attack-vector-type "$attack_vector_type" \
              --attack-type "$attack_type" \
              --model QWEN3_MAX \
              --max-workers 1 \
              --force-rerun \
              --defense melon \
              --logdir "$LOG_DIR" \
              2>&1 | tee -a "$LOG_FILE"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Completed: $JOB_NAME" >> "$LOG_FILE"
        ) &
    fi
    
    # 记录进程ID和任务名称
    PIDS+=($!)
    JOB_NAMES+=("$JOB_NAME")
}

echo "=========================================="
echo "Starting parallel execution of all tests"
echo "Start time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 启动所有测试（并行）
for suite in "${SUITES[@]}"; do
    # type_i_a - parameter_override
    run_test "$suite" "type_i_a" "parameter_override"
    
    # type_i_b - postaction_dependency
    run_test "$suite" "type_i_b" "postaction_dependency"
    
    # type_i_b - prerequisite_dependency
    run_test "$suite" "type_i_b" "prerequisite_dependency"
    
    # type_ii_a - 无 attack_type
    run_test "$suite" "type_ii_a" ""
    
    # type_ii_b - 无 attack_type
    run_test "$suite" "type_ii_b" ""
    
    # type_iii_a - sop_injection
    run_test "$suite" "type_iii_a" "sop_injection"
done

echo ""
echo "=========================================="
echo "All ${#PIDS[@]} tests launched in parallel"
echo "Waiting for completion..."
echo "=========================================="
echo ""

# 等待所有后台任务完成并检查状态
failed_jobs=0
for i in "${!PIDS[@]}"; do
    pid=${PIDS[$i]}
    job_name=${JOB_NAMES[$i]}
    
    if wait $pid; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Completed: $job_name"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ Failed: $job_name (exit code: $?)"
        ((failed_jobs++))
    fi
done

echo ""
echo "=========================================="
echo "All tests completed!"
echo "End time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Total jobs: ${#PIDS[@]}"
echo "Failed jobs: $failed_jobs"
echo "Success rate: $(( (${#PIDS[@]} - failed_jobs) * 100 / ${#PIDS[@]} ))%"
echo "=========================================="
echo ""
echo "Results saved to: ${WORKSPACE}/runs/melon/"
