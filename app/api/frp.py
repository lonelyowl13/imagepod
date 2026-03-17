"""
FRP server-plugin HTTP handler for per-executor authentication.

frps is configured to call POST /internal/frp/handler on every frpc Login
event. The frpc client must include:

    metas.executor_id       = <executor DB id>
    metas.executor_key_hash = <sha256 of executor API key>

frps forwards these metadata values to this endpoint, which validates them
against the executor record in the database (by comparing to Executor.token_hash)
and responds with {"reject": false} on success or {"reject": true,
"reject_reason": "..."} on failure.

Reference: https://gofrp.org/docs/features/common/server-plugin/
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.executor import Executor
from app.utils import hash_key

router = APIRouter(prefix="/internal/frp", tags=["frp-internal"])


class _FrpPluginRequest(BaseModel):
    content: Dict[str, Any] = {}
    op: str = ""


class _FrpPluginResponse(BaseModel):
    reject: bool = False
    reject_reason: str = ""
    unchange: bool = True


@router.post("/handler", response_model=_FrpPluginResponse)
def frp_auth_handler(
    body: _FrpPluginRequest,
    db: Session = Depends(get_db),
) -> _FrpPluginResponse:
    """Validate an frpc Login event from the frps auth plugin."""
    metas: Dict[str, Any] = body.content.get("metas") or {}

    raw_executor_id = metas.get("executor_id")
    executor_key = metas.get("executor_key")

    if not raw_executor_id or not executor_key:
        return _FrpPluginResponse(reject=True, reject_reason="missing executor credentials")

    try:
        executor_id = int(raw_executor_id)
    except (ValueError, TypeError):
        return _FrpPluginResponse(reject=True, reject_reason="invalid executor_id")

    executor_key_hash = hash_key(executor_key)

    executor: Executor | None = db.query(Executor).filter(Executor.id == executor_id).first()
    if not executor or not executor.token_hash or executor.token_hash != executor_key_hash:
        return _FrpPluginResponse(reject=True, reject_reason="invalid credentials")

    return _FrpPluginResponse(reject=False, unchange=True)
