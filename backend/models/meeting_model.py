from pydantic import BaseModel


class Meeting(BaseModel):
    meeting_id: str
    title: str
    status: str
    scheduled_for: str
    created_at: str
    summary_s3_key: str | None = None
    session_id: str | None = None
