"""
Progent 日志配置和格式化工具
用于控制日志输出的详细程度和格式
"""
import sys
import os
from typing import Any, Dict, List
from datetime import datetime

# 日志级别
LOG_LEVEL = os.getenv("PROGENT_LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR
VERBOSE = os.getenv("PROGENT_VERBOSE", "False").lower() == "true"

# ANSI颜色代码
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def format_section_header(text: str, char: str = "=", width: int = 80) -> str:
    """格式化章节标题"""
    return f"\n{char * width}\n{text.center(width)}\n{char * width}"


def format_subsection_header(text: str, width: int = 80) -> str:
    """格式化子章节标题"""
    return f"\n{'-' * width}\n  {text}\n{'-' * width}"


def format_task_header(suite: str, user_task: str, injection_task: str,
                       current: int, total: int) -> str:
    """格式化任务标题"""
    return f"""
{'=' * 80}
  任务 [{current}/{total}]
  Suite: {suite}  |  User Task: {user_task}  |  Injection: {injection_task}
{'=' * 80}
"""


def log_info(message: str, prefix: str = "ℹ"):
    """输出信息日志"""
    if LOG_LEVEL in ["DEBUG", "INFO"]:
        print(f"{Colors.OKCYAN}{prefix}{Colors.ENDC} {message}", file=sys.stderr)


def log_success(message: str, prefix: str = "✓"):
    """输出成功日志"""
    print(f"{Colors.OKGREEN}{prefix}{Colors.ENDC} {message}", file=sys.stderr)


def log_warning(message: str, prefix: str = "⚠"):
    """输出警告日志"""
    if LOG_LEVEL in ["DEBUG", "INFO", "WARNING"]:
        print(f"{Colors.WARNING}{prefix}{Colors.ENDC} {message}", file=sys.stderr)


def log_error(message: str, prefix: str = "✗"):
    """输出错误日志"""
    print(f"{Colors.FAIL}{prefix}{Colors.ENDC} {message}", file=sys.stderr)


def log_debug(message: str, prefix: str = "🔍"):
    """输出调试日志"""
    if LOG_LEVEL == "DEBUG":
        print(f"{Colors.OKBLUE}{prefix}{Colors.ENDC} {message}", file=sys.stderr)


def log_tool_update(tool_count: int, show_details: bool = False):
    """记录工具更新（简化版）"""
    if not VERBOSE and not show_details:
        log_debug(f"可用工具已更新 ({tool_count} 个工具)")
    else:
        log_info(f"可用工具已更新 ({tool_count} 个工具)")


def log_policy_update(policy: Dict, show_details: bool = False):
    """记录策略更新（简化版）"""
    if policy is None:
        log_debug("安全策略已重置")
        return

    tool_count = len(policy)
    restricted_count = sum(1 for rules in policy.values() if any(r[1] == 1 for r in rules))

    if not VERBOSE and not show_details:
        log_debug(f"安全策略已更新: {tool_count} 个工具, {restricted_count} 个受限")
    else:
        log_info(f"安全策略已更新: {tool_count} 个工具, {restricted_count} 个受限")
        if VERBOSE:
            for tool_name, rules in policy.items():
                for rule in rules:
                    status = "受限" if rule[1] == 1 else "允许"
                    constraints = rule[2] if rule[2] else "无约束"
                    log_debug(f"  - {tool_name}: {status}, 约束: {constraints}")


def log_policy_generation(query: str, success: bool = True, tokens: tuple = None):
    """记录策略生成"""
    query_preview = query[:60] + "..." if len(query) > 60 else query

    if success:
        log_success(f"已为查询生成安全策略: {query_preview}")
        if tokens and VERBOSE:
            log_debug(f"  Token 使用: completion={tokens[0]}, prompt={tokens[1]}")
    else:
        log_error(f"策略生成失败: {query_preview}")


def log_tool_call(tool_name: str, args: Dict, result_summary: str = None):
    """记录工具调用（简化版）"""
    # 简化参数显示
    if args:
        key_args = {k: (v if len(str(v)) < 30 else str(v)[:27] + "...")
                    for k, v in list(args.items())[:3]}  # 只显示前3个参数
        args_str = f" | 参数: {key_args}"
    else:
        args_str = ""

    log_info(f"🔧 调用工具: {tool_name}{args_str}")

    if result_summary and VERBOSE:
        log_debug(f"  结果: {result_summary}")


def log_benchmark_progress(completed: int, total: int, success: int, failed: int):
    """记录基准测试进度"""
    progress = f"[{completed}/{total}]"
    stats = f"成功: {success} | 失败: {failed}"
    percentage = (completed / total * 100) if total > 0 else 0

    bar_width = 30
    filled = int(bar_width * completed / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_width - filled)

    print(f"\r{Colors.OKCYAN}{progress}{Colors.ENDC} {bar} {percentage:.1f}% | {stats}",
          end="", file=sys.stderr, flush=True)


def format_tool_list_summary(tools: List[Dict[str, Any]]) -> str:
    """格式化工具列表摘要"""
    if not tools:
        return "无工具"

    if VERBOSE:
        return "\n".join([f"  - {tool['name']}: {tool['description'][:80]}..."
                         for tool in tools[:10]])  # 只显示前10个
    else:
        tool_names = [tool['name'] for tool in tools[:5]]
        more = f" (+{len(tools) - 5} 更多)" if len(tools) > 5 else ""
        return ", ".join(tool_names) + more


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断长文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_policy_for_display(policy: Dict) -> str:
    """格式化策略以供显示（简化版）"""
    if not policy:
        return "无策略"

    lines = []
    for tool_name, rules in list(policy.items())[:5]:  # 只显示前5个
        for rule in rules[:1]:  # 每个工具只显示第一条规则
            status = "🔒 受限" if rule[1] == 1 else "✓ 允许"
            constraints = str(rule[2]) if rule[2] else ""
            constraint_str = truncate_text(constraints, 50) if constraints else ""
            lines.append(f"  {status} {tool_name}: {constraint_str}")

    if len(policy) > 5:
        lines.append(f"  ... (还有 {len(policy) - 5} 个工具)")

    return "\n".join(lines)


def log_security_check(tool_name: str, args: Dict, decision: str,
                       reason: str = None, constraints: Dict = None):
    """记录安全检查决策"""
    if decision == "ALLOWED":
        log_success(f"工具调用已允许: {tool_name}")
    elif decision == "BLOCKED":
        log_error(f"工具调用已拦截: {tool_name}")
    elif decision == "WARNING":
        log_warning(f"工具调用警告: {tool_name}")

    if VERBOSE:
        if args:
            args_preview = {k: (str(v)[:50] + "..." if len(str(v)) > 50 else v)
                           for k, v in list(args.items())[:5]}
            log_debug(f"  参数: {args_preview}")

        if reason:
            log_debug(f"  原因: {reason}")

        if constraints:
            log_debug(f"  约束: {truncate_text(str(constraints), 100)}")


def log_task_start(task_id: str, user_task: str, injection_task: str = None):
    """记录任务开始"""
    header = f"\n{'='*80}\n"
    header += f"  🎯 任务: {task_id}\n"
    header += f"  📝 用户任务: {truncate_text(user_task, 60)}\n"
    if injection_task:
        header += f"  ⚠️  注入任务: {truncate_text(injection_task, 60)}\n"
    header += f"{'='*80}"
    print(header, file=sys.stderr)


def log_task_end(task_id: str, success: bool, duration: float = None):
    """记录任务结束"""
    status = "成功 ✓" if success else "失败 ✗"
    color = Colors.OKGREEN if success else Colors.FAIL

    footer = f"\n{'-'*80}\n"
    footer += f"  {color}任务 {task_id} {status}{Colors.ENDC}"
    if duration:
        footer += f" (用时: {duration:.2f}秒)"
    footer += f"\n{'-'*80}\n"
    print(footer, file=sys.stderr)


def log_policy_details(policy: Dict):
    """记录策略详细信息"""
    if not policy:
        log_debug("策略为空")
        return

    log_info(f"策略详情 ({len(policy)} 个工具):")

    allowed_tools = []
    blocked_tools = []
    constrained_tools = []

    for tool_name, rules in policy.items():
        for rule in rules:
            priority, effect, constraints, fallback = rule
            if effect == 0:  # allowed
                if constraints:
                    constrained_tools.append((tool_name, constraints))
                else:
                    allowed_tools.append(tool_name)
            else:  # blocked
                blocked_tools.append((tool_name, constraints if constraints else "无条件阻止"))

    if allowed_tools:
        log_success(f"  ✓ 无条件允许 ({len(allowed_tools)}): {', '.join(allowed_tools[:5])}" +
                   (f" (+{len(allowed_tools)-5})" if len(allowed_tools) > 5 else ""))

    if constrained_tools:
        log_info(f"  🔐 条件允许 ({len(constrained_tools)}):")
        for tool, constraints in constrained_tools[:3]:
            constraint_str = truncate_text(str(constraints), 80)
            log_debug(f"    - {tool}: {constraint_str}")
        if len(constrained_tools) > 3:
            log_debug(f"    ... (+{len(constrained_tools)-3} 更多)")

    if blocked_tools:
        log_warning(f"  🔒 已阻止 ({len(blocked_tools)}):")
        for tool, reason in blocked_tools[:3]:
            log_debug(f"    - {tool}: {reason}")
        if len(blocked_tools) > 3:
            log_debug(f"    ... (+{len(blocked_tools)-3} 更多)")


def format_json_compact(data: Any, max_length: int = 80) -> str:
    """紧凑格式化 JSON 数据"""
    json_str = json.dumps(data, ensure_ascii=False)
    if len(json_str) <= max_length:
        return json_str
    return json_str[:max_length-3] + "..."


def log_step(step_num: int, total_steps: int, description: str):
    """记录执行步骤"""
    log_info(f"[{step_num}/{total_steps}] {description}")


import json
