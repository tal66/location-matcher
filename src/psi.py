import logging
import uuid
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import List, Dict

from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sec import currUserDep

log = logging.getLogger(__name__)

router = APIRouter(prefix="/psi", tags=["PSI"])

SESSION_TIMEOUT_MINUTES = 30


class SessionStatus(Enum):
    INITIATED = 1
    JOINED = 2
    COMPLETED = 3


class InitiateRequest(BaseModel):
    blinded_values: List[int]
    user_id: str


class JoinRequest(BaseModel):
    session_id: str
    response_values: List[int]
    user_id: str


class IntersectionUpdateRequest(BaseModel):
    user_id: str
    other_user_id: str
    len_intersection: int = Field(..., ge=0)


class SessionData(BaseModel):
    initiator_values: List[int]
    status: int
    user_id: str
    created_at: datetime
    response_values: Dict[str, List[int]] = {}
    intersection: Dict[str, int] = {}


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}

    def create_session(self, user_id: str, values: List[int]) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = SessionData(
            initiator_values=values,
            status=SessionStatus.INITIATED,
            user_id=user_id,
            created_at=datetime.now(UTC)
        )
        return session_id

    def get(self, session_id: str) -> SessionData:
        return self.sessions[session_id]

    def remove(self, session_id: str):
        del self.sessions[session_id]

    def cleanup_expired_sessions(self):
        for sid, session in self.sessions.items():
            if self.is_expired(session):
                del self.sessions[sid]

    @classmethod
    def is_expired(cls, session):
        session_age = datetime.now(UTC) - session.created_at
        return session_age > timedelta(minutes=SESSION_TIMEOUT_MINUTES)


session_manager = SessionManager()


@router.post("/init", status_code=201)
async def initiate_psi(request: InitiateRequest, current_user: currUserDep):
    """store initiator's blinded values and create session."""
    if not request.blinded_values:
        raise HTTPException(status_code=400, detail="Invalid request")

    session_id = session_manager.create_session(current_user.user_id, request.blinded_values)
    return {"session_id": session_id}


@router.post("/{session_id}/join")
async def join_psi(session_id: str, request: JoinRequest, current_user: currUserDep):
    """store joiner's response values and update session status."""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_manager.is_expired(session):
        session_manager.remove(session_id)
        raise HTTPException(status_code=410, detail="Session expired")

    if session.status != SessionStatus.INITIATED.value:
        raise HTTPException(status_code=400, detail=f"Invalid session status ({session["status"]}, not 1)")

    session.response_values[current_user.user_id] = request.response_values
    session.status = SessionStatus.JOINED.value

    return {"status": session.status, "session_id": session_id}


@router.get("/{session_id}")
async def get_values(session_id: str, current_user: currUserDep):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == SessionStatus.INITIATED.value:
        return {"values": session.initiator_values, "status": SessionStatus.INITIATED.value}
    elif session.status == SessionStatus.JOINED.value:
        if current_user.user_id != session.user_id:
            raise HTTPException(status_code=403, detail="Access allowed only for initiator")
        return {"values": session.response_values, "status": SessionStatus.JOINED.value}
    else:
        log.error(f"Invalid session status: {session.status}")
        raise HTTPException(status_code=400, detail="Invalid session status")


@router.patch("/{session_id}/intersection")
async def update_intersection_result(session_id: str, request: IntersectionUpdateRequest, current_user: currUserDep):
    """update number of intersections with other user"""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.user_id != session.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if session.status != SessionStatus.JOINED.value:
        raise HTTPException(status_code=400, detail="Invalid session status")

    # update
    session.intersection[request.other_user_id] = request.len_intersection
    session.status = SessionStatus.COMPLETED.value

    return {"status": f"Intersection updated to {request.len_intersection}"}


@router.get("/{session_id}/intersection")
async def get_intersection_result(session_id: str, current_user: currUserDep):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    n = session.intersection.get(current_user.user_id, -1)
    return {"intersection_len": n}
