from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from app.schemas.reminder import ReminderResponse, ReminderCreate, ReminderUpdate
from app.utils.mock_data import mock_generator
from app.models.reminder import ReminderStatus

router = APIRouter()


@router.get("/", response_model=List[ReminderResponse])
async def list_reminders(
    case_id: Optional[str] = Query(None),
    status: Optional[ReminderStatus] = Query(None),
    due_before: Optional[datetime] = Query(None)
):
    """List reminders with optional filters"""
    reminders = [mock_generator.generate_reminder(case_id) for _ in range(5)]
    
    if status:
        for reminder in reminders:
            reminder["status"] = status
    
    return [ReminderResponse(**reminder) for reminder in reminders]


@router.get("/upcoming")
async def get_upcoming_reminders(days: int = 7):
    """Get reminders due in next N days"""
    reminders = [mock_generator.generate_reminder() for _ in range(3)]
    return {
        "count": len(reminders),
        "days": days,
        "reminders": [ReminderResponse(**r) for r in reminders]
    }


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(reminder_id: str):
    """Get specific reminder"""
    reminder = mock_generator.generate_reminder()
    reminder["id"] = reminder_id
    return ReminderResponse(**reminder)


@router.post("/", response_model=ReminderResponse, status_code=201)
async def create_reminder(reminder: ReminderCreate):
    """Create new reminder"""
    reminder_data = mock_generator.generate_reminder()
    reminder_data.update(reminder.dict())
    return ReminderResponse(**reminder_data)


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(reminder_id: str, reminder: ReminderUpdate):
    """Update reminder"""
    reminder_data = mock_generator.generate_reminder()
    reminder_data["id"] = reminder_id
    reminder_data.update(reminder.dict(exclude_unset=True))
    return ReminderResponse(**reminder_data)


@router.post("/{reminder_id}/complete")
async def complete_reminder(reminder_id: str):
    """Mark reminder as completed"""
    return {
        "reminder_id": reminder_id,
        "status": "completed",
        "completed_at": datetime.now().isoformat()
    }