from models.LoginRequest import LoginRequest
from utils import utils
from controllers.v1.base import new_router
from passlib.context import CryptContext
from models.user import User
from fastapi import Body

router = new_router()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 模拟数据库
fake_db = {
    "admin": {
        "id": 1001,
        "username": "admin",
        "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # secret
    },
    "test001": {
        "id": 1002,
        "username": "test001",
        "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # secret
    }
}

# 工具函数
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return User(**user_dict)

def authenticate_user(username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


@router.post('/login')
async def login(login_request: LoginRequest = Body(...)):
    user = authenticate_user(login_request.username, login_request.password)
    if not user:
        utils.get_response(status=401, message="用户名或者密码验证失败")

    return utils.get_response(status=200, data={'user_id':user.id}, message="success")

