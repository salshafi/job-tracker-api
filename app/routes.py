from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application
from app.schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate, Status

# All endpoints in this file start with /applications
router = APIRouter(prefix="/applications", tags=["applications"])


# Helper: find one application or stop with a 404 error
def get_or_404(db: Session, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


# CREATE: add a new application
@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    application = Application(**payload.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)  # reload so we get the new id and created_at
    return application


# READ: list applications, newest first. Optional filter: /applications?status=applied
@router.get("", response_model=list[ApplicationOut])
def list_applications(status: Status | None = None, db: Session = Depends(get_db)):
    query = select(Application).order_by(Application.created_at.desc())
    if status is not None:
        query = query.where(Application.status == status.value)
    return db.scalars(query).all()


# READ: get one application by id
@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(application_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, application_id)


# UPDATE: change only the fields the client sent
@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)
):
    application = get_or_404(db, application_id)
    # exclude_unset=True means fields the client did not send are left alone
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(application, field, value)
    db.commit()
    db.refresh(application)
    return application


# DELETE: remove an application (204 = success with no body)
@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: int, db: Session = Depends(get_db)):
    application = get_or_404(db, application_id)
    db.delete(application)
    db.commit()