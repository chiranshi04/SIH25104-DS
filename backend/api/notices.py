"""Public notice feed aur staff/admin notice management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_roles
from backend.database.admin_schemas import NoticeCreate, NoticeResponse, NoticeUpdate
from backend.database.connection import get_db
from backend.database.models import Notice, User

router = APIRouter(tags=["Notices"])


@router.get("/notices", response_model=list[NoticeResponse])
def public_notices(db: Session = Depends(get_db)):
    return db.scalars(
        select(Notice).where(Notice.is_active.is_(True)).order_by(Notice.created_at.desc())
    ).all()


@router.get("/admin/notices", response_model=list[NoticeResponse])
def admin_notices(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    return db.scalars(select(Notice).order_by(Notice.created_at.desc())).all()


@router.post("/notices", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
def create_notice(
    request: NoticeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("staff", "admin")),
):
    notice = Notice(
        title=request.title.strip(),
        content=request.content.strip(),
        is_active=request.is_active,
        created_by=user.id,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice


@router.put("/notices/{notice_id}", response_model=NoticeResponse)
def update_notice(
    notice_id: int,
    request: NoticeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    notice = db.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="Notice not found")
    if request.title is not None:
        notice.title = request.title.strip()
    if request.content is not None:
        notice.content = request.content.strip()
    if request.is_active is not None:
        notice.is_active = request.is_active
    db.commit()
    db.refresh(notice)
    return notice


@router.delete("/notices/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    notice = db.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="Notice not found")
    db.delete(notice)
    db.commit()
