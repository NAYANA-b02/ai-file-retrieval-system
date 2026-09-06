from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def log_audit(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    file_id: Optional[int] = None,
    query: Optional[str] = None,
    details: Optional[str] = None,
) -> AuditLog:
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        file_id=file_id,
        query=query,
        details=details,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
