from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Provider
from ..schemas import DaySlots, ProviderOut
from ..security import get_current_user
from ..services.scheduling import slots_by_day

router = APIRouter(prefix="/providers", tags=["providers"], dependencies=[Depends(get_current_user)])


@router.get("/{provider_id}", response_model=ProviderOut)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "Provider not found")
    return p


@router.get("/{provider_id}/slots", response_model=list[DaySlots])
def get_slots(provider_id: int, days: int = Query(14, ge=1, le=30), db: Session = Depends(get_db)):
    if not db.get(Provider, provider_id):
        raise HTTPException(404, "Provider not found")
    return slots_by_day(db, provider_id, days)
