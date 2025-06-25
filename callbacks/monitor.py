
from loguru import logger
from service.db.video_task_db_service import VideoTaskDBService
import traceback

def handle_failed_job(job, connection, type, value, traceback_obj):
    """
    处理失败的Job，记录日志
    """
    try:
        user_id = int(job.meta.get('user_id', 0))
        tb_list = traceback.format_tb(traceback_obj) if traceback_obj else []
        error_traceback = "".join(tb_list)
        logger.info(
            f"[handle_failed_job] User id:{user_id}, Job {job.id} failed with exception: {error_traceback}")
        if error_traceback.find('RunwayTaskFailedException') != -1:
            error_value = 'Runway运行任务失败'
        elif error_traceback.find('RunwayCreditException') != -1:
            error_value = 'Runway评估任务积分失败'
        elif error_traceback.find('RunwayTokenExpiredException') != -1:
            error_value = 'Runway账户过期'
        else:
            error_value = value
        # 更新数据库中的任务状态
        result = VideoTaskDBService.update_video_task_execution(
            task_id=job.id,
            prompt=job.meta.get('prompt'),
            model=job.meta.get('model'),
            ratio=job.meta.get('ratio'),
            video_duration=job.meta.get('video_duration'),
            video_nums=job.meta.get('video_nums'),
            task_status='failed',
            failed_reason=str(error_value)
        )
        if not result:
            logger.error(f"[handle_failed_job] Failed to update video task execution for job {job.id} with user_id {user_id}")

    except Exception as e:
        logger.error(f'[handle_failed_job] Exception while handling failed job: {e}')


def handle_finished_job(job, connection, result, *args, **kwargs):
    """
    处理成功的Job，记录日志
    """
    try:
        user_id = int(job.meta.get('user_id', 0))
        logger.info(f"[handle_success_job] User id:{user_id}, Job { job.id} finished with result: {result}")
        video_url_str = ''
        if type(result) is list:
            video_url_or_list = result[0]
            video_url_str = ','.join(video_url_or_list)

        if type(result) is str:
            video_url_str = result

        # 更新数据库中的任务状态
        result = VideoTaskDBService.update_video_task_execution(
            task_id=job.id,
            prompt=job.meta.get('prompt'),
            model=job.meta.get('model'),
            ratio=job.meta.get('ratio'),
            video_duration=job.meta.get('video_duration'),
            video_nums=job.meta.get('video_nums'),
            task_status='finished',
            video_url=video_url_str
        )
        if not result:
            logger.error(
                f"[handle_finished_job] Failed to update video task execution for job {job.id} with user_id {user_id}")

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
        result = VideoTaskDBService.update_video_task_execution(
            task_id=job.id,
            prompt=job.meta.get('prompt'),
            model=job.meta.get('model'),
            ratio=job.meta.get('ratio'),
            video_duration=job.meta.get('video_duration'),
            video_nums=job.meta.get('video_nums'),
            task_status='canceled'
        )
        if not result:
            logger.error(f"[handle_canceled_job] Failed to update video task execution for job {job.id} with user_id {user_id}")
    except Exception as e:
        logger.error(f'[handle_canceled_job] Exception while handling canceled job: {e}')

