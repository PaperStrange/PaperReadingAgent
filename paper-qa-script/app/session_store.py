"""会话存储：接口 + 内存实现（替代 backend 中的全局 SESSIONS 字典）。

Sprint-2 US-2.4：
- `SessionStore` 为接口（get_or_create/get/reset），后续多 worker/多机可换 Redis 等实现；
- `MemorySessionStore` 提供 dict 风格访问（__getitem__/__setitem__/get/__contains__），
  使现有调用点以最小 diff 迁移，行为不变（行为不变以回归测试为证）。
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from paperqa import Docs, Settings


@dataclass
class SessionState:
    session_id: str
    settings: Settings | None = None
    search_index: Any | None = None
    candidate_paths: list[str] = field(default_factory=list)
    docs: Docs | None = None
    evidence_session: Any | None = None
    answer_session: Any | None = None
    run_records: list[dict[str, Any]] = field(default_factory=list)
    # Sprint-3：config 步骤存下的数据源参数（load_index 步骤读取；Run All 时各节点参数相互独立）
    data_source_params: dict[str, Any] = field(default_factory=dict)


class SessionStore(ABC):
    """会话存储接口。实现必须线程安全（FastAPI 可能多 worker 共享进程内实例）。"""

    @abstractmethod
    def get_or_create(self, session_id: str | None = None) -> SessionState:
        """按 id 取会话，不存在则创建；id 为空则生成新 id。"""

    @abstractmethod
    def get(self, session_id: str) -> SessionState | None:
        """按 id 取会话，不存在返回 None。"""

    @abstractmethod
    def reset(self, session_id: str) -> SessionState:
        """重建会话（清空状态但保留 id）。"""


class MemorySessionStore(SessionStore):
    """进程内字典实现（当前单机形态）。"""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str | None = None) -> SessionState:
        sid = session_id or str(uuid.uuid4())
        if sid not in self._sessions:
            self._sessions[sid] = SessionState(session_id=sid)
        return self._sessions[sid]

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def reset(self, session_id: str) -> SessionState:
        state = SessionState(session_id=session_id)
        self._sessions[session_id] = state
        return state

    # dict 风格访问（兼容旧代码，最小迁移）
    def __getitem__(self, key: str) -> SessionState:
        return self._sessions[key]

    def __setitem__(self, key: str, value: SessionState) -> None:
        self._sessions[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._sessions
