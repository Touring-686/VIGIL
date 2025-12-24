#!/bin/bash
# Quick start script for testing VIGIL framework

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}VIGIL Framework - Quick Test Runner${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY environment variable is not set${NC}"
    echo "Please set it with: export OPENAI_API_KEY='your-api-key'"
    exit 1
fi

echo -e "${GREEN}✓ OPENAI_API_KEY is set${NC}"
echo ""

# Parse command line arguments
MODE=${1:-quick}

case $MODE in
    quick)
        echo -e "${YELLOW}Running QUICK TEST mode${NC}"
        echo "This will test banking suite with Type I-A attack only"
        echo ""
        python test_vigil_all_attacks.py --quick-test
        ;;

    single)
        SUITE=${2:-banking}
        ATTACK_TYPE=${3:-type_i_a}
        echo -e "${YELLOW}Running SINGLE ATTACK test${NC}"
        echo "Suite: $SUITE"
        echo "Attack: $ATTACK_TYPE"
        echo ""
        python debug_vigil_single_attack.py --suite $SUITE --attack tool --attack-type $ATTACK_TYPE
        ;;

    suite)
        SUITE=${2:-banking}
        echo -e "${YELLOW}Running FULL SUITE test${NC}"
        echo "Suite: $SUITE"
        echo "This will test all attack types on $SUITE suite"
        echo ""
        python test_vigil_all_attacks.py --suite $SUITE
        ;;

    all)
        echo -e "${YELLOW}Running FULL TEST (all suites, all attacks)${NC}"
        echo -e "${RED}Warning: This will take 2-4 hours!${NC}"
        echo "Press Ctrl+C within 5 seconds to cancel..."
        sleep 5
        echo ""
        python test_vigil_all_attacks.py
        ;;

    important)
        SUITE=${2:-banking}
        echo -e "${YELLOW}Running IMPORTANT INSTRUCTIONS attack test${NC}"
        echo "Suite: $SUITE"
        echo ""
        python debug_vigil_single_attack.py --suite $SUITE --attack important_instructions
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo ""
        echo "Usage: $0 [mode] [options]"
        echo ""
        echo "Modes:"
        echo "  quick              - Quick test (banking + type_i_a only) [default]"
        echo "  single [suite] [attack_type] - Test single attack on a suite"
        echo "  suite [suite]      - Test all attacks on a single suite"
        echo "  all                - Test all attacks on all suites (takes hours!)"
        echo "  important [suite]  - Test important_instructions attack"
        echo ""
        echo "Examples:"
        echo "  $0 quick"
        echo "  $0 single banking type_i_a"
        echo "  $0 single travel type_ii_a"
        echo "  $0 suite banking"
        echo "  $0 all"
        echo "  $0 important slack"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Test completed!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Results are saved in:"
echo "  - vigil_test_results/ (for full tests)"
echo "  - debug_logs/ (for debug tests)"
echo ""
echo "To view results:"
echo "  - Check the JSON files in vigil_test_results/"
echo "  - Check logs in the respective log directories"
