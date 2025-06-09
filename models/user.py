from pydantic import BaseModel

class User(BaseModel):
    id: int
    username: str
    password: str  # 存储的是哈希后的密码