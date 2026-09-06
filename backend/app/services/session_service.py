from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Response
from sqlalchemy.orm import Session as DBSession
from app.models.session import Session as UserSession
from app.core.config import settings
from app.core.security import generate_session_id


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_user_session(
    db: DBSession,
    user_id: int,
    user_agent: Optional[str] = None
) -> UserSession:
    session_id = generate_session_id()
    expires_at = utc_now() + timedelta(hours=settings.SESSION_EXPIRE_HOURS)
    session = UserSession(
        id=session_id,
        user_id=user_id,
        expires_at=expires_at,
        last_seen_at=utc_now(),
        is_active=True,
        user_agent=user_agent
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def set_session_cookie(response: Response, session_id: str):
    max_age = settings.SESSION_EXPIRE_HOURS * 3600
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=max_age,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/"
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE
    )


def invalidate_user_session(db: DBSession, session_id: str):
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if session:
        session.is_active = False
        db.commit()
