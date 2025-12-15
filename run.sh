#!/bin/bash
# Logs now encode SECAGENT options for easier inspection.

log_dir="logs"
mkdir -p "$log_dir"

# model="gpt-4o-2024-08-06"
# model="claude-3-7-sonnet-20250219"
# model="facebook/Meta-SecAlign-70B"
# model="claude-sonnet-4-20250514"
# model="gpt-4.1-2025-04-14"
# model="gemini-2.5-flash"
model="qwen3-max"

# export SECAGENT_POLICY_MODEL="gpt-4o-2024-08-06"
# export SECAGENT_POLICY_MODEL="claude-sonnet-4-20250514"
# export SECAGENT_POLICY_MODEL="gpt-4.1-2025-04-14"
# export SECAGENT_POLICY_MODEL="gemini-2.5-flash"
export SECAGENT_POLICY_MODEL="qwen3-max"
export OPENAI_API_KEY="sk-fea1a3667df94b538703ebe57d96aa35"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

# manual policies
export SECAGENT_GENERATE="False"

# auto policies (set to True to enable)
# export SECAGENT_UPDATE="True"
# export SECAGENT_IGNORE_UPDATE_ERROR="True"

export COLUMNS=300

run_suite() {
  local suite="$1"
  local attack="$2"  # empty string for no attack
  local attack_label="${attack:-none}"
  local log_name="SECAGENT_SUITE=${suite}_SECAGENT_POLICY_MODEL=${SECAGENT_POLICY_MODEL}_SECAGENT_GENERATE=${SECAGENT_GENERATE}_SECAGENT_UPDATE=${SECAGENT_UPDATE:-False}_SECAGENT_IGNORE_UPDATE_ERROR=${SECAGENT_IGNORE_UPDATE_ERROR:-False}_ATTACK=${attack_label}.log"

  if [ -z "$attack" ]; then
    SECAGENT_SUITE="$suite" python -m agentdojo.scripts.benchmark -s "$suite" --model "$model" --logdir "$log_dir" > "$log_dir/$log_name" 2>&1 &
  else
    SECAGENT_SUITE="$suite" python -m agentdojo.scripts.benchmark -s "$suite" --model "$model" --attack "$attack" --logdir "$log_dir" > "$log_dir/$log_name" 2>&1 &
  fi
  echo "started ${suite} attack=${attack_label} -> $log_dir/$log_name"
}

# Examples (uncomment what you need)
# run_suite banking ""
# run_suite slack ""
# run_suite travel ""
# run_suite workspace ""

run_suite banking "important_instructions"
# run_suite slack "important_instructions"
# run_suite travel "important_instructions"
# run_suite workspace "important_instructions"
