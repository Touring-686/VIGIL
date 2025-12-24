"""VIGIL框架的类型定义

定义了VIGIL框架中使用的核心数据结构和类型。
"""

from typing import TypedDict, Literal, Any, Callable
from pydantic import BaseModel


class SecurityConstraint(BaseModel):
    """安全约束定义

    定义了一个可以被验证的安全约束。
    """

    constraint_id: str
    """约束的唯一标识符"""

    constraint_type: Literal["allow", "forbid", "require_confirmation"]
    """约束类型：
    - allow: 允许操作
    - forbid: 禁止操作
    - require_confirmation: 需要确认
    """

    description: str
    """约束的人类可读描述"""

    condition: dict[str, Any] | None = None
    """约束的条件（可选的结构化条件）"""

    priority: int = 5
    """约束的优先级（1-10，数字越小优先级越高）"""

    violation_message: str | None = None
    """违反约束时的错误消息"""


class ConstraintSet(BaseModel):
    """约束集合

    包含针对特定用户查询生成的所有安全约束。
    """

    user_query: str
    """原始用户查询"""

    constraints: list[SecurityConstraint]
    """生成的约束列表"""

    global_rules: list[str] | None = None
    """全局规则（可选）"""

    metadata: dict[str, Any] | None = None
    """额外的元数据"""


class AuditResult(BaseModel):
    """审计结果

    表示对一个工具调用的审计结果。
    """

    allowed: bool
    """是否允许执行"""

    violated_constraints: list[SecurityConstraint] | None = None
    """违反的约束列表"""

    feedback_message: str | None = None
    """反馈消息（用于Reflective Backtracking）"""

    require_confirmation: bool = False
    """是否需要用户确认"""

    metadata: dict[str, Any] | None = None
    """额外的审计元数据"""


class ToolCallInfo(TypedDict):
    """工具调用信息"""

    tool_name: str
    """工具名称"""

    arguments: dict[str, Any]
    """工具参数"""

    tool_call_id: str | None
    """工具调用ID（可选）"""


# 类型别名
ConstraintVerifier = Callable[[ToolCallInfo, SecurityConstraint], bool]
"""约束验证函数类型：接收工具调用信息和约束，返回是否满足约束"""
