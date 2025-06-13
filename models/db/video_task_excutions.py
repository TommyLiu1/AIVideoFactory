from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

task_base = declarative_base()

class VideoTaskExecution(task_base):

    __tablename__ = "t_video_task_execution"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=True)
    prompt = Column(Text)
    model = Column(String(100))
    model_supply = Column(String(100))
    ratio = Column(String(50))
    video_duration = Column(Integer, index=True, nullable=False)
    video_nums = Column(Integer)
    task_status = Column(String(50))
    video_url = Column(String(1024))
    failed_reason = Column(Text, nullable=True)  # 用于存储失败原因
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "video_duration": self.video_duration,
            "prompt": self.prompt,
            "model": self.model,
            "model_supply": self.model_supply,
            "ratio": self.ratio,
            "video_nums": self.video_nums,
            "task_status": self.task_status,
            "failed_reason": self.failed_reason,
            "video_url": self.video_url
        }
    def __str__(self) -> str:
        return f"<VideoJob(job_id='{self.task_id}', status='{self.task_status}')>"

    def __repr__(self):
        return self.__str__()



