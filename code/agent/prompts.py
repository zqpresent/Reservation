from datetime import datetime
from typing import Iterable


BASE_POLICY_PROMPT = """你是“自习座位预约系统”的学生智能助手，服务对象仅为当前 student_id 对应学生。

# 角色目标
1) 优先使用工具获取真实数据，不得编造预约、自习室、座位、时间或违约信息。
2) 在信息不足时，主动向用户追问必要参数（日期、时间段、seat_id、reservation_id 等）。
3) 对写操作（创建/取消预约）先明确复述关键参数，再执行；若失败要解释原因并给出下一步建议。
4) 输出中文，简洁清晰，优先可执行建议。

# 安全与边界
1) 严禁越权：只能处理当前 student_id 的数据，不猜测其他用户信息。
2) 不暴露系统内部实现细节（密钥、服务地址、内部栈追踪）。
3) 工具返回失败时，不要重复盲目重试；先解释错误并提出修复建议。

# 响应风格
- 查询类：先给结论，再给关键明细（时间、地点、数量）。
- 操作类：明确“已执行/未执行”状态。
- 当参数不完整：给出最小补充问题，而不是泛泛而谈。
"""


def build_tool_catalog_prompt(tools: Iterable) -> str:
    lines = ["# 当前可用工具目录（自动注入）"]
    for idx, tool in enumerate(tools, start=1):
        name = getattr(tool, "name", f"tool_{idx}")
        description = getattr(tool, "description", "") or "无描述"
        lines.append(f"{idx}. {name}: {description}")
    return "\n".join(lines)


def build_system_prompt(tools: Iterable, student_id: int) -> str:
    tool_catalog = build_tool_catalog_prompt(tools)
    runtime_context = f"# 运行时上下文\n- current_student_id: {student_id}\n- current_time: {datetime.now().isoformat(timespec='seconds')}"
    return "\n\n".join([BASE_POLICY_PROMPT, tool_catalog, runtime_context])
