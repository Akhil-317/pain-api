from datetime import datetime
from sqlalchemy.orm import Session
from models.on_boarding_models import AuditLog

def log_audit(db: Session, audit_title: str, message: str):
    """
    Create a new audit log entry in the database.
    """
    audit_entry = AuditLog(
        audit_title=audit_title,
        message=message,
        logged_at=datetime.utcnow()
    )
    db.add(audit_entry)
    db.commit()
