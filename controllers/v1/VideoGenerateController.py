import os
from urllib.parse import urlparse, unquote

import requests

from callbacks.monitor import handle_failed_job, handle_finished_job, handle_canceled_job
from controllers.v1.base import new_router
from models.ImageToVideoRequest import ImageToVideoRequest
from fastapi import Depends, Request

from service.db.user_settings_db_service import UserSettingsDBService
from service.db.video_task_db_service import VideoTaskDBService
from service.runway import verify_profile
from tasks.runway_generate_video_task import generate_video_task
from utils import utils
from loguru import logger
from redis import Redis
from utils.auth import verify_token_signature
import rq



router = new_router(dependencies=[Depends(verify_token_signature)])
# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
# 连接到 Redis 服务器
redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
# 创建任务队列
generate_videos_queue = rq.Queue(name="runway_generate_videos_queue", connection=redis_conn)


@router.post('/tasks/create')
async def create_generate_video_task(
        task_request: ImageToVideoRequest,
        user_id: int):
    try:
        logger.info(f'[create_generate_video_task] create generate video request:{task_request}')
        # 跑任务前验证下token是否失效
        execution_task = VideoTaskDBService.create_video_task_execution(
            user_id = user_id,
            prompt = task_request.prompt,
            model = task_request.model,
            model_supply = 'runway',
            ratio = task_request.ratio,
            video_duration = task_request.video_duration,
            video_nums = task_request.numbers,
            task_status='pending',
        )
        if not execution_task:
            logger.warning(f'[create_generate_video_task] create video task execution failed for user_id:{user_id}')
            return utils.get_response(status=500, message="创建视频执行任务失败")

        return utils.get_response(status=200, data={'job_id': execution_task.get('task_id')}, message='success')
    except Exception as e:
        logger.error(f'[create_generate_video_task] create generate video task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")

@router.get('/tasks/{task_id}/run')
async def run_generate_video_task(task_id: str, user_id: int):
    try:
        logger.info(f'[create_generate_video_task] run video generate task, task id:{task_id}, user id:{user_id}')
        # 跑任务前验证下token是否失效
        user_setting = UserSettingsDBService.get_user_settings(user_id)
        if not user_setting:
            logger.error(f'[create_generate_video_task] user settings not found for user_id:{user_id}')
            return utils.get_response(status=1001, message="用户设置未找到")

        result_code, result_str = await verify_profile(user_setting.get('token'))
        if result_code != 200:
            return utils.get_response(status=result_code, message=result_str)
        team_id = result_str
        task_request = VideoTaskDBService.get_video_task_execution_by_task_id(task_id)
        if not task_request:
            logger.error(f'[create_generate_video_task] video task execution not found for task_id:{task_id}')
            return utils.get_response(status=1004, message="任务记录未找到")
        meta_info = {
            'user_id': user_id,
            'prompt':task_request.get('prompt'),
            'model':task_request.get('model'),
            'ratio':task_request.get('ratio'),
            'video_nums':task_request.get('video_nums')
        }
        job = generate_videos_queue.enqueue_call(generate_video_task,
                                            args=(task_request, team_id, user_setting.get('token')),
                                            job_id=task_id,
                                            meta=meta_info,
                                            timeout=3600,
                                            on_failure=handle_failed_job,
                                            on_success=handle_finished_job,
                                            on_stopped=handle_canceled_job,
                                            failure_ttl = 86400 * 5,
                                            result_ttl=86400 * 2)

        return utils.get_response(status=200, data={'job_id': job.id}, message='success')
    except Exception as e:
        logger.error(f'[create_generate_video_task] create generate video task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")

@router.post('/tasks/batch_run')
async def batch_run_generate_video_task(request: Request):
    try:
        data = await request.json()
        task_ids = data.get('task_ids')
        user_id = data.get('user_id')
        job_ids = []
        logger.info(f'[batch_run_generate_video_task] batch run generate video task, the task ids:{task_ids}, user id:{user_id}')
        # 跑任务前验证下token是否失效
        user_setting = UserSettingsDBService.get_user_settings(user_id)
        if not user_setting:
            logger.error(f'[batch_run_generate_video_task] user settings not found for user_id:{user_id}')
            return utils.get_response(status=1001, message="用户设置未找到")

        result_code, result_str = await verify_profile(user_setting.get('token'))
        if result_code != 200:
            return utils.get_response(status=result_code, message=result_str)
        team_id = result_str
        task_request_list = VideoTaskDBService.get_video_task_executions_by_task_ids(task_ids)
        for task_request in task_request_list:
            meta_info = {
                'user_id': user_id,
                'prompt': task_request.get('prompt'),
                'model': task_request.get('model'),
                'ratio': task_request.get('ratio'),
                'video_nums': task_request.get('video_nums')
            }
            job = generate_videos_queue.enqueue_call(generate_video_task,
                                                     args=(task_request, team_id, user_setting.get('token')),
                                                     job_id=task_request.get('task_id'),
                                                     meta=meta_info,
                                                     timeout=3600,
                                                     on_failure=handle_failed_job,
                                                     on_success=handle_finished_job,
                                                     on_stopped=handle_canceled_job,
                                                     failure_ttl=86400 * 5,
                                                     result_ttl=86400 * 2)
            job_ids.append(job.id)
        return utils.get_response(status=200, data={'job_ids': job_ids}, message='success')
    except Exception as e:
        logger.error(f'[batch_run_generate_video_task] batch run generate video task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.get('/tasks/{task_id}/query')
async def query_task(task_id: str, user_id: int):
    logger.info(f'[api/tasks/{task_id}/query] query task request:{task_id}')
    try:
        task = VideoTaskDBService.get_video_task_execution_by_task_id(task_id)
        if not task:
            logger.error(f"[api/tasks/{task_id}/query] query task failed: task not found for task_id:{task_id}")
            return utils.get_response(status=1004, message="查询的任务不存在")
        if task.get('user_id') != user_id:
            logger.error(
                f"[api/tasks/{task_id}/query] query task failed: user_id {user_id} does not have access to task {task_id}")
            return utils.get_response(status=403, message="无权访问该任务")

        return utils.get_response(status=200, data=task, message='success')
    except Exception as e:
        logger.error(f"[api/tasks/{task_id}/query] query task exception: {e}")
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.post('/tasks/{task_id}/update')
async def update_task(task_id: str, user_id: int,  task_request: ImageToVideoRequest):
    try:
        logger.info(
            f'[api/tasks/{task_id}/update] update task request:{task_id}, user_id:{user_id}, task_request:{task_request}')
        task = VideoTaskDBService.get_video_task_execution_by_task_id(task_id)
        if not task:
            logger.error(f"[api/tasks/{task_id}/update] update task failed: task not found for task_id:{task_id}")
            return utils.get_response(status=1004, message="查询的任务不存在")
        if  task.get('user_id') != user_id:
            logger.error(
                f"[api/tasks/{task_id}/update] update task failed: user_id {user_id} does not have access to task {task_id}")
            return utils.get_response(status=403, message="无权访问该任务")
        logger.info(
            f'[api/tasks/{task_id}/update] update task request:{task_id}, user_id:{user_id}, task_request:{task_request}')
        # 更新任务执行记录
        result = VideoTaskDBService.update_video_task_execution(
            task_id=task_id,
            prompt=task_request.prompt,
            model=task_request.model,
            ratio=task_request.ratio,
            video_duration=task_request.video_duration,
            video_nums=task_request.numbers
        )
        if not result:
            logger.warning(f'[api/tasks/{task_id}/update] update video task execution failed for task_id:{task_id}')
            return utils.get_response(status=500, message="更新任务失败")
        return utils.get_response(status=200, data=result, message='success')
    except Exception as e:
        logger.error(f'[api/tasks/{task_id}/update] update task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.get('/tasks')
async def query_all_task(user_id: int):
    try:
        logger.info(f'[api/tasks] query all task request:{user_id}')
        res_tasks = []
        task_list = VideoTaskDBService.get_video_task_executions_by_user_id(user_id)
        if not task_list:
            return utils.get_response(status=1004, message="没有查询到任务记录", data=res_tasks)
        for task in task_list:
            res_tasks.append(task)

        return utils.get_response(status=200, data=res_tasks, message="success")
    except Exception as e:
        logger.error(f'[api/tasks] query all task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.get('/tasks/{task_id}/retry')
async def rerun_task(task_id: str, user_id: int):
    try:
        logger.info(f'[api/tasks/{task_id}/retry] retry task request:{task_id}, user_id:{user_id}')
        job = generate_videos_queue.fetch_job(task_id)
        if not job:
            return utils.get_response(status=1004, message="重试的任务不存在")
        if job.meta.get('user_id') != user_id:
            return utils.get_response(status=403, message="无权访问该任务")
        job = job.requeue(at_front=True)
        if not job:
            return utils.get_response(500, message=f'任务：{task_id}重启失败')
        result = VideoTaskDBService.update_video_task_execution(task_id=task_id, task_status='queued')
        if not result:
            logger.warning(f'[api/tasks/{task_id}/retry] update video task execution failed for task_id:{task_id}')
        return utils.get_response(status=200, data={'job_id': job.id, 'job_status': job.get_status()},
                                  message="success")
    except Exception as e:
        logger.error(f'[api/tasks/{task_id}/retry] retry task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")

@router.post('/tasks/batch_retry')
async def batch_rerun_task(request: Request):
    try:
        data = await request.json()
        task_ids = data.get('task_ids')
        user_id = data.get('user_id')
        logger.info(f'[/tasks/batch_retry] batch retry task request:{task_ids}, user_id:{user_id}')
        rerun_task_ids = []
        for task_id in task_ids or []:
            job = generate_videos_queue.fetch_job(task_id)
            if not job:
                logger.error(f"[/tasks/batch_retry] retry task failed: job not found for task_id:{task_id}, user_id:{user_id}")
                continue
            if job.meta.get('user_id') != user_id:
                logger.error(f"[/tasks/batch_retry] retry task failed: user_id {user_id} does not have access to task {task_id}")
                continue
            job = job.requeue(at_front=True)
            if not job:
                logger.error(f"[/tasks/batch_retry] retry task failed: job requeue failed for task_id:{task_id}")
                continue
            result = VideoTaskDBService.update_video_task_execution(task_id=task_id, task_status='queued')
            if not result:
                logger.error(f'[api/tasks/{task_id}/retry] update video task execution failed for task_id:{task_id}')
            rerun_task_ids.append(task_id)
        return utils.get_response(status=200, data={'job_ids': rerun_task_ids}, message="success")
    except Exception as e:
        logger.error(f'[/tasks/batch_retry] batch retry task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.get('/tasks/{task_id}/cancel')
async def cancel_task(task_id: str, user_id: int):
    try:
        logger.info(f'[api/tasks/{task_id}/cancel] cancel task request:{task_id}, user_id:{user_id}')
        job = generate_videos_queue.fetch_job(task_id)
        if not job:
            return utils.get_response(status=1004, message="取消的任务不存在")
        if job.meta.get('user_id') != user_id:
            return utils.get_response(status=403, message="无权访问该任务")
        try:
            job.cancel()
        except Exception as e:
            logger.error(f'[api/tasks/{task_id}/cancel] cancel task exception:{e}')
            return utils.get_response(status=500, message=f'任务：{task_id}取消失败')
        result = VideoTaskDBService.update_video_task_execution(task_id=task_id, task_status='canceled')
        if not result:
            logger.warning(f'[api/tasks/{task_id}/cancel] update video task execution failed for task_id:{task_id}')
        return utils.get_response(status=200, data={'job_id': job.id, 'job_status': 'canceled'}, message="success")
    except Exception as e:
        logger.error(f'[api/tasks/{task_id}/cancel] cancel task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")

@router.post('/tasks/batch_cancel')
async def batch_cancel_task(request: Request):
    try:
        data = await request.json()
        task_ids = data.get('task_ids')
        user_id = data.get('user_id')
        logger.info(f'[/tasks/batch_cancel] batch cancel task request:{task_ids}, user_id:{user_id}')
        batch_cancel_job_ids = []
        for task_id in task_ids or []:
            job = generate_videos_queue.fetch_job(task_id)
            if not job:
                logger.error(f"[/tasks/batch_cancel] cancel task failed: job not found for task_id:{task_id}")
                continue
            if job.meta.get('user_id') != user_id:
                logger.error(
                    f"[/tasks/batch_cancel] cancel task failed: user_id {user_id} does not have access to task {task_id}")
                continue
            try:
                job.cancel()
                batch_cancel_job_ids.append(task_id)
            except Exception as e:
                logger.error(f'[/tasks/batch_cancel] cancel task exception:{e}')
                continue
            result = VideoTaskDBService.update_video_task_execution(task_id=task_id, task_status='canceled')
            if not result:
                logger.error(f'[/tasks/batch_cancel] update video task execution failed for task_id:{task_id}')
        return utils.get_response(status=200, data={'job_ids': batch_cancel_job_ids}, message="success")
    except Exception as e:
        logger.error(f'[/tasks/batch_cancel] batch cancel task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.get('/tasks/{task_id}/download')
async def download_task_result(task_id: str, user_id: int):
    try:
        logger.info(f'[api/tasks/{task_id}/download] download task request:{task_id}')
        job = generate_videos_queue.fetch_job(task_id)
        if not job:
            job = VideoTaskDBService.get_video_task_execution_by_task_id(task_id)
            if not job:
                logger.error(f'[api/tasks/{task_id}/download] download task failed: task not found')
                return utils.get_response(status=1004, message="任务不存在")
            job_user_id = job.get('user_id')
            job_result = job.get('video_url')
        else:
            job_result = job.latest_result().return_value
            job_user_id = job.meta.get('user_id')

        if job_user_id != user_id:
            return utils.get_response(status=403, message="无权访问该任务")

        user_setting = UserSettingsDBService.get_user_settings(job_user_id)
        video_save_path = os.path.join(user_setting.get('save_video_path'), job.id)
        if not os.path.exists(video_save_path):
            os.makedirs(video_save_path)

        video_url_or_list = []
        saved_path_list = []
        if type(job_result) is list:
            video_url_or_list = job_result[0]
            if type(video_url_or_list) is not list:
                video_url_or_list = [video_url_or_list]

        for video_url in video_url_or_list:
            logger.info(f'begin to download video url: {video_url}')
            saved_path = download_video(video_url, video_save_path, get_filename_from_url(video_url))
            saved_path_list.append(saved_path)

        # 过滤掉None，确保join参数都是str
        saved_path_list = [str(path) for path in saved_path_list if path]
        saved_path_str = ','.join(saved_path_list)
        if len(saved_path_list) > 0:
            logger.info(f"Videos saved to: {saved_path_list}")
            VideoTaskDBService.update_video_task_execution(task_id=task_id, video_url=saved_path_str)

        return utils.get_response(status=200, data={'job_id': job.id, 'video_save_path': saved_path_str},
                                  message="success")
    except Exception as e:
        logger.error(f'[api/tasks/{task_id}/download] download task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")



def download_video(url, save_dir, filename=None):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
    if not filename:
        filename = url.split('/')[-1].split('?')[0]
    save_path = os.path.join(save_dir, filename)
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        logger.info(f"视频下载成功: {url} -> {save_path}")
        return save_path
    except Exception as e:
        logger.error(f"下载视频失败: {url}, 错误: {e}")
        return None


def get_filename_from_url(url):
    path = urlparse(url).path
    filename = os.path.basename(path)
    return unquote(filename)

@router.delete('/tasks/{task_id}/delete')
async def delete_task(task_id: str, user_id: int):
    try:
        logger.info(f'[api/tasks/{task_id}/delete] delete task request:{task_id}, user_id:{user_id}')
        job = generate_videos_queue.fetch_job(task_id)
        if job:
            if job.meta.get('user_id') != user_id:
                return utils.get_response(status=403, message="无权删除该任务")
            try:
                job.delete()
            except Exception as e:
                logger.error(f'[api/tasks/{task_id}/delete] delete task exception:{e}')
                return utils.get_response(status=500, message=f'任务：{task_id}删除失败')
        # 同步删除数据库记录
        VideoTaskDBService.delete_video_task_execution(user_id, task_id)
        return utils.get_response(status=200, message="任务删除成功")
    except Exception as e:
        logger.error(f'[api/tasks/{task_id}/delete] delete task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.delete('/tasks/batch_delete')
async def batch_delete_tasks(request: Request):
    try:
        logger.info(f'[api/tasks/batch_delete] batch delete tasks request: {request}')
        failed = []
        data = await request.json()
        task_ids = data.get('task_ids', [])
        user_id = data.get('user_id')
        for task_id in task_ids:
            job = generate_videos_queue.fetch_job(task_id)
            if job and job.meta.get('user_id') == user_id:
                try:
                    job.delete()
                except Exception as e:
                    logger.error(f'[api/tasks/batch_delete] delete task {task_id} exception:{e}')
                    failed.append(task_id)
                    continue
            # 同步删除数据库记录
            try:
                VideoTaskDBService.delete_video_task_execution(user_id, task_id)
            except Exception as e:
                logger.error(f'[api/tasks/batch_delete] delete db task {task_id} exception:{e}')
                failed.append(task_id)
        if failed:
            return utils.get_response(status=207, message=f'部分任务删除失败: {failed}', data={'failed': failed})
        return utils.get_response(status=200, message="批量任务删除成功")
    except Exception as e:
        logger.error(f'[api/tasks/batch_delete] batch delete tasks exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")
