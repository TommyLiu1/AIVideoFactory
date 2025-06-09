"""Application configuration - root APIRouter.

Defines all FastAPI application endpoints.

Resources:
    1. https://fastapi.tiangolo.com/tutorial/bigger-applications

"""

from fastapi import APIRouter
from controllers.v1 import VideoGenerateController,LoginController
root_api_router = APIRouter()
# 添加文生视频的路由
root_api_router.include_router(VideoGenerateController.router)
# 添加登录的路由
root_api_router.include_router(LoginController.router)