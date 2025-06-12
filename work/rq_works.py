from rq import SimpleWorker
from rq.worker_pool import WorkerPool
from controllers.v1.VideoGenerateController import redis_conn
from controllers.v1.VideoGenerateController import generate_videos_queue
import logging
import os


def start_simple_rq_worker(verbose=False):
    """
    Start the RQ worker to process jobs from the 'generate_videos' queue.
    """
    if verbose:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.WARNING
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'rq_worker.log')
    logging.basicConfig(
        filename=log_path,
        level=logging_level,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    worker = SimpleWorker([generate_videos_queue], connection=redis_conn)
    worker.work(logging_level=logging_level)

def start_rq_worker_pool(verbose=False, num_workers=3):
    """
    Start a pool of RQ workers to process jobs from the 'generate_videos' queue.

    :param num_workers: Number of worker threads to start.
    """
    if verbose:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.WARNING

    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'rq_worker.log')
    logging.basicConfig(
        filename=log_path,
        level=logging_level,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    worker_pool = WorkerPool(num_workers =num_workers, queues=[generate_videos_queue], connection=redis_conn)
    worker_pool.start(logging_level=logging_level)