from pydantic import BaseModel
from typing import Optional

class Artifact(BaseModel):
    id: str
    createdAt: str
    updatedAt: str
    userId: int
    createdBy: int
    taskId: str
    parentAssetGroupId: str
    filename: str
    url: str
    fileSize: str
    isDirectory: bool
    previewUrls: list[str]
    private: bool
    privateInTeam: bool
    deleted: bool
    reported: bool
    metadata: dict
    favorite: bool
    sourceAssetId: Optional[str]