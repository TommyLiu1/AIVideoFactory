from utils import utils
from controllers.v1.base import new_router
from service.db.user_settings_db_service import UserSettingsDBService
from fastapi import Request, Depends
from utils.auth import verify_token_signature
from loguru import logger
router = new_router(dependencies=[Depends(verify_token_signature)])

@router.get("/settings/{user_id}/get", tags=["get user settings"])
def get_user_settings(user_id: int):
    """
    获取用户设置
    """
    try:
        if not user_id:
            return utils.get_response(status=10001, message="query参数缺少[user_id]")

        user_setting = UserSettingsDBService.get_user_settings(user_id)
        if not user_setting:
            return utils.get_response(status=10002, message="无效用户, 请检查用户ID是否正确")

        return utils.get_response(status=200, message="数据获取成功", data=user_setting.to_dict())
    except Exception as e:
        logger.error(f"[get_user_settings] 获取用户设置失败: {e}")
        return utils.get_response(status=500, message=f"获取用户设置失败")


@router.post("/settings/{user_id}/create_or_update", tags=["create or update user settings"])
async def create_or_update_user_settings(user_id: int, request: Request):
    """
    创建或更新用户设置
    """
    try:
        if not user_id:
            return utils.get_response(status=10001, message="query参数缺少[user_id]")

        data = await request.json()
        logger.info(f"[create_user_settings] 接收到的数据: {data}")
        token = data.get("token")
        video_save_path = data.get("video_save_path")
        if not all([token, video_save_path]):
            return utils.get_response(status=10001, message="提交的数据缺少必要的数据[token, video_save_path]")

        user_setting = UserSettingsDBService.get_user_settings(user_id)
        if not user_setting:
            created = UserSettingsDBService.create_user_settings(user_id=user_id, token=token,
                                                                 save_video_path=video_save_path)
            if not created:
                logger.error(f"[create_user_settings] 创建用户设置失败, 用户ID: {user_id}, 数据: {data}")
                return utils.get_response(status=10002, message="数据创建失败, 请检查用户ID是否正确")
            return utils.get_response(status=200, message="数据创建成功", data=created.to_dict())

        updated = UserSettingsDBService.update_user_settings(user_id, token=token, save_video_path=video_save_path)
        if not updated:
            logger.error(f"[update_user_settings] 更新用户设置失败, 用户ID: {user_id}, 数据: {data}")
            return utils.get_response(status=10002, message="数据更新失败, 请检查用户ID是否正确")
        return utils.get_response(status=200, message="数据更新成功", data=updated.to_dict())

    except Exception as e:
        logger.error(f"[create_user_settings] 创建用户设置失败: {e}")
        return utils.get_response(status=500, message=f"创建用户设置失败")

