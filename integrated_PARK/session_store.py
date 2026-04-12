"""
세션 스토어: Cosmos DB를 백엔드로 사용한 stateless 세션 관리.

COSMOS_ENDPOINT 환경변수가 없으면 인메모리 딕셔너리로 폴백하므로
로컬 개발에서도 추가 설정 없이 동작한다.

Cosmos DB 구조:
  Database  : COSMOS_DATABASE (기본값 "sohobi")
  Container : COSMOS_CONTAINER (기본값 "sessions")
  Partition : /id  (= session_id)
  TTL       : COSMOS_SESSION_TTL 초 (기본값 86400 = 24시간)

저장 스키마:
  {
    "id": "<session_id>",
    "profile":   "<창업자 프로필 문자열>",
    "history":   [{"role": "user"|"assistant"|"system", "content": "..."}, ...],
    "extracted": {"key": value, ...}
  }
"""

import os
from collections import OrderedDict
from typing import Any

from semantic_kernel.contents import ChatHistory

# ── Cosmos DB 연결 싱글턴 ───────────────────────────────────────
_container = None  # azure.cosmos.aio.ContainerProxy
_cosmos_client = None  # CosmosClient (종료 시 닫기 위해 보관)


async def _get_container():
    global _container
    if _container is not None:
        return _container

    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    if not endpoint:
        return None  # 폴백 모드

    from azure.cosmos.aio import CosmosClient
    from azure.identity.aio import DefaultAzureCredential

    db_name = os.getenv("COSMOS_DATABASE", "sohobi")
    con_name = os.getenv("COSMOS_CONTAINER", "sessions")

    # 키 인증이 비활성화된 계정이므로 AD 토큰 인증 사용
    credential = DefaultAzureCredential()
    client = CosmosClient(url=endpoint, credential=credential)
    db = client.get_database_client(db_name)
    _container = db.get_container_client(con_name)
    global _cosmos_client
    _cosmos_client = client
    return _container


async def close() -> None:
    """FastAPI 종료 시 호출해 Cosmos DB 연결을 정상 종료한다."""
    global _cosmos_client, _container
    if _cosmos_client is not None:
        await _cosmos_client.close()
        _cosmos_client = None
        _container = None


# ── ChatHistory 직렬화 ──────────────────────────────────────────


def _serialize_history(history: ChatHistory) -> list[dict]:
    result = []
    for msg in history.messages:
        role = str(msg.role).lower()
        # SK role 값: "AuthorRole.user" 형태일 수 있으므로 정규화
        if "user" in role:
            role = "user"
        elif "assistant" in role:
            role = "assistant"
        elif "system" in role:
            role = "system"
        else:
            continue
        result.append({"role": role, "content": str(msg.content)})
    return result


def _deserialize_history(data: list[dict]) -> ChatHistory:
    history = ChatHistory()
    for msg in data:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            history.add_user_message(content)
        elif role == "assistant":
            history.add_assistant_message(content)
        elif role == "system":
            history.add_system_message(content)
    return history


# ── 인메모리 폴백 ───────────────────────────────────────────────
_memory: OrderedDict[str, dict] = OrderedDict()
_MEMORY_MAX = 500  # 세션 수 상한 — 초과 시 가장 오래 미접근 항목 제거


def _evict_if_needed() -> None:
    if len(_memory) >= _MEMORY_MAX:
        evict_count = len(_memory) - _MEMORY_MAX + 1
        for _ in range(evict_count):
            _memory.popitem(last=False)  # 가장 오래 미접근 항목 제거 (LRU)


_EMPTY_CONTEXT = {"adm_codes": [], "business_type": "", "location_name": ""}


def _empty_query_session() -> dict:
    return {
        "profile": "",
        "history": ChatHistory(),
        "extracted": {},
        "context": dict(_EMPTY_CONTEXT),
    }


# ── 공개 API ────────────────────────────────────────────────────


async def get_query_session(session_id: str) -> dict:
    """session_id에 해당하는 Q&A 세션을 반환.
    없으면 빈 세션을 반환한다 (저장하지 않음).
    """
    container = await _get_container()

    if container is None:
        # 인메모리 폴백
        if session_id not in _memory:
            _evict_if_needed()
            _memory[session_id] = _empty_query_session()
        _memory.move_to_end(session_id)
        return _memory[session_id]

    try:
        item = await container.read_item(item=session_id, partition_key=session_id)
        return {
            "profile": item.get("profile", ""),
            "history": _deserialize_history(item.get("history", [])),
            "extracted": item.get("extracted", {}),
            "context": item.get("context", dict(_EMPTY_CONTEXT)),
            "user_id": item.get("user_id", ""),
            "last_domain": item.get("last_domain", ""),
            "messages": item.get("messages", []),
        }
    except Exception:
        return _empty_query_session()


async def session_exists(session_id: str) -> bool:
    """session_id가 실제 저장된 세션인지 확인한다."""
    container = await _get_container()
    if container is None:
        return session_id in _memory
    try:
        await container.read_item(item=session_id, partition_key=session_id)
        return True
    except Exception:
        return False


async def save_query_session(session_id: str, session: dict) -> None:
    """Q&A 세션을 저장한다."""
    container = await _get_container()
    ttl = int(os.getenv("COSMOS_SESSION_TTL", "86400"))

    if container is None:
        if session_id not in _memory:
            _evict_if_needed()
        _memory[session_id] = session
        _memory.move_to_end(session_id)
        return

    doc: dict[str, Any] = {
        "id": session_id,
        "profile": session.get("profile", ""),
        "history": _serialize_history(session.get("history", ChatHistory())),
        "extracted": session.get("extracted", {}),
        "context": session.get("context", dict(_EMPTY_CONTEXT)),
        "last_domain": session.get("last_domain", ""),
        "messages": session.get("messages", []),
        "ttl": ttl,
    }
    # user_id가 세션에 있으면 보존 (link_session_to_user 이후 덮어쓰기 방지)
    if session.get("user_id"):
        doc["user_id"] = session["user_id"]
    await container.upsert_item(doc)


HISTORY_WINDOW = 14  # 에이전트에 주입할 최대 메시지 수 (user+assistant 쌍 5턴)


def get_recent_history(history: ChatHistory, n: int = HISTORY_WINDOW) -> list[dict]:
    """히스토리에서 최근 n개 메시지(user/assistant)를 [{role, content}] 형태로 반환."""
    msgs = [
        {
            "role": m.role.value.lower()
            if hasattr(m.role, "value")
            else str(m.role).split(".")[-1].lower(),
            "content": str(m.content),
        }
        for m in history.messages
        if ("user" in str(m.role).lower() or "assistant" in str(m.role).lower())
    ]
    return msgs[-n:]


async def get_doc_history(session_id: str) -> list[dict]:
    """문서 생성 플로우의 대화 이력(raw list)을 반환."""
    container = await _get_container()

    if container is None:
        key = f"doc:{session_id}"
        if key in _memory:
            _memory.move_to_end(key)
        return _memory.get(key, [])

    try:
        item = await container.read_item(
            item=f"doc:{session_id}", partition_key=f"doc:{session_id}"
        )
        return item.get("history", [])
    except Exception:
        return []


async def save_doc_history(session_id: str, history_raw: list[dict]) -> None:
    """문서 생성 플로우의 대화 이력을 저장."""
    container = await _get_container()
    ttl = int(os.getenv("COSMOS_SESSION_TTL", "86400"))
    key = f"doc:{session_id}"

    if container is None:
        if key not in _memory:
            _evict_if_needed()
        _memory[key] = history_raw
        _memory.move_to_end(key)
        return

    await container.upsert_item(
        {
            "id": key,
            "history": history_raw,
            "ttl": ttl,
        }
    )


async def link_session_to_user(session_id: str, user_id: str) -> None:
    """session_id를 user_id에 귀속하고 TTL을 30일로 연장 (Cosmos) 또는 메모리에 기록."""
    container = await _get_container()
    ttl_member = 30 * 86400  # 30일

    if container is None:
        if session_id in _memory:
            _memory[session_id]["user_id"] = user_id
        return

    try:
        item = await container.read_item(item=session_id, partition_key=session_id)
        item["user_id"] = user_id
        item["ttl"] = ttl_member
        await container.replace_item(item=session_id, body=item)
    except Exception:
        pass  # 세션이 이미 만료된 경우 무시


async def get_user_id_by_session(session_id: str) -> str:
    """session_id에 귀속된 user_id 반환. 없거나 만료된 경우 빈 문자열."""
    container = await _get_container()
    if container is None:
        sess = _memory.get(session_id)
        if isinstance(sess, dict):
            return sess.get("user_id", "")
        return ""
    try:
        item = await container.read_item(item=session_id, partition_key=session_id)
        return item.get("user_id", "")
    except Exception:
        return ""


async def get_sessions_by_user(user_id: str) -> list[dict]:
    """user_id에 귀속된 세션 목록을 최신순으로 반환.

    반환 형태: [{"session_id", "context", "history_count", "_ts"}, ...]
    """
    container = await _get_container()

    if container is None:
        results = []
        for sid, sess in _memory.items():
            if isinstance(sess, dict) and sess.get("user_id") == user_id:
                history = sess.get("history", ChatHistory())
                results.append(
                    {
                        "session_id": sid,
                        "context": sess.get("context", {}),
                        "history_count": len(history.messages)
                        if hasattr(history, "messages")
                        else 0,
                        "_ts": 0,
                    }
                )
        return results

    query = (
        "SELECT c.id, c.context, c.history, c._ts "
        "FROM c WHERE c.user_id = @uid "
        "ORDER BY c._ts DESC"
    )
    params = [{"name": "@uid", "value": user_id}]
    results = []
    async for item in container.query_items(query=query, parameters=params):
        results.append(
            {
                "session_id": item["id"],
                "context": item.get("context", {}),
                "history_count": len(item.get("history", [])),
                "_ts": item.get("_ts", 0),
            }
        )
    return results


async def get_session_messages(session_id: str) -> list[dict]:
    """특정 세션의 프론트 렌더링용 messages 메타데이터를 반환."""
    container = await _get_container()

    if container is None:
        sess = _memory.get(session_id)
        if sess is None or not isinstance(sess, dict):
            return []
        return sess.get("messages", [])

    try:
        item = await container.read_item(item=session_id, partition_key=session_id)
        return item.get("messages", [])
    except Exception:
        return []


async def get_session_history(session_id: str) -> list[dict]:
    """특정 세션의 Q&A 히스토리를 [{role, content}] 형태로 반환."""
    container = await _get_container()

    if container is None:
        sess = _memory.get(session_id)
        if sess is None:
            return []
        history = sess.get("history", ChatHistory())
        return _serialize_history(history)

    try:
        item = await container.read_item(item=session_id, partition_key=session_id)
        return item.get("history", [])
    except Exception:
        return []
