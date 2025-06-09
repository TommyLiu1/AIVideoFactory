from pydantic import BaseModel
from typing import Optional

from models.ImageToVideoOptions import ImageToVideoOptions

class ImageToVideoRequest(BaseModel):
    ratio: str
    seconds: int
    numbers: int
    image_url: Optional[str] = None
    prompt: Optional[str] = ""
    model: Optional[str] = "gen3a_turbo"
    options: Optional[ImageToVideoOptions] = None
    asTeamId: Optional[int] = 38479536
    sessionId: Optional[str] = None