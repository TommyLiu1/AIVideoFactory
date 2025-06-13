
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
user_table_base = declarative_base()

class User(user_table_base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    user_type = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    token = Column(String(512), nullable=True)  # runway token 字段，长度200+，可空
    video_save_path = Column(String(300), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "user_type": self.user_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "token": self.token,
            "video_save_path": self.video_save_path
        }

    def __str__(self) -> str:
        return f"<User(id='{self.id}', username='{self.username}', user_type='{self.user_type}')>"

    def __repr__(self):
        return self.__str__()

