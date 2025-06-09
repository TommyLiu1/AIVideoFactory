from pydantic import BaseModel
from typing import Optional


class ImageToVideoOptions(BaseModel):
    name: str
    init_image: str
    seed: Optional[int] = None
    exploreMode: Optional[bool] = False
    width: Optional[int] = 720
    height: Optional[int] = 1280
    seconds: Optional[int] = 5
    watermark: Optional[bool] = True
    text_prompt: Optional[str] = ""
    route: Optional[str] = "i2v"
    assetGroupId: Optional[str] = None
 