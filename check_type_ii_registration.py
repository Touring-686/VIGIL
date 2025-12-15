#!/usr/bin/env python3
"""Check if Type II-A and Type II-B injection tasks are registered"""

from agentdojo.task_suite.load_suites import get_suite

TRAVEL_SUITE = get_suite(benchmark_version='v1', suite_name='travel')

def print_separator(char="=", length=80):
    print(char * length)

print("\n")
print_separator("=")
print("CHECKING TYPE II INJECTION TASK REGISTRATION")
print_separator("=")
print()

# Get all injection tasks
all_injection_tasks = [task for task in TRAVEL_SUITE.injection_tasks]

# Filter by attack vector
type_ii_a_tasks = [t for t in all_injection_tasks if hasattr(t, 'ATTACK_VECTOR') and t.ATTACK_VECTOR == 'type_ii_a']
type_ii_b_tasks = [t for t in all_injection_tasks if hasattr(t, 'ATTACK_VECTOR') and t.ATTACK_VECTOR == 'type_ii_b']

print(f"Total injection tasks: {len(all_injection_tasks)}")
print()

print_separator("-")
print("TYPE II-A TASKS (Super Tool Attack)")
print_separator("-")
print(f"Found: {len(type_ii_a_tasks)} tasks")
if type_ii_a_tasks:
    for task in type_ii_a_tasks[:5]:  # Show first 5
        task_id = task.ID if hasattr(task, 'ID') else task.__class__.__name__
        source = task.SOURCE_USER_TASK_ID if hasattr(task, 'SOURCE_USER_TASK_ID') else 'N/A'
        print(f"  - {task_id} (source: {source})")
    if len(type_ii_a_tasks) > 5:
        print(f"  ... and {len(type_ii_a_tasks) - 5} more")
else:
    print("  ❌ NO TYPE II-A TASKS FOUND!")
print()

print_separator("-")
print("TYPE II-B TASKS (Honeypot Parameter Trap)")
print_separator("-")
print(f"Found: {len(type_ii_b_tasks)} tasks")
if type_ii_b_tasks:
    for task in type_ii_b_tasks[:5]:  # Show first 5
        task_id = task.ID if hasattr(task, 'ID') else task.__class__.__name__
        source = task.SOURCE_USER_TASK_ID if hasattr(task, 'SOURCE_USER_TASK_ID') else 'N/A'
        print(f"  - {task_id} (source: {source})")
    if len(type_ii_b_tasks) > 5:
        print(f"  ... and {len(type_ii_b_tasks) - 5} more")
else:
    print("  ❌ NO TYPE II-B TASKS FOUND!")
print()

# Check all attack vectors
print_separator("-")
print("ALL ATTACK VECTORS IN SUITE")
print_separator("-")
attack_vectors = {}
for task in all_injection_tasks:
    if hasattr(task, 'ATTACK_VECTOR'):
        vector = task.ATTACK_VECTOR
        attack_vectors[vector] = attack_vectors.get(vector, 0) + 1

for vector, count in sorted(attack_vectors.items()):
    print(f"  {vector}: {count} tasks")
print()

# Summary
print_separator("=")
print("SUMMARY")
print_separator("=")
if type_ii_a_tasks and type_ii_b_tasks:
    print("✅ Both Type II-A and Type II-B tasks are registered!")
elif type_ii_a_tasks:
    print("⚠️  Only Type II-A tasks are registered (Type II-B missing)")
elif type_ii_b_tasks:
    print("⚠️  Only Type II-B tasks are registered (Type II-A missing)")
else:
    print("❌ Neither Type II-A nor Type II-B tasks are registered!")
    print("\nPossible causes:")
    print("  1. Modules not imported in __init__.py")
    print("  2. Circular import issues")
    print("  3. Tasks not decorated with @task_suite.register_injection_task")

print()
