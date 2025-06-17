from utils import utils
from controllers.v1.base import new_router
from service.db.user_settings_db_service import UserSettingsDBService
from fastapi import Request, Depends
from utils.auth import verify_token_signature

router = new_router(dependencies=[Depends(verify_token_signature)])

@router.get("/settings/get", tags=["User Settings"])
def get_user_settings(user_id: str):
    """
    获取用户设置
    """
    if not user_id:
        return utils.get_response(status=10001, message="query参数缺少[user_id]")

    user_setting = UserSettingsDBService.get_user_settings(user_id)
    if not user_setting:
        return utils.get_response(status=10002, message="无效用户, 请检查用户ID是否正确")

    return utils.get_response(status=200, message="数据获取成功", data=user_setting.to_dict())

@router.post("/settings/update", tags=["User Settings"])
async def update_user_settings(request: Request):
    """
    更新用户设置
    """
    data = await request.json()
    user_id = data.get("user_id")
    token = data.get("token")
    video_save_path = data.get("video_save_path")
    if not all([user_id, token, video_save_path]):
        return utils.get_response(status=10001, message="缺少必要参数[user_id, token, video_save_path]")
    updated = UserSettingsDBService.update_user_settings(user_id=user_id, token=token, save_video_path=video_save_path)
    if not updated:
        return utils.get_response(status=10002, message="无效用户配置, 请检查用户ID是否正确")
    return utils.get_response(status=200, message="数据更新成功", data=updated.to_dict())

