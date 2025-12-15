#!/usr/bin/env python3
"""
统计 type_i_a_injection_tasks.py 中的 parameter_override injection tasks
"""

# 读取文件内容
file_path = "/Users/justin/BDAA/agent + 安全/code/agentdojo/src/agentdojo/adverseral_tool/travel/type_i_a_injection_tasks.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("=" * 80)
print("Parameter Override Injection Tasks 统计")
print("=" * 80)

# 统计所有 InjectionTask10XX 类
import re

# 查找所有类定义
class_pattern = r'class (InjectionTask10\d{2})\(_BaseAdversarialInjection\):'
classes = re.findall(class_pattern, content)

print(f"\n找到 {len(classes)} 个 InjectionTask 类:\n")
for i, cls in enumerate(sorted(classes), 1):
    print(f"{i:2d}. {cls}")

# 查找带装饰器的类
decorator_pattern = r'@task_suite\.register_injection_task\s+class (InjectionTask10\d{2})\('
decorated_classes = re.findall(decorator_pattern, content)

print(f"\n\n带 @task_suite.register_injection_task 装饰器的类: {len(decorated_classes)} 个\n")
for i, cls in enumerate(sorted(decorated_classes), 1):
    print(f"{i:2d}. {cls}")

# 检查缺少装饰器的类
missing_decorator = set(classes) - set(decorated_classes)
if missing_decorator:
    print(f"\n\n⚠️  缺少装饰器的类: {len(missing_decorator)} 个\n")
    for cls in sorted(missing_decorator):
        print(f"  - {cls}")
else:
    print(f"\n\n✅ 所有类都有装饰器!")

# 检查每个类的属性
print("\n" + "=" * 80)
print("检查类属性")
print("=" * 80)

for cls_name in sorted(classes):
    # 查找类定义开始
    cls_match = re.search(rf'class {cls_name}\(_BaseAdversarialInjection\):(.+?)(?=\n    @task_suite\.register_injection_task|class \w+|def _register_parameter_override|$)', content, re.DOTALL)
    
    if cls_match:
        cls_content = cls_match.group(1)
        
        # 检查必要属性
        has_source = bool(re.search(r'SOURCE_USER_TASK_ID\s*=', cls_content))
        has_attack_type = bool(re.search(r'ATTACK_TYPE\s*=', cls_content))
        has_attack_vector = bool(re.search(r'ATTACK_VECTOR\s*=', cls_content))
        has_malicious_tools = bool(re.search(r'MALICIOUS_TOOLS\s*=', cls_content))
        has_ground_truth = bool(re.search(r'def ground_truth\(', cls_content))
        has_security_from_traces = bool(re.search(r'def security_from_traces\(', cls_content))
        
        status = "✅" if all([has_source, has_attack_type, has_attack_vector, 
                             has_malicious_tools, has_ground_truth, 
                             has_security_from_traces]) else "❌"
        
        # 提取 SOURCE_USER_TASK_ID
        source_match = re.search(r'SOURCE_USER_TASK_ID\s*=\s*"([^"]+)"', cls_content)
        source_id = source_match.group(1) if source_match else "N/A"
        
        # 提取 MALICIOUS_TOOLS 数量
        tools_match = re.search(r'MALICIOUS_TOOLS\s*=\s*\[(.*?)\]', cls_content, re.DOTALL)
        if tools_match:
            tools_count = tools_match.group(1).count('{"name"')
        else:
            tools_count = 0
        
        print(f"{status} {cls_name:20s} -> {source_id:15s} | Tools: {tools_count}")

print("\n" + "=" * 80)
print("✅ 统计完成")
print("=" * 80)
