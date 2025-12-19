# WORKSPACE="/Users/justin/BDAA/agent + 安全/code/agentdojo"
# export PYTHONPATH="${WORKSPACE}/src"

# LOG_FILE="${WORKSPACE}/runs/melon/travel/type_iii_a/type_iii_a_sop_exfiltration.log"

# # 创建日志目录（如果不存在）
# mkdir -p "$(dirname "$LOG_FILE")"

# # 执行并重定向输出到日志文件
# # python -m agentdojo.scripts.benchmark \
# #   --suite banking \
# #   --benchmark-version adversarial \
# #   --attack tool_attack \
# #   --attack-vector-type type_iii_a \
# #   --attack-type sop_exfiltration \
# #   --model QWEN3_MAX \
# #   --max-workers 1 \
# #   --force-rerun \
# #   --defense melon \
# #   --logdir "${WORKSPACE}/runs/melon/banking/type_iii_a_sop_exfiltration" \
# #   2>&1 | tee "$LOG_FILE"

# python -m agentdojo.scripts.benchmark \
#   --suite travel \
#   --benchmark-version adversarial \
#   --attack tool_attack \
#   --attack-vector-type type_iii_a \
#   --attack-type sop_exfiltration \
#   --model QWEN3_MAX \
#   --max-workers 1 \
#   --force-rerun \
#   --defense melon \
#   --logdir "${WORKSPACE}/runs/melon/travel/type_iii_a_sop_exfiltration" \
#   2>&1 | tee "$LOG_FILE"


# echo "Log saved to: $LOG_FILE"

WORKSPACE="/Users/justin/BDAA/agent + 安全/code/agentdojo"
export PYTHONPATH="${WORKSPACE}/src"

LOG_FILE="${WORKSPACE}/runs/melon/travel/type_i_b/type_i_b_prerequisite_dependency.log"

# 创建日志目录（如果不存在）
mkdir -p "$(dirname "$LOG_FILE")"

python -m agentdojo.scripts.benchmark \
  --suite travel \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type type_i_b \
  --attack-type prerequisite_dependency \
  --model QWEN3_MAX \
  --max-workers 1 \
  --force-rerun \
  --defense melon \
  --logdir "${WORKSPACE}/runs/melon/travel/type_i_b_prerequisite_dependency" \
  2>&1 | tee "$LOG_FILE"


echo "Log saved to: $LOG_FILE"