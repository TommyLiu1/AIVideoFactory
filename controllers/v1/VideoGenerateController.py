import os.path

from controllers.v1.base import new_router
from models.ImageToVideoRequest import ImageToVideoRequest
from fastapi import  Header
from urllib.parse import urlparse, unquote
from service.db.user_db_service import UserDBService
from service.db.video_task_db_service import VideoTaskDBService
from service.runway import verify_profile
from tasks.runway_generate_video_task import generate_video_task
from utils import utils
from loguru import logger
from redis import Redis, int_or_str
from rq.registry import FinishedJobRegistry, FailedJobRegistry
import rq
import requests


router = new_router()
# 连接到 Redis 服务器
redis_conn = Redis(host='localhost', port=6379, db=0)
# 创建任务队列
generate_videos_queue = rq.Queue(name="runway_generate_videos_queue", connection=redis_conn)

async def generate_video_for_client(request: ImageToVideoRequest, authorization: str, task_id: str = None):
    try:
        logger.info(f'[generate_video_for_client] generate video request:{request}')
        # 跑任务前验证下token是否失效
        result_code, result_str = await verify_profile(authorization)
        if result_code != 200:
            return False, result_str
        team_id = result_str
        job = generate_videos_queue.enqueue(generate_video_task,
                                            args=(request, team_id, authorization, task_id),
                                            job_id=task_id if task_id else utils.get_uuid(),
                                            timeout=3600,
                                            on_failure=handle_failed_job,
                                            on_success=handle_success_job,
                                            failure_ttl=86400 * 5,
                                            result_ttl=86400 * 2)
        if not job:
            return False, "任务提交失败，请稍后再试"
        return True, job.id
    except Exception as e:
        logger.error(f'[generate_video_for_client] generate video request exception:{e}')
        return False, "任务提交异常，请稍后再试"

def handle_success_job(job, connection, result):
    logger.info(f'[handle_success_job] Job {job.id} completed successfully.')
    try:
        user = UserDBService.get_user()
        video_save_path = os.path.join(user.vodeo_save_path, job.id)
        if not os.path.exists(video_save_path):
            os.makedirs(video_save_path)

        if type(result) is list:
            video_url_list = result[0]
            saved_path_list = []
            for video_url in video_url_list:
                logger.info(f'[handle_success_job] Video URL: {video_url}')
                saved_path = download_video(video_url, video_save_path, get_filename_from_url(video_url))
                saved_path_list.append(saved_path)
            # 更新数据库中的任务状态
            saved_path_str = ','.join(saved_path_list)
            VideoTaskDBService.update_task_status(job.id, 'finished', video_url=saved_path_str)
        VideoTaskDBService.update_task_status(job.id, 'finished', video_url="")
    except Exception as e:
        logger.error(f'[handle_success_job] Exception while handling success job: {e}')


def handle_failed_job(job,  connection, result):
    logger.error(f'[handle_failed_job] Job {job.id} failed with result: {result}')
    VideoTaskDBService.update_task_status(job.id, 'failed', video_url="")

def download_video(url, save_dir, filename=None):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    if not filename:
        filename = url.split('/')[-1].split('?')[0]
    save_path = os.path.join(save_dir, filename)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return save_path

def get_filename_from_url(url):
    path = urlparse(url).path
    filename = os.path.basename(path)
    return unquote(filename)

@router.post('/generate-video')
async def generate_video(
        request: ImageToVideoRequest,
        user_id: int,
        authorization: str = Header(None, description="Runway授权令牌")):
    try:
        logger.info(f'[api/generate-video] generate video request:{request}')
        # 跑任务前验证下token是否失效
        result_code, result_str = await verify_profile(authorization)
        if result_code != 200:
            return utils.get_response(status=result_code, message=result_str)
        team_id = result_str
        meta_info = {
            'user_id': user_id,
            'prompt':request.prompt,
            'model':request.model,
            'ratio':request.ratio,
            'video_nums':request.numbers
        }
        job = generate_videos_queue.enqueue(generate_video_task,
                                            args=(request, team_id,authorization),
                                            job_id=utils.get_uuid(),
                                            meta=meta_info,
                                            timeout=3600,
                                            failure_ttl = 86400 * 5,
                                            result_ttl=86400 * 2)

        return utils.get_response(status=200, data={'job_id': job.id}, message='success')
    except Exception as e:
        logger.error(f'[api/generate-video] generate video task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.get('/tasks/{task_id}/query')
async def query_task(task_id: str, user_id: int):
    logger.info(f'[api/tasks/{task_id}/query] query task request:{task_id}')
    job = generate_videos_queue.fetch_job(task_id)
    if not job:
        return utils.get_response(status=1004, message="查询的任务不存在")
    if job.meta.get('user_id') != user_id:
        return utils.get_response(status=403, message="无权访问该任务")
    return_res_dict = {
        'user_id': job.meta.get('user_id'),
        'job_id': job.id,
        'prompt': job.meta.get('prompt'),
        'model': job.meta.get('model'),
        'ratio': job.meta.get('ratio'),
        'video_nums': job.meta.get('video_nums'),
        'job_status': job.get_status()
    }
    return utils.get_response(status=200, data=return_res_dict, message='success')

@router.get('/tasks')
async def query_all_task(user_id: int):
    logger.info(f'[api/tasks] query all task request:{user_id}')
    res_tasks = []
    # 查询队列中的job
    job_id_list = generate_videos_queue.get_job_ids()
    for queue_job_id in job_id_list:
        queue_job = generate_videos_queue.fetch_job(queue_job_id)
        if queue_job.meta.get('user_id') == user_id:
            return_res_dict = {
                'user_id': queue_job.meta.get('user_id'),
                'job_id': queue_job.id,
                'prompt': queue_job.meta.get('prompt'),
                'model': queue_job.meta.get('model'),
                'ratio': queue_job.meta.get('ratio'),
                'video_nums': queue_job.meta.get('video_nums'),
                'job_status': queue_job.get_status()
            }
            res_tasks.append(return_res_dict)
    # 查询已开始但未完成的任务
    workers = rq.Worker.all(connection=redis_conn)
    for worker in workers:
        cur_run_job = worker.get_current_job()
        if cur_run_job and cur_run_job.meta.get('user_id') == user_id:
            return_res_dict = {
                'user_id': cur_run_job.meta.get('user_id'),
                'job_id': cur_run_job.id,
                'prompt': cur_run_job.meta.get('prompt'),
                'model': cur_run_job.meta.get('model'),
                'ratio': cur_run_job.meta.get('ratio'),
                'video_nums': cur_run_job.meta.get('video_nums'),
                'job_status': cur_run_job.get_status()
            }
            res_tasks.append(return_res_dict)

    # 检查已完成的任务
    finished_registry = FinishedJobRegistry(generate_videos_queue.name, generate_videos_queue.connection)
    for finished_job_id in finished_registry.get_job_ids():
        finished_job = generate_videos_queue.fetch_job(finished_job_id)
        if finished_job.meta.get('user_id') == user_id:
            return_res_dict = {
                'user_id': finished_job.meta.get('user_id'),
                'job_id': finished_job.id,
                'prompt': finished_job.meta.get('prompt'),
                'model': finished_job.meta.get('model'),
                'ratio': finished_job.meta.get('ratio'),
                'video_nums': finished_job.meta.get('video_nums'),
                'job_status': finished_job.get_status()
            }
            res_tasks.append(return_res_dict)

        # 检查失败的任务
        failed_registry = FailedJobRegistry(generate_videos_queue.name, generate_videos_queue.connection)
        for failed_job_id in failed_registry.get_job_ids():
            failed_job = generate_videos_queue.fetch_job(failed_job_id)
            if failed_job.meta.get('user_id') == user_id:
                return_res_dict = {
                    'user_id': failed_job.meta.get('user_id'),
                    'job_id': failed_job.id,
                    'prompt': failed_job.meta.get('prompt'),
                    'model': failed_job.meta.get('model'),
                    'ratio': failed_job.meta.get('ratio'),
                    'video_nums': failed_job.meta.get('video_nums'),
                    'job_status': failed_job.get_status()
                }
                res_tasks.append(return_res_dict)

    return utils.get_response(status=200, data=res_tasks, message="success")

@router.get('/tasks/{task_id}/retry')
async def rerun_task(task_id: str, user_id: int):
    logger.info(f'[api/tasks/{task_id}/retry] retry task request:{task_id}')
    job = generate_videos_queue.fetch_job(task_id)
    if not job:
        return utils.get_response(status=1004, message="重试的任务不存在")
    if job.meta.get('user_id') != user_id:
        return utils.get_response(status=403, message="无权访问该任务")
    job = job.requeue(at_front=True)
    if not job:
        return utils.get_response(500, message=f'任务：{task_id}重启失败')
    return utils.get_response(status=200, data={'job_id':job.id, 'job_status': job.get_status()}, message="success")

@router.get('/tasks/{task_id}/download')
async def rerun_task(task_id: str, user_id: int):
    logger.info(f'[api/tasks/{task_id}/download] download task request:{task_id}')
    job = generate_videos_queue.fetch_job(task_id)
    if not job:
        return utils.get_response(status=1004, message="任务不存在")
    if job.meta.get('user_id') != user_id:
        return utils.get_response(status=403, message="无权访问该任务")

    return utils.get_response(status=200, data={'job_id':job.id, 'videos': job.latest_result().return_value}, message="success")