#!/bin/bash

# Slack Suite Attack Execution Scripts
# Based on launch.json configurations for Travel suite

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

WORKSPACE_FOLDER="/Users/justin/BDAA/agent + 安全/code/agentdojo"
MODEL="QWEN3_MAX"
MAX_WORKERS=1

# Function to run benchmark
run_benchmark() {
    local name=$1
    local suite=$2
    local attack_vector_type=$3
    local attack_type=$4
    local logdir=$5
    
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${GREEN}Running: ${name}${NC}"
    echo -e "${BLUE}===========================================${NC}"
    
    cd "$WORKSPACE_FOLDER"
    export PYTHONPATH="${WORKSPACE_FOLDER}/src"
    
    if [ -z "$attack_type" ]; then
        python -m agentdojo.scripts.benchmark \
            --suite "$suite" \
            --benchmark-version adversarial \
            --attack tool_attack \
            --attack-vector-type "$attack_vector_type" \
            --model "$MODEL" \
            --max-workers "$MAX_WORKERS" \
            --force-rerun \
            --logdir "$logdir"
    else
        python -m agentdojo.scripts.benchmark \
            --suite "$suite" \
            --benchmark-version adversarial \
            --attack tool_attack \
            --attack-vector-type "$attack_vector_type" \
            --attack-type "$attack_type" \
            --model "$MODEL" \
            --max-workers "$MAX_WORKERS" \
            --force-rerun \
            --logdir "$logdir"
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ ${name} completed successfully${NC}"
    else
        echo -e "${RED}✗ ${name} failed${NC}"
        return 1
    fi
}

# ============================================================================
# Slack Suite Attacks
# ============================================================================

# Type I-A: Explicit Directive Injection
slack_type_i_a() {
    run_benchmark \
        "Slack | Type I-A | Intent Hijacking" \
        "slack" \
        "type_i_a" \
        "intent_hijecking" \
        "${WORKSPACE_FOLDER}/runs/slack/type_i_a"
}

# Type I-B: Procedural Dependency Trap
slack_type_i_b() {
    run_benchmark \
        "Slack | Type I-B | Procedural Dependency" \
        "slack" \
        "type_i_b" \
        "procedural_dependency" \
        "${WORKSPACE_FOLDER}/runs/slack/type_i_b"
}

# Type II-A: Reasoning Path Short-Circuit
slack_type_ii_a() {
    run_benchmark \
        "Slack | Type II-A | Reasoning Shortcircuit" \
        "slack" \
        "type_ii_a" \
        "" \
        "${WORKSPACE_FOLDER}/runs/slack/type_ii_a"
}

# Type II-B: Induced Parameter Attack
slack_type_ii_b() {
    run_benchmark \
        "Slack | Type II-B | Induced Parameter" \
        "slack" \
        "type_ii_b" \
        "" \
        "${WORKSPACE_FOLDER}/runs/slack/type_ii_b"
}

# Type III-A: SOP Injection
slack_type_iii_a_sop() {
    run_benchmark \
        "Slack | Type III-A | SOP Injection" \
        "slack" \
        "type_iii_a" \
        "sop_injection" \
        "${WORKSPACE_FOLDER}/runs/slack/type_iii_a_sop_injection"
}

# Type III-A: Memory Poisoning
slack_type_iii_a_memory() {
    run_benchmark \
        "Slack | Type III-A | Memory Poisoning" \
        "slack" \
        "type_iii_a" \
        "memory_poisoning" \
        "${WORKSPACE_FOLDER}/runs/slack/type_iii_a_memory_poisoning"
}

# ============================================================================
# Travel Suite Attacks (Reference)
# ============================================================================

# Type I-A: Explicit Directive Injection
travel_type_i_a() {
    run_benchmark \
        "Travel | Type I-A | Intent Hijacking" \
        "travel" \
        "type_i_a" \
        "intent_hijecking" \
        "${WORKSPACE_FOLDER}/runs/travel/type_i_a"
}

# Type I-B: Prerequisite Dependency
travel_type_i_b_prereq() {
    run_benchmark \
        "Travel | Type I-B | Prerequisite" \
        "travel" \
        "type_i_b" \
        "prerequisite_dependency" \
        "${WORKSPACE_FOLDER}/runs/travel/type_i_b_prerequisite"
}

# Type I-B: Postaction Dependency
travel_type_i_b_postaction() {
    run_benchmark \
        "Travel | Type I-B | Postaction" \
        "travel" \
        "type_i_b" \
        "postaction_dependency" \
        "${WORKSPACE_FOLDER}/runs/travel/type_i_b_postaction"
}

# Type II-A: Reasoning Path Short-Circuit
travel_type_ii_a() {
    run_benchmark \
        "Travel | Type II-A" \
        "travel" \
        "type_ii_a" \
        "" \
        "${WORKSPACE_FOLDER}/debug_run/travel/type_ii_a"
}

# Type II-B: Induced Parameter
travel_type_ii_b() {
    run_benchmark \
        "Travel | Type II-B" \
        "travel" \
        "type_ii_b" \
        "" \
        "${WORKSPACE_FOLDER}/runs/travel/type_ii_b"
}

# Type III-A: SOP Injection
travel_type_iii_a_sop() {
    run_benchmark \
        "Travel | Type III-A | SOP Injection" \
        "travel" \
        "type_iii_a" \
        "sop_injection" \
        "${WORKSPACE_FOLDER}/runs/travel/type_iii_a_sop_injection"
}

# Type III-A: SOP Exfiltration
travel_type_iii_a_exfil() {
    run_benchmark \
        "Travel | Type III-A | SOP Exfiltration" \
        "travel" \
        "type_iii_a" \
        "sop_exfiltration" \
        "${WORKSPACE_FOLDER}/runs/travel/type_iii_a_sop_exfiltration"
}

# Type I-A: Parameter Override
travel_type_i_a_param() {
    run_benchmark \
        "Travel | Type I-A | Parameter Override" \
        "travel" \
        "type_i_a" \
        "parameter_override" \
        "${WORKSPACE_FOLDER}/runs/travel/parameter_override_multitools"
}

# ============================================================================
# Main Menu
# ============================================================================

show_menu() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║      Agent Dojo Attack Execution Scripts          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Slack Suite:${NC}"
    echo "  1) Type I-A   - Explicit Directive Injection"
    echo "  2) Type I-B   - Procedural Dependency Trap"
    echo "  3) Type II-A  - Reasoning Path Short-Circuit"
    echo "  4) Type II-B  - Induced Parameter Attack"
    echo "  5) Type III-A - SOP Injection"
    echo "  6) Type III-A - Memory Poisoning"
    echo "  7) Run ALL Slack attacks"
    echo ""
    echo -e "${GREEN}Travel Suite (Reference):${NC}"
    echo "  11) Type I-A   - Intent Hijacking"
    echo "  12) Type I-B   - Prerequisite Dependency"
    echo "  13) Type I-B   - Postaction Dependency"
    echo "  14) Type II-A  - Reasoning Shortcircuit"
    echo "  15) Type II-B  - Induced Parameter"
    echo "  16) Type III-A - SOP Injection"
    echo "  17) Type III-A - SOP Exfiltration"
    echo "  18) Type I-A   - Parameter Override"
    echo "  19) Run ALL Travel attacks"
    echo ""
    echo "  0) Exit"
    echo ""
}

run_all_slack() {
    echo -e "${BLUE}Running all Slack attacks...${NC}"
    slack_type_i_a
    slack_type_i_b
    slack_type_ii_a
    slack_type_ii_b
    slack_type_iii_a_sop
    slack_type_iii_a_memory
    echo -e "${GREEN}All Slack attacks completed!${NC}"
}

run_all_travel() {
    echo -e "${BLUE}Running all Travel attacks...${NC}"
    travel_type_i_a
    travel_type_i_b_prereq
    travel_type_i_b_postaction
    travel_type_ii_a
    travel_type_ii_b
    travel_type_iii_a_sop
    travel_type_iii_a_exfil
    travel_type_i_a_param
    echo -e "${GREEN}All Travel attacks completed!${NC}"
}

# ============================================================================
# Main Execution
# ============================================================================

if [ $# -eq 0 ]; then
    # Interactive mode
    while true; do
        show_menu
        read -p "Select an option: " choice
        case $choice in
            1) slack_type_i_a ;;
            2) slack_type_i_b ;;
            3) slack_type_ii_a ;;
            4) slack_type_ii_b ;;
            5) slack_type_iii_a_sop ;;
            6) slack_type_iii_a_memory ;;
            7) run_all_slack ;;
            11) travel_type_i_a ;;
            12) travel_type_i_b_prereq ;;
            13) travel_type_i_b_postaction ;;
            14) travel_type_ii_a ;;
            15) travel_type_ii_b ;;
            16) travel_type_iii_a_sop ;;
            17) travel_type_iii_a_exfil ;;
            18) travel_type_i_a_param ;;
            19) run_all_travel ;;
            0) echo "Exiting..."; exit 0 ;;
            *) echo -e "${RED}Invalid option${NC}" ;;
        esac
        echo ""
        read -p "Press Enter to continue..."
    done
else
    # Command line mode
    case $1 in
        slack-i-a) slack_type_i_a ;;
        slack-i-b) slack_type_i_b ;;
        slack-ii-a) slack_type_ii_a ;;
        slack-ii-b) slack_type_ii_b ;;
        slack-iii-a-sop) slack_type_iii_a_sop ;;
        slack-iii-a-mem) slack_type_iii_a_memory ;;
        slack-all) run_all_slack ;;
        travel-i-a) travel_type_i_a ;;
        travel-i-b-prereq) travel_type_i_b_prereq ;;
        travel-i-b-post) travel_type_i_b_postaction ;;
        travel-ii-a) travel_type_ii_a ;;
        travel-ii-b) travel_type_ii_b ;;
        travel-iii-a-sop) travel_type_iii_a_sop ;;
        travel-iii-a-exfil) travel_type_iii_a_exfil ;;
        travel-i-a-param) travel_type_i_a_param ;;
        travel-all) run_all_travel ;;
        *)
            echo "Usage: $0 [option]"
            echo ""
            echo "Slack options:"
            echo "  slack-i-a          Type I-A attack"
            echo "  slack-i-b          Type I-B attack"
            echo "  slack-ii-a         Type II-A attack"
            echo "  slack-ii-b         Type II-B attack"
            echo "  slack-iii-a-sop    Type III-A SOP injection"
            echo "  slack-iii-a-mem    Type III-A memory poisoning"
            echo "  slack-all          All Slack attacks"
            echo ""
            echo "Travel options:"
            echo "  travel-i-a         Type I-A attack"
            echo "  travel-i-b-prereq  Type I-B prerequisite"
            echo "  travel-i-b-post    Type I-B postaction"
            echo "  travel-ii-a        Type II-A attack"
            echo "  travel-ii-b        Type II-B attack"
            echo "  travel-iii-a-sop   Type III-A SOP injection"
            echo "  travel-iii-a-exfil Type III-A SOP exfiltration"
            echo "  travel-i-a-param   Type I-A parameter override"
            echo "  travel-all         All Travel attacks"
            echo ""
            echo "Run without arguments for interactive mode"
            exit 1
            ;;
    esac
fi
