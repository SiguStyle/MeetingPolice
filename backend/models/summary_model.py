from pydantic import BaseModel


class Summary(BaseModel):
    meeting_id: str
    content: str
