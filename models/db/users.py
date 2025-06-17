
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from models.db.database_base import Base

class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    # 密码盐
    salt = Column(String(100), nullable=False)
    # 用户类型，1-runway共享，2-runway独享，3-即梦
    user_type = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime(timezone=True),nullable=False)
    valid_to = Column(DateTime(timezone=True),nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "user_type": self.user_type,
            "is_active": self.is_active,
            "valid_from": self.valid_from.strftime("%Y-%m-%d %H:%M:%S") if self.valid_from else None,
            "valid_to": self.valid_to.strftime("%Y-%m-%d %H:%M:%S") if self.valid_to else None,
        }

    def __str__(self) -> str:
        return (
            f"User(id={self.id}, username='{self.username}', user_type={self.user_type}, "
            f"is_active={self.is_active}, valid_from='{self.valid_from}', valid_to='{self.valid_to}')"
        )

    def __repr__(self):
        return self.__str__()

