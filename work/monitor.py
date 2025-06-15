import os
import time
from urllib.parse import urlparse, unquote

import requests
from redis import Redis
from rq import Queue
from rq.registry import FailedJobRegistry, FinishedJobRegistry, CanceledJobRegistry
from loguru import logger

from service.db.user_db_service import UserDBService
from service.db.video_task_db_service import VideoTaskDBService


def monitor_jobs(interval=10):
    """
    每隔指定间隔时间查询失败和成功的Job情况

    :param interval: 监控间隔时间（秒），默认为5秒
    """
    # 连接到Redis
    redis_conn = Redis()

    # 获取所有队列
    queues = Queue.all(connection=redis_conn)
    failed_jobs = []
    finished_jobs = []
    canceled_jobs = []
    while True:
        # 检查每个队列
        for queue in queues:
            logger.info(f"Job状态检查,队列: {queue.name} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            # 获取失败的Job注册表
            failed_registry = FailedJobRegistry(queue.name, connection=redis_conn)
            failed_job_ids = failed_registry.get_job_ids()
            for failed_job_id in failed_job_ids:
                failed_jobs.append(queue.fetch_job(failed_job_id))

            # 获取成功的Job注册表
            finished_registry = FinishedJobRegistry(queue.name, connection=redis_conn)
            finished_job_ids = finished_registry.get_job_ids()
            for finished_job_id in finished_job_ids:
                failed_jobs.append(queue.fetch_job(finished_job_id))

            # 获取取消的Job注册表
            canceled_registry = CanceledJobRegistry(queue.name, connection=redis_conn)
            canceled_job_ids = canceled_registry.get_job_ids()
            for canceled_job_id in canceled_job_ids:
                failed_jobs.append(queue.fetch_job(canceled_job_id))

        # 等待指定间隔时间
        time.sleep(interval)


def handle_failed_job(failed_job_id, reason=None):
    """
    处理失败的Job，记录日志
    """
    try:
        logger.info(
            f"[handle_failed_job] Job {failed_job_id} failed with exception: {reason}")
        # 更新数据库中的任务状态
        VideoTaskDBService.update_task_status(failed_job_id, 'failed', failed_reason=reason)
    except Exception as e:
        logger.error(f'[handle_failed_job] Exception while handling failed job: {e}')


def handle_finished_job(finished_job_id, result=None):
    """
    处理成功的Job，记录日志
    """
    try:
        user_dict = UserDBService.get_user()
        video_save_path = os.path.join(user_dict['video_save_path'], finished_job_id)
        if not os.path.exists(video_save_path):
            os.makedirs(video_save_path)

        logger.info(f"[handle_success_job] Job {finished_job_id} finished with result: {result}")
        if type(result) is list:
            video_url_or_list = result[0]
            if type(video_url_or_list) is not list:
                video_url_or_list = [video_url_or_list]

            saved_path_list = []
            for video_url in video_url_or_list:
                logger.info(f'[handle_success_job] Video URL: {video_url}')
                saved_path = download_video(video_url, video_save_path, get_filename_from_url(video_url))
                saved_path_list.append(saved_path)
            # 更新数据库中的任务状态
            saved_path_str = ','.join(saved_path_list)
            VideoTaskDBService.update_task_status(finished_job_id, 'finished', video_url=saved_path_str)
        VideoTaskDBService.update_task_status(finished_job_id, 'finished', video_url="")
    except Exception as e:
        logger.error(f'[handle_success_job] Exception while handling success job: {e}')


def handle_canceled_job(canceled_job_id):
    """
    处理取消的Job，记录日志
    """
    try:
        logger.info(f"[handle_canceled_job] Job {canceled_job_id} was canceled.")
        # 更新数据库中的任务状态
        VideoTaskDBService.update_task_status(canceled_job_id, 'canceled')
    except Exception as e:
        logger.error(f'[handle_canceled_job] Exception while handling canceled job: {e}')


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


if __name__ == '__main__':
    print("启动RQ Job监控器，每隔5秒检查一次...")
    monitor_jobs(interval=5)
