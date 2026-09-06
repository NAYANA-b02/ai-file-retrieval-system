from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, UserOut, MessageResponse
from app.services.auth_service import register_user, authenticate_user
from app.services.session_service import (
    create_user_session,
    set_session_cookie,
    clear_session_cookie,
    invalidate_user_session,
)
from app.services.audit_service import log_audit
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: DBSession = Depends(get_db)):
    user = register_user(db, user_in)
    log_audit(db, action="register", user_id=user.id, details=f"User registered: {user.username}")
    return user


@router.post("/login", response_model=UserOut)
def login(
    user_in: UserLogin,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db)
):
    user = authenticate_user(db, user_in.username_or_email, user_in.password)
    if not user:
        log_audit(db, action="login_failure", details=f"Failed login attempt for: {user_in.username_or_email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password"
        )

    user_agent = request.headers.get("user-agent")
    session = create_user_session(db, user_id=user.id, user_agent=user_agent)
    set_session_cookie(response, session.id)
    log_audit(db, action="login_success", user_id=user.id, details="User logged in successfully")
    return user


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db)
):
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    user_id = None
    if session_id:
        from app.models.session import Session as UserSession
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            user_id = session.user_id
        invalidate_user_session(db, session_id)

    clear_session_cookie(response)
    if user_id:
        log_audit(db, action="logout", user_id=user_id, details="User logged out")
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
