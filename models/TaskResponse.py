from pydantic import BaseModel
from typing import Optional
from models.Artifact import Artifact


class TaskResponse(BaseModel):
    id: str
    name: Optional[str]
    image: Optional[str]
    createdAt: Optional[str]
    updatedAt: Optional[str]
    taskType: Optional[str]
    options: Optional[dict]
    status: str
    error: Optional[str]
    progressText: Optional[str]
    progressRatio:  Optional[str]
    estimatedTimeToStartSeconds: int
    artifacts: Optional[list[Artifact]]
    sharedAsset: Optional[dict]
    sourceAssetId: Optional[str]