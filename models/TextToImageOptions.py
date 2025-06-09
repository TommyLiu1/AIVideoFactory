from pydantic import BaseModel
from typing import Optional


class TextToImageOptions(BaseModel):
    text_prompt: str
    seed: Optional[int] = None
    exploreMode: Optional[bool] = True
    width: Optional[int] = 768
    height: Optional[int] = 1280
    num_images: Optional[int] = 1
    flip: Optional[bool] = True
    diversity: Optional[int] = 2
    publicImageGeneratorName: Optional[str] = "Gen-4"
    assetGroupId: Optional[str] = None
    recordingEnabled: Optional[bool] = True