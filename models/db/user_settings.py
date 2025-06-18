from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, func

from models.db.database_base import Base

class UserSettings(Base):
    __tablename__ = "t_user_settings"

    user_id = Column(Integer,  ForeignKey("t_users.id"), primary_key=True, index=True)
    token = Column(String(512), nullable=False, index=True)
    save_video_path = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "token": self.token,
            "save_video_path": self.save_video_path
        }

    def __str__(self) -> str:
        return f"<UserSettings(user_id='{self.user_id}', token='{self.token}', video_save_path='{self.save_video_path}')>"

    def __repr__(self):
        return self.__str__()