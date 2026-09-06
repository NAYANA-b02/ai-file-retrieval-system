from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.database import get_db
from app.models.session import Session as UserSession
from app.models.user import User
from app.services.audit_service import log_audit

session_cookie_scheme = APIKeyCookie(
    name=settings.SESSION_COOKIE_NAME,
    auto_error=False,
    description="HTTP-only session cookie"
)


def get_current_user(
    request: Request,
    cookie_token: Optional[str] = Depends(session_cookie_scheme),
    db: DBSession = Depends(get_db)
) -> User:
    session_id = cookie_token or request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        log_audit(db, action="unauthorized_access_attempt", details="Missing session cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.is_active == True
    ).first()

    if not session:
        log_audit(db, action="unauthorized_access_attempt", details="Invalid session token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    now = datetime.now(timezone.utc)
    if session.expires_at < now:
        session.is_active = False
        db.commit()
        log_audit(db, user_id=session.user_id, action="unauthorized_access_attempt", details="Expired session token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )

    session.last_seen_at = now
    db.commit()

    user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
    if not user:
        log_audit(db, user_id=session.user_id, action="unauthorized_access_attempt", details="User inactive or deleted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account unavailable"
        )

    return user
