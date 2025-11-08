from pydantic import BaseModel


class AgendaItem(BaseModel):
    agenda_id: str
    meeting_id: str
    title: str
