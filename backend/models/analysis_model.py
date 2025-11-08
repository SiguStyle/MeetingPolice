from pydantic import BaseModel


class AnalysisResult(BaseModel):
    meeting_id: str
    sentiment: str
