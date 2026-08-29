"""统一事件模型（Sprint-2 US-2.3 类型定义）。

设计原则（refactor-analysis.MD §2 Consistent patterns）：
- 普通流水线步骤、Agent 内部工具、未来的其它步骤（如 Summarize）都发同构事件；
- 事件是可序列化的 pydantic 模型，作为 SSE/前端时间线/持久化的唯一契约；
- 字段命名与现有 SSE `function_trace`/`step_done` 消息保持兼容（本期不改变线上协议）。
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EventKind(StrEnum):
    """事件大类。"""

    STEP_START = "step_start"
    STEP_DONE = "step_done"
    AGENT_ACTION = "agent_action"          # Agent 决策了某个动作（工具调用）
    AGENT_TOOL = "agent_tool"              # 某个工具开始/完成
    FUNCTION_TRACE = "function_trace"      # paperqa 函数级追踪（兼容现有协议）
    ERROR = "error"
    PROGRESS = "progress"


class BaseEvent(BaseModel):
    """所有事件的公共头。"""

    kind: EventKind
    session_id: str
    run_id: str
    step: str | None = None
    ts: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str | None = None            # 一次执行的关联 id（错误排查的一手证据）


class StepEvent(BaseEvent):
    """流水线步骤事件（config/load_index/retrieve/parse_chunk_embed/evidence/answer）。"""

    kind: EventKind = EventKind.STEP_DONE
    ok: bool = True
    duration_s: float = 0.0
    output: dict = Field(default_factory=dict)
    error: str | None = None


class AgentActionEvent(BaseEvent):
    """Agent 决策事件（如 ToolSelector 选择调哪个工具、带什么参数）。"""

    kind: EventKind = EventKind.AGENT_ACTION
    action: str                              # 动作名（工具名 / final_answer 等）
    action_input: dict = Field(default_factory=dict)


class AgentToolEvent(BaseEvent):
    """Agent 内部工具执行事件（与 StepEvent 区分：归属 agent，而非流水线节点）。"""

    kind: EventKind = EventKind.AGENT_TOOL
    tool: str
    ok: bool = True
    duration_s: float = 0.0
    output: dict = Field(default_factory=dict)
    error: str | None = None


class FunctionTraceEvent(BaseEvent):
    """函数级追踪事件（兼容 runtime_trace 输出与现有 SSE function_trace 协议）。"""

    kind: EventKind = EventKind.FUNCTION_TRACE
    call_id: int = 0
    parent_call_id: int | None = None
    depth: int = 0
    task_id: str | None = None
    func: str = ""
    status: str = "ok"
    duration_s: float = 0.0
    args: dict = Field(default_factory=dict)
    result: str | None = None
    result_payload: dict | None = None
    args_payload: dict | None = None
    error: str | None = None


class ErrorEvent(BaseEvent):
    """错误事件：携带原始错误与上下文的"一手证据"。"""

    kind: EventKind = EventKind.ERROR
    error_type: str = ""
    message: str = ""
    detail: str | None = None                # 原始 traceback / 原始错误文本
