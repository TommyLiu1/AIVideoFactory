import secrets

from models.LoginRequest import LoginRequest
from service.db.user_db_service import UserDBService
from utils import utils
from controllers.v1.base import new_router
from passlib.context import CryptContext
from fastapi import Body
from datetime import datetime, timedelta
from loguru import logger
import jwt
import os

router = new_router()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JW_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1天

def verify_password(plain_password: str, salt:str, hashed_password: str):
    return pwd_context.verify(plain_password + salt, hashed_password)


def authenticate_user(username: str, password: str):
    user = UserDBService.get_user_by_name(username)
    if not user:
        return None
    if not user.is_active:
        return None
    now = datetime.now()
    if user.valid_from and now < user.valid_from:
        return None
    if user.valid_to and now > user.valid_to:
        return None
    if not verify_password(password, user.salt, user.password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post('/logout')
def logout(user_id: int = Body(...), token: str = Body(None)):
    """
    用户登出，token立即失效，用户active变为0。
    """
    if not user_id or not token:
        return utils.get_response(status=400, message="用户ID缺失或者Token缺失")
    user = UserDBService.get_user_by_id(user_id)
    if not user:
        return utils.get_response(status=404, message="用户不存在")
    if not user.is_active:
        return utils.get_response(status=400, message="用户已登出")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if user_id != int(payload.get("user_id")):
            return utils.get_response(status=401, message="无效的用户ID")
    except Exception as e:
        logger.error(f"Token解码失败: {e}")
        return utils.get_response(status=401, message="无效token")
    user = UserDBService.update_user(user_id, is_active=False)
    if not user:
        return utils.get_response(status=404, message="用户不存在或已被禁用")
    return utils.get_response(status=200, message="登出成功")


@router.post('/login')
async def login(login_request: LoginRequest = Body(...)):
    user = authenticate_user(login_request.username, login_request.password)
    if not user:
        return utils.get_response(status=401, message="用户名或密码错误，或账号无效/过期")
    access_token = create_access_token(data={"user_id": user.id, "username": user.username})
    return utils.get_response(status=200, data={"token": access_token,
                                                "user_id": user.id,
                                                "username": user.username,
                                                "secret_key": SECRET_KEY}, message="success")

