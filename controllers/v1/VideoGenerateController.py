from controllers.v1.base import new_router
from models.ImageToVideoRequest import ImageToVideoRequest
from fastapi import  Header
from service.runway import verify_profile
from tasks.runway_generate_video_task import generate_video_task
from utils import utils
from loguru import logger
from redis import Redis
import rq


router = new_router()
# 连接到 Redis 服务器
redis_conn = Redis(host='localhost', port=6379, db=0)
# 创建任务队列
generate_videos_queue = rq.Queue(name="runway_generate_videos_queue", connection=redis_conn)


@router.post('/generate-video')
async def generate_video(
        request: ImageToVideoRequest,
        user_id: int,
        authorization: str = Header(None, description="Runway授权令牌")):
    try:
        # 跑任务前验证下token是否失效
        result_code, result_str = await verify_profile(authorization)
        if result_code != 200:
            return utils.get_response(status=result_code, message=result_str)
        team_id = result_str
        job = generate_videos_queue.enqueue(generate_video_task,
                                            args=(request, team_id,authorization),
                                            job_id=utils.get_uuid(),
                                            meta={'user_id': user_id},
                                            timeout=3600,
                                            failure_ttl = 86400 * 5,
                                            result_ttl=86400)

        return utils.get_response(status=200, data={'job_id': job.id}, message='success')
    except Exception as e:
        logger.error(f'[api/generate-video] generate video task exception:{e}')
        return utils.get_response(status=500, message="服务器内部发生错误")


@router.get('/task/{task_id}/query')
async def query_task(task_id: str, user_id: int):
    job = generate_videos_queue.fetch_job(task_id)
    if not job:
        return utils.get_response(status=1004, message="查询的任务不存在")
    if job.meta.get('user_id') != user_id:
        return utils.get_response(status=403, message="无权访问该任务")
    return utils.get_response(status=200, data={'job_id':job.id, 'status':job.get_status()})

@router.get('/tasks')
async def query_all_task(user_id: int):
    res_tasks = []
    job_id_list = generate_videos_queue.get_job_ids()
    for job_id in job_id_list:
        job = generate_videos_queue.fetch_job(job_id)
        if job.meta.get('user_id') == user_id:
            res_tasks.append({'job_id': job.id, 'job_status': job.get_status()})

    return utils.get_response(status=200, data=res_tasks, message="success")

@router.get('/tasks/{task_id}/retry')
async def rerun_task(task_id: str, user_id: int):
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
    job = generate_videos_queue.fetch_job(task_id)
    if not job:
        return utils.get_response(status=1004, message="任务不存在")
    if job.meta.get('user_id') != user_id:
        return utils.get_response(status=403, message="无权访问该任务")

    return utils.get_response(status=200, data={'job_id':job.id, 'videos': job.latest_result().return_value}, message="success")