#!/usr/bin/env python
"""Check how many Type II-B tasks are registered in the travel suite."""

from agentdojo.default_suites.v1.travel import travel_task_suite

print("=" * 60)
print("Checking Type II-B tasks registration")
print("=" * 60)

# Check original suite (1, 0, 0)
print("\n1. Original suite (version 1.0.0):")
original_suite = travel_task_suite
type_ii_b_original = []
for task_id in original_suite.injection_tasks.keys():
    try:
        task = original_suite.get_injection_task_by_id(task_id)
        av = getattr(task, 'ATTACK_VECTOR', None) or getattr(task.__class__, 'ATTACK_VECTOR', None)
        if av == 'type_ii_b':
            type_ii_b_original.append(task_id)
    except:
        pass

print(f"   Found {len(type_ii_b_original)} Type II-B tasks")
if type_ii_b_original:
    for tid in sorted(type_ii_b_original):
        print(f"     - {tid}")

# Check adversarial suite (1, 2, 0)
print("\n2. Adversarial suite (version 1.2.0):")
adv_suite = travel_task_suite.get_new_version((1, 2, 0))
type_ii_b_adv = []
for task_id in adv_suite.injection_tasks.keys():
    try:
        task = adv_suite.get_injection_task_by_id(task_id)
        av = getattr(task, 'ATTACK_VECTOR', None) or getattr(task.__class__, 'ATTACK_VECTOR', None)
        if av == 'type_ii_b':
            source = getattr(task, 'SOURCE_USER_TASK_ID', None) or getattr(task.__class__, 'SOURCE_USER_TASK_ID', None)
            type_ii_b_adv.append((task_id, source))
    except:
        pass

print(f"   Found {len(type_ii_b_adv)} Type II-B tasks")
if type_ii_b_adv:
    for tid, source in sorted(type_ii_b_adv):
        print(f"     - {tid} -> {source}")

print("\n" + "=" * 60)
print(f"SUMMARY: {len(type_ii_b_adv)}/20 tasks found in adversarial suite")
print("=" * 60)
