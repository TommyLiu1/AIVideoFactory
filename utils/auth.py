from fastapi import Header, HTTPException, status, Request
from jwt import ExpiredSignatureError
import hashlib
import jwt
import os
import secrets
import redis.asyncio as aioredis
from datetime import datetime
from loguru import logger
from service.db.user_db_service import UserDBService

SECRET_KEY = os.getenv("JW_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ALLOWED_TIMESTAMP_SKEW = 300  # 允许5分钟内
# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

REDIS_NONCE_EXPIRE = 300  # nonce有效期5分钟
redis = None  # aioredis连接池

async def get_redis():
    global redis
    if redis is None:
        redis = await aioredis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            encoding="utf-8",
            decode_responses=True
        )
    return redis

async def verify_token_signature(
    request: Request,
    token: str = Header(..., alias="X-Token"),
    signature: str = Header(..., alias="X-Signature"),
    timestamp: str = Header(..., alias="X-Timestamp"),
    nonce: str = Header(..., alias="X-Nonce")
):
    """
    高安全性签名校验：token+timestamp+nonce+body+secret
    """
    # 1. 校验token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("user_id"))
        user = UserDBService.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效用户")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户已登用")
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token已过期")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效token")

    # 2. 校验timestamp
    try:
        ts = int(timestamp)
    except Exception:
        raise HTTPException(status_code=400, detail="timestamp格式错误")
    now = int(datetime.now().timestamp())
    if abs(now - ts) > ALLOWED_TIMESTAMP_SKEW:
        raise HTTPException(status_code=401, detail="请求已过期")
    # 3. 校验nonce防重放（用Redis持久化）
    redis_client = await get_redis()
    if await redis_client.get(f"nonce:{nonce}"):
        raise HTTPException(status_code=401, detail="重复请求")
    await redis_client.setex(f"nonce:{nonce}", REDIS_NONCE_EXPIRE, 1)
    # 4. 获取body
    body = await request.body()
    body_str = body.decode("utf-8") if body else ""
    # 5. 计算签名
    logger.info(f"Calculating signature with token: {token}, secret_key: {SECRET_KEY}, timestamp: {timestamp}, nonce: {nonce}, body: {body_str}")
    sign_str = token + timestamp + nonce + body_str + SECRET_KEY
    expected_signature = hashlib.sha256(sign_str.encode()).hexdigest()
    logger.info(f"Expected signature: {expected_signature}, Provided signature: {signature}")
    if signature != expected_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="签名不合法")
    return payload
