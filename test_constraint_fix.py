"""测试修复后的约束验证逻辑

测试多个场景以确保修复正确
"""

import sys
sys.path.insert(0, 'src')

from vigil_agent.config import get_vigil_config
from vigil_agent.runtime_auditor import RuntimeAuditor
from vigil_agent.types import SecurityConstraint, ConstraintSet, ToolCallInfo

config = get_vigil_config("balanced", "gpt-4o")

def test_case(name, constraints, tool_call, expected_allowed):
    """测试一个场景"""
    print(f"\n{'='*80}")
    print(f"测试场景: {name}")
    print(f"{'='*80}")

    constraint_set = ConstraintSet(
        user_query="Test query",
        constraints=constraints,
        global_rules=[]
    )

    auditor = RuntimeAuditor(config, constraint_set)
    result = auditor.audit_tool_call(tool_call)

    print(f"工具调用: {tool_call['tool_name']}({tool_call['arguments']})")
    print(f"约束数量: {len(constraints)}")
    for c in constraints:
        print(f"  - [{c.constraint_type}] {c.description}")

    status = "✓ PASS" if result.allowed == expected_allowed else "✗ FAIL"
    print(f"\n结果: allowed={result.allowed}, expected={expected_allowed} {status}")

    if not result.allowed and result.violated_constraints:
        print(f"违反的约束: {[c.description for c in result.violated_constraints]}")

    return result.allowed == expected_allowed


# 测试场景 1: 特定 allow 应该覆盖宽泛 forbid
test1_constraints = [
    SecurityConstraint(
        constraint_id="allow_specific",
        constraint_type="allow",
        description="Allow reading bill-december-2023.txt",
        condition={"operation": "READ", "target": "bill-december-2023.txt"},
        priority=3
    ),
    SecurityConstraint(
        constraint_id="forbid_general",
        constraint_type="forbid",
        description="Forbid all READ operations",
        condition={"operation": "READ"},
        priority=2
    )
]

test1_call = {
    "tool_name": "read_file",
    "arguments": {"file_path": "bill-december-2023.txt"},
    "tool_call_id": "test1"
}

result1 = test_case(
    "特定 allow 覆盖宽泛 forbid",
    test1_constraints,
    test1_call,
    expected_allowed=True
)

# 测试场景 2: 不在 allow 列表中的应该被 forbid
test2_call = {
    "tool_name": "read_file",
    "arguments": {"file_path": "other-file.txt"},
    "tool_call_id": "test2"
}

result2 = test_case(
    "不在 allow 列表中应该被 block",
    test1_constraints,  # 使用相同的约束
    test2_call,
    expected_allowed=False
)

# 测试场景 3: 不同 operation 的约束不应该相互覆盖
test3_constraints = [
    SecurityConstraint(
        constraint_id="allow_read",
        constraint_type="allow",
        description="Allow READ operations",
        condition={"operation": "READ"},
        priority=3
    ),
    SecurityConstraint(
        constraint_id="forbid_write",
        constraint_type="forbid",
        description="Forbid WRITE operations",
        condition={"operation": "WRITE"},
        priority=2
    )
]

test3_call = {
    "tool_name": "write_file",
    "arguments": {"file_path": "test.txt", "content": "test"},
    "tool_call_id": "test3"
}

result3 = test_case(
    "不同 operation 的约束不相互影响",
    test3_constraints,
    test3_call,
    expected_allowed=False  # WRITE 应该被 forbid
)

# 测试场景 4: 没有匹配约束的应该允许（hybrid mode）
test4_call = {
    "tool_name": "get_balance",
    "arguments": {},
    "tool_call_id": "test4"
}

result4 = test_case(
    "没有匹配约束应该允许",
    test3_constraints,  # 只有 READ/WRITE 约束
    test4_call,
    expected_allowed=True  # get_balance (READ) 匹配 allow_read
)

# 总结
print(f"\n{'='*80}")
print("测试总结")
print(f"{'='*80}")
all_passed = all([result1, result2, result3, result4])
print(f"总共 4 个测试，{'全部通过 ✓' if all_passed else '有失败 ✗'}")
