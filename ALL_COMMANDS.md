# All 24 Benchmark Commands

This document contains all 24 individual benchmark commands organized by suite and attack type.

## Base Command Structure
```bash
python -m agentdojo.scripts.benchmark \
    --suite <SUITE> \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type <VECTOR> \
    [--attack-type <TYPE>] \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/<TASK>.out \
    2> logs/<TASK>.log
```

---

## Type I-A: parameter_override (4 tasks)

### 1. travel + type_i_a + parameter_override
```bash
python -m agentdojo.scripts.benchmark \
    --suite travel \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_a \
    --attack-type parameter_override \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/travel_type_i_a_parameter_override.out \
    2> logs/travel_type_i_a_parameter_override.log
```

### 2. workspace + type_i_a + parameter_override
```bash
python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_a \
    --attack-type parameter_override \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/workspace_type_i_a_parameter_override.out \
    2> logs/workspace_type_i_a_parameter_override.log
```

### 3. banking + type_i_a + parameter_override
```bash
python -m agentdojo.scripts.benchmark \
    --suite banking \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_a \
    --attack-type parameter_override \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/banking_type_i_a_parameter_override.out \
    2> logs/banking_type_i_a_parameter_override.log
```

### 4. slack + type_i_a + parameter_override
```bash
python -m agentdojo.scripts.benchmark \
    --suite slack \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_a \
    --attack-type parameter_override \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/slack_type_i_a_parameter_override.out \
    2> logs/slack_type_i_a_parameter_override.log
```

---

## Type I-B: prerequisite_dependency (4 tasks)

### 5. travel + type_i_b + prerequisite_dependency
```bash
python -m agentdojo.scripts.benchmark \
    --suite travel \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type prerequisite_dependency \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/travel_type_i_b_prerequisite_dependency.out \
    2> logs/travel_type_i_b_prerequisite_dependency.log
```

### 6. workspace + type_i_b + prerequisite_dependency
```bash
python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type prerequisite_dependency \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/workspace_type_i_b_prerequisite_dependency.out \
    2> logs/workspace_type_i_b_prerequisite_dependency.log
```

### 7. banking + type_i_b + prerequisite_dependency
```bash
python -m agentdojo.scripts.benchmark \
    --suite banking \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type prerequisite_dependency \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/banking_type_i_b_prerequisite_dependency.out \
    2> logs/banking_type_i_b_prerequisite_dependency.log
```

### 8. slack + type_i_b + prerequisite_dependency
```bash
python -m agentdojo.scripts.benchmark \
    --suite slack \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type prerequisite_dependency \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/slack_type_i_b_prerequisite_dependency.out \
    2> logs/slack_type_i_b_prerequisite_dependency.log
```

---

## Type I-B: postaction_dependency (4 tasks)

### 9. travel + type_i_b + postaction_dependency
```bash
python -m agentdojo.scripts.benchmark \
    --suite travel \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type postaction_dependency \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/travel_type_i_b_postaction_dependency.out \
    2> logs/travel_type_i_b_postaction_dependency.log
```

### 10. workspace + type_i_b + postaction_dependency
```bash
python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type postaction_dependency \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/workspace_type_i_b_postaction_dependency.out \
    2> logs/workspace_type_i_b_postaction_dependency.log
```

### 11. banking + type_i_b + postaction_dependency
```bash
python -m agentdojo.scripts.benchmark \
    --suite banking \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type postaction_dependency \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/banking_type_i_b_postaction_dependency.out \
    2> logs/banking_type_i_b_postaction_dependency.log
```

### 12. slack + type_i_b + postaction_dependency
```bash
python -m agentdojo.scripts.benchmark \
    --suite slack \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_i_b \
    --attack-type postaction_dependency \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/slack_type_i_b_postaction_dependency.out \
    2> logs/slack_type_i_b_postaction_dependency.log
```

---

## Type II-A: no attack-type (4 tasks)

### 13. travel + type_ii_a
```bash
python -m agentdojo.scripts.benchmark \
    --suite travel \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_a \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/travel_type_ii_a.out \
    2> logs/travel_type_ii_a.log
```

### 14. workspace + type_ii_a
```bash
python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_a \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/workspace_type_ii_a.out \
    2> logs/workspace_type_ii_a.log
```

### 15. banking + type_ii_a
```bash
python -m agentdojo.scripts.benchmark \
    --suite banking \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_a \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/banking_type_ii_a.out \
    2> logs/banking_type_ii_a.log
```

### 16. slack + type_ii_a
```bash
python -m agentdojo.scripts.benchmark \
    --suite slack \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_a \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/slack_type_ii_a.out \
    2> logs/slack_type_ii_a.log
```

---

## Type II-B: no attack-type (4 tasks)

### 17. travel + type_ii_b
```bash
python -m agentdojo.scripts.benchmark \
    --suite travel \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_b \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/travel_type_ii_b.out \
    2> logs/travel_type_ii_b.log
```

### 18. workspace + type_ii_b
```bash
python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_b \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/workspace_type_ii_b.out \
    2> logs/workspace_type_ii_b.log
```

### 19. banking + type_ii_b
```bash
python -m agentdojo.scripts.benchmark \
    --suite banking \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_b \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/banking_type_ii_b.out \
    2> logs/banking_type_ii_b.log
```

### 20. slack + type_ii_b
```bash
python -m agentdojo.scripts.benchmark \
    --suite slack \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_ii_b \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/slack_type_ii_b.out \
    2> logs/slack_type_ii_b.log
```

---

## Type III-A: sop_exfiltration (4 tasks)

### 21. travel + type_iii_a + sop_exfiltration
```bash
python -m agentdojo.scripts.benchmark \
    --suite travel \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_iii_a \
    --attack-type sop_exfiltration \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/travel_type_iii_a_sop_exfiltration.out \
    2> logs/travel_type_iii_a_sop_exfiltration.log
```

### 22. workspace + type_iii_a + sop_exfiltration
```bash
python -m agentdojo.scripts.benchmark \
    --suite workspace \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_iii_a \
    --attack-type sop_exfiltration \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/workspace_type_iii_a_sop_exfiltration.out \
    2> logs/workspace_type_iii_a_sop_exfiltration.log
```

### 23. banking + type_iii_a + sop_exfiltration
```bash
python -m agentdojo.scripts.benchmark \
    --suite banking \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_iii_a \
    --attack-type sop_exfiltration \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/banking_type_iii_a_sop_exfiltration.out \
    2> logs/banking_type_iii_a_sop_exfiltration.log
```

### 24. slack + type_iii_a + sop_exfiltration
```bash
python -m agentdojo.scripts.benchmark \
    --suite slack \
    --benchmark-version adversarial \
    --attack tool_attack \
    --attack-vector-type type_iii_a \
    --attack-type sop_exfiltration \
    --defense melon \
    --model QWEN3_MAX \
    --max-workers 1 \
    --force-rerun \
    --logdir ./runs \
    > outputs/slack_type_iii_a_sop_exfiltration.out \
    2> logs/slack_type_iii_a_sop_exfiltration.log
```

---

## Quick Reference: Using the Helper Scripts

### Run all 24 tasks in parallel:
```bash
chmod +x run_all_benchmarks.sh
./run_all_benchmarks.sh
```

### Run a single task:
```bash
chmod +x run_single_task.sh
./run_single_task.sh <suite> <attack_vector> [attack_type]
```

Examples:
```bash
./run_single_task.sh travel type_i_a parameter_override
./run_single_task.sh workspace type_ii_a
./run_single_task.sh banking type_iii_a sop_exfiltration
```

### Monitor running tasks:
```bash
# Watch a specific log in real-time
tail -f logs/travel_type_i_a_parameter_override.log

# Use the monitoring script
chmod +x monitor_tasks.sh
./monitor_tasks.sh

# Check all running tasks
ps aux | grep benchmark

# Kill all running tasks
pkill -f 'agentdojo.scripts.benchmark'
```

---

## Output Files

All outputs and logs will be saved in:
- `outputs/` - Standard output for each task
- `logs/` - Error logs for each task
- `runs/` - Benchmark results (JSON format)

File naming pattern: `<suite>_<attack_vector>_[attack_type].{out,log}`
