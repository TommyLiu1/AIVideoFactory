from pydantic import BaseModel
from typing import Optional

from models.TextToImageOptions import TextToImageOptions


class TextToImageRequest(BaseModel):
    prompt: str
    ratio: str
    num: int
    model: Optional[str] = None
    options: Optional[TextToImageOptions] = None
    asTeamId: Optional[int] = 38479536
    sessionId: Optional[str] = None