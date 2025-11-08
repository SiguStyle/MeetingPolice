from pydantic import BaseModel


class Transcript(BaseModel):
    meeting_id: str
    text: str
