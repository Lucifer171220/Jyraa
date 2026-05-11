import os
import uuid
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.models import IssueAttachment, Issue


UPLOAD_DIR = "uploads/attachments"


def ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload_file(upload_file: UploadFile, user_id: int) -> dict:
    ensure_upload_dir()

    file_extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    content = upload_file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "filename": upload_file.filename,
        "file_path": file_path,
        "file_size": len(content),
        "mime_type": upload_file.content_type or "application/octet-stream"
    }


def create_attachment(
    db: Session,
    issue_id: int,
    user_id: int,
    upload_file: UploadFile
) -> IssueAttachment:
    file_info = save_upload_file(upload_file, user_id)

    attachment = IssueAttachment(
        issue_id=issue_id,
        user_id=user_id,
        filename=file_info["filename"],
        file_path=file_info["file_path"],
        file_size=file_info["file_size"],
        mime_type=file_info["mime_type"]
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachment(db: Session, attachment_id: int) -> Optional[IssueAttachment]:
    return db.query(IssueAttachment).filter(IssueAttachment.attachment_id == attachment_id).first()


def get_issue_attachments(db: Session, issue_id: int) -> list:
    return db.query(IssueAttachment).filter(IssueAttachment.issue_id == issue_id).all()


def delete_attachment(db: Session, attachment_id: int) -> bool:
    attachment = get_attachment(db, attachment_id)
    if not attachment:
        return False

    try:
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)
    except Exception:
        pass

    db.delete(attachment)
    db.commit()
    return True