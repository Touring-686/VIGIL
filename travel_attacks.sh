#!/bin/bash

# Travel Suite Attack Execution Scripts
# Based on launch.json configurations

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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
    
    echo ""
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${GREEN}Running: ${name}${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${YELLOW}Suite: ${suite}${NC}"
    echo -e "${YELLOW}Attack Vector: ${attack_vector_type}${NC}"
    echo -e "${YELLOW}Attack Type: ${attack_type:-N/A}${NC}"
    echo -e "${YELLOW}Model: ${MODEL}${NC}"
    echo -e "${YELLOW}Log Directory: ${logdir}${NC}"
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
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ ${name} completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ ${name} failed with exit code ${exit_code}${NC}"
        return 1
    fi
}

# ============================================================================
# Travel Suite Attacks
# ============================================================================

# Type I-A: Explicit Directive Injection (Intent Hijacking)
type_i_a_intent_hijacking() {
    run_benchmark \
        "Travel | Type I-A | Intent Hijacking" \
        "travel" \
        "type_i_a" \
        "intent_hijecking" \
        "${WORKSPACE_FOLDER}/runs/travel/type_i_a"
}

# Type I-A: Parameter Override
type_i_a_parameter_override() {
    run_benchmark \
        "Travel | Type I-A | Parameter Override" \
        "travel" \
        "type_i_a" \
        "parameter_override" \
        "${WORKSPACE_FOLDER}/runs/travel/parameter_override_multitools"
}

# Type I-B: Prerequisite Dependency
type_i_b_prerequisite() {
    run_benchmark \
        "Travel | Type I-B | Prerequisite Dependency" \
        "travel" \
        "type_i_b" \
        "prerequisite_dependency" \
        "${WORKSPACE_FOLDER}/runs/travel/type_i_b_prerequisite"
}

# Type I-B: Postaction Dependency
type_i_b_postaction() {
    run_benchmark \
        "Travel | Type I-B | Postaction Dependency" \
        "travel" \
        "type_i_b" \
        "postaction_dependency" \
        "${WORKSPACE_FOLDER}/runs/travel/type_i_b_postaction"
}

# Type II-A: Reasoning Path Short-Circuit
type_ii_a() {
    run_benchmark \
        "Travel | Type II-A | Reasoning Shortcircuit" \
        "travel" \
        "type_ii_a" \
        "" \
        "${WORKSPACE_FOLDER}/debug_run/travel/type_ii_a"
}

# Type II-B: Induced Parameter Attack
type_ii_b() {
    run_benchmark \
        "Travel | Type II-B | Induced Parameter" \
        "travel" \
        "type_ii_b" \
        "" \
        "${WORKSPACE_FOLDER}/runs/travel/type_ii_b"
}

# Type III-A: SOP Injection
type_iii_a_sop_injection() {
    run_benchmark \
        "Travel | Type III-A | SOP Injection" \
        "travel" \
        "type_iii_a" \
        "sop_injection" \
        "${WORKSPACE_FOLDER}/runs/travel/type_iii_a_sop_injection"
}

# Type III-A: SOP Exfiltration
type_iii_a_sop_exfiltration() {
    run_benchmark \
        "Travel | Type III-A | SOP Exfiltration" \
        "travel" \
        "type_iii_a" \
        "sop_exfiltration" \
        "${WORKSPACE_FOLDER}/runs/travel/type_iii_a_sop_exfiltration"
}

# ============================================================================
# Batch Execution Functions
# ============================================================================

# Run all Type I-A attacks
run_all_type_i_a() {
    echo -e "${BLUE}Running all Type I-A attacks...${NC}"
    type_i_a_intent_hijacking
    type_i_a_parameter_override
    echo -e "${GREEN}All Type I-A attacks completed!${NC}"
}

# Run all Type I-B attacks
run_all_type_i_b() {
    echo -e "${BLUE}Running all Type I-B attacks...${NC}"
    type_i_b_prerequisite
    type_i_b_postaction
    echo -e "${GREEN}All Type I-B attacks completed!${NC}"
}

# Run all Type II attacks
run_all_type_ii() {
    echo -e "${BLUE}Running all Type II attacks...${NC}"
    type_ii_a
    type_ii_b
    echo -e "${GREEN}All Type II attacks completed!${NC}"
}

# Run all Type III-A attacks
run_all_type_iii_a() {
    echo -e "${BLUE}Running all Type III-A attacks...${NC}"
    type_iii_a_sop_injection
    type_iii_a_sop_exfiltration
    echo -e "${GREEN}All Type III-A attacks completed!${NC}"
}

# Run ALL Travel suite attacks
run_all_attacks() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Running ALL Travel Suite Attacks                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
    
    local start_time=$(date +%s)
    local failed_count=0
    
    type_i_a_intent_hijacking || ((failed_count++))
    type_i_a_parameter_override || ((failed_count++))
    type_i_b_prerequisite || ((failed_count++))
    type_i_b_postaction || ((failed_count++))
    type_ii_a || ((failed_count++))
    type_ii_b || ((failed_count++))
    type_iii_a_sop_injection || ((failed_count++))
    type_iii_a_sop_exfiltration || ((failed_count++))
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Execution Summary                                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
    echo -e "${YELLOW}Total attacks: 8${NC}"
    echo -e "${GREEN}Successful: $((8 - failed_count))${NC}"
    if [ $failed_count -gt 0 ]; then
        echo -e "${RED}Failed: ${failed_count}${NC}"
    fi
    echo -e "${YELLOW}Total time: ${duration}s${NC}"
    echo ""
    
    if [ $failed_count -eq 0 ]; then
        echo -e "${GREEN}✓ All Travel suite attacks completed successfully!${NC}"
    else
        echo -e "${RED}✗ Some attacks failed. Check logs for details.${NC}"
    fi
}

# ============================================================================
# Main Menu
# ============================================================================

show_menu() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║      Travel Suite Attack Execution Menu           ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Type I-A: Explicit Directive Injection${NC}"
    echo "  1) Intent Hijacking"
    echo "  2) Parameter Override"
    echo "  3) Run all Type I-A attacks"
    echo ""
    echo -e "${GREEN}Type I-B: Procedural Dependency Trap${NC}"
    echo "  4) Prerequisite Dependency"
    echo "  5) Postaction Dependency"
    echo "  6) Run all Type I-B attacks"
    echo ""
    echo -e "${GREEN}Type II: Advanced Attacks${NC}"
    echo "  7) Type II-A: Reasoning Path Short-Circuit"
    echo "  8) Type II-B: Induced Parameter Attack"
    echo "  9) Run all Type II attacks"
    echo ""
    echo -e "${GREEN}Type III-A: SOP-based Attacks${NC}"
    echo "  10) SOP Injection"
    echo "  11) SOP Exfiltration"
    echo "  12) Run all Type III-A attacks"
    echo ""
    echo -e "${YELLOW}Batch Operations${NC}"
    echo "  99) Run ALL Travel attacks (8 total)"
    echo ""
    echo "  0) Exit"
    echo ""
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
            1) type_i_a_intent_hijacking ;;
            2) type_i_a_parameter_override ;;
            3) run_all_type_i_a ;;
            4) type_i_b_prerequisite ;;
            5) type_i_b_postaction ;;
            6) run_all_type_i_b ;;
            7) type_ii_a ;;
            8) type_ii_b ;;
            9) run_all_type_ii ;;
            10) type_iii_a_sop_injection ;;
            11) type_iii_a_sop_exfiltration ;;
            12) run_all_type_iii_a ;;
            99) run_all_attacks ;;
            0) echo -e "${GREEN}Exiting...${NC}"; exit 0 ;;
            *) echo -e "${RED}Invalid option. Please try again.${NC}" ;;
        esac
        echo ""
        read -p "Press Enter to continue..."
    done
else
    # Command line mode
    case $1 in
        # Individual attacks
        i-a-intent) type_i_a_intent_hijacking ;;
        i-a-param) type_i_a_parameter_override ;;
        i-b-prereq) type_i_b_prerequisite ;;
        i-b-post) type_i_b_postaction ;;
        ii-a) type_ii_a ;;
        ii-b) type_ii_b ;;
        iii-a-sop) type_iii_a_sop_injection ;;
        iii-a-exfil) type_iii_a_sop_exfiltration ;;
        
        # Batch operations
        i-a) run_all_type_i_a ;;
        i-b) run_all_type_i_b ;;
        ii) run_all_type_ii ;;
        iii-a) run_all_type_iii_a ;;
        all) run_all_attacks ;;
        
        # Help
        -h|--help|help)
            echo "Travel Suite Attack Execution Script"
            echo ""
            echo "Usage: $0 [option]"
            echo ""
            echo "Individual Attacks:"
            echo "  i-a-intent      Type I-A: Intent Hijacking"
            echo "  i-a-param       Type I-A: Parameter Override"
            echo "  i-b-prereq      Type I-B: Prerequisite Dependency"
            echo "  i-b-post        Type I-B: Postaction Dependency"
            echo "  ii-a            Type II-A: Reasoning Shortcircuit"
            echo "  ii-b            Type II-B: Induced Parameter"
            echo "  iii-a-sop       Type III-A: SOP Injection"
            echo "  iii-a-exfil     Type III-A: SOP Exfiltration"
            echo ""
            echo "Batch Operations:"
            echo "  i-a             Run all Type I-A attacks"
            echo "  i-b             Run all Type I-B attacks"
            echo "  ii              Run all Type II attacks"
            echo "  iii-a           Run all Type III-A attacks"
            echo "  all             Run ALL Travel attacks (8 total)"
            echo ""
            echo "Other:"
            echo "  -h, --help      Show this help message"
            echo ""
            echo "Run without arguments for interactive menu mode"
            ;;
        
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use '$0 --help' for usage information"
            exit 1
            ;;
    esac
fi
