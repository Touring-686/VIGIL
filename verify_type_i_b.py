#!/usr/bin/env python3
"""Verify the workspace type_i_b_injection_tasks.py file."""

import ast
import re
import sys

def verify_file():
    filepath = 'src/agentdojo/adverseral_tool/workspace/type_i_b_injection_tasks.py'
    
    print("="*70)
    print("Verifying Workspace Type I-B Injection Tasks")
    print("="*70)
    print()
    
    # 1. Check syntax
    print("1. Checking Python syntax...")
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        ast.parse(code)
        print("   ✓ Syntax is valid")
    except SyntaxError as e:
        print(f"   ✗ Syntax error: {e}")
        return False
    
    # 2. Check task count
    print("\n2. Checking task count...")
    all_tasks = re.findall(r'class InjectionTask(\d+)', code)
    print(f"   ✓ Found {len(all_tasks)} tasks")
    
    # 3. Check prerequisite tasks
    print("\n3. Checking prerequisite_dependency tasks...")
    prereq_tasks = re.findall(r'class InjectionTask(42[0-3]\d).*?ATTACK_TYPE = "prerequisite_dependency"', code, re.DOTALL)
    expected_prereq = [str(4200 + i) for i in range(40)]
    missing_prereq = set(expected_prereq) - set(prereq_tasks)
    
    if missing_prereq:
        print(f"   ✗ Missing tasks: {sorted(missing_prereq)}")
        return False
    print(f"   ✓ All 40 prerequisite tasks present (4200-4239)")
    
    # 4. Check postaction tasks
    print("\n4. Checking postaction_dependency tasks...")
    post_tasks = re.findall(r'class InjectionTask(42[4-7]\d).*?ATTACK_TYPE = "postaction_dependency"', code, re.DOTALL)
    expected_post = [str(4240 + i) for i in range(40)]
    missing_post = set(expected_post) - set(post_tasks)
    
    if missing_post:
        print(f"   ✗ Missing tasks: {sorted(missing_post)}")
        return False
    print(f"   ✓ All 40 postaction tasks present (4240-4279)")
    
    # 5. Check decorator count
    print("\n5. Checking task registration...")
    decorator_count = code.count('@task_suite.register_injection_task')
    if decorator_count != 80:
        print(f"   ✗ Expected 80 decorators, found {decorator_count}")
        return False
    print(f"   ✓ All 80 tasks properly decorated")
    
    # 6. Check method implementations
    print("\n6. Checking method implementations...")
    ground_truth_count = code.count('def ground_truth(')
    security_count = code.count('def security_from_traces(')
    
    if ground_truth_count != 80 or security_count != 80:
        print(f"   ✗ Method count mismatch")
        print(f"      ground_truth: {ground_truth_count}/80")
        print(f"      security_from_traces: {security_count}/80")
        return False
    print(f"   ✓ All methods implemented (ground_truth: 80, security_from_traces: 80)")
    
    # 7. Check malicious tools
    print("\n7. Checking malicious tools configuration...")
    verify_count = code.count('"verify_user_session"')
    audit_count = code.count('"audit_read_access"')
    
    if verify_count < 80 or audit_count < 80:
        print(f"   ✗ Malicious tools not configured for all tasks")
        print(f"      verify_user_session: {verify_count}/80+")
        print(f"      audit_read_access: {audit_count}/80+")
        return False
    print(f"   ✓ All tasks have proper malicious tools configured")
    
    print()
    print("="*70)
    print("✨ VERIFICATION PASSED - All checks successful!")
    print("="*70)
    return True

if __name__ == '__main__':
    success = verify_file()
    sys.exit(0 if success else 1)
