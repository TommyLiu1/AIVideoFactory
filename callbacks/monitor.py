
from loguru import logger
from service.db.video_task_db_service import VideoTaskDBService


def handle_failed_job(job, connection, type, value, traceback):
    """
    处理失败的Job，记录日志
    """
    try:
        user_id = int(job.meta.get('user_id', 0))
        logger.info(
            f"[handle_failed_job] User id:{user_id}, Job {job.id} failed with exception: {traceback}")
        # 更新数据库中的任务状态
        VideoTaskDBService.update_video_task_execution(job.id, user_id=user_id, task_status='failed', failed_reason=str(value))
    except Exception as e:
        logger.error(f'[handle_failed_job] Exception while handling failed job: {e}')


def handle_finished_job(job, connection, result, *args, **kwargs):
    """
    处理成功的Job，记录日志
    """
    try:
        user_id = int(job.meta.get('user_id', 0))
        logger.info(f"[handle_success_job] User id:{user_id}, Job { job.id} finished with result: {result}")
        VideoTaskDBService.update_video_task_execution(job.id, user_id=user_id, task_status='finished', video_url=result)
    except Exception as e:
        logger.error(f'[handle_success_job] Exception while handling success job: {e}')


def handle_canceled_job(job, connection):
    """
    处理取消的Job，记录日志
    """
    try:
        user_id = int(job.meta.get('user_id', 0))
        logger.info(f"[handle_canceled_job] User id:{user_id}, Job {job.id} was canceled.")
        # 更新数据库中的任务状态
        VideoTaskDBService.update_video_task_execution(job.id, user_id=user_id, task_status='canceled')
    except Exception as e:
        logger.error(f'[handle_canceled_job] Exception while handling canceled job: {e}')

