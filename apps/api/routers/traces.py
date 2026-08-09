"""TRAZA HTTP transport."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.dependencies import CallSvc, CurrentAccount
from apps.api.schemas.traces import CallTraceResponse

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("/{call_id}", response_model=CallTraceResponse)
async def get_trace(
    call_id: str,
    account: CurrentAccount,
    calls: CallSvc,
) -> CallTraceResponse:
    payload = calls.trace(account.account_id, call_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "call_not_found", "message": "Call not found"},
        )
    return CallTraceResponse.model_validate(payload)
