from utils.sqlite_manager import SQLAlchemyManager
from models.db.video_task_excutions import VideoTaskExecution
from loguru import logger
import uuid

class VideoTaskDBService:
    @classmethod
    def query_all_task(cls):
        session = SQLAlchemyManager().get_session()
        try:
            tasks = session.query(VideoTaskExecution).order_by(VideoTaskExecution.created_at.desc()).all()
            return [task.to_dict() for task in tasks]
        except Exception as e:
            logger.exception(f"查询所有任务失败: {e}")
            return []
        finally:
            session.close()
    @classmethod
    def update_task_status(cls, task_id, status, video_url=None):
        session = SQLAlchemyManager().get_session()
        try:
            task = session.query(VideoTaskExecution).filter_by(task_id=task_id).first()
            if not task:
                return False, '任务不存在'
            task.task_status = status
            if video_url:
                task.video_url = video_url
            session.commit()
            return True, task
        except Exception as e:
            session.rollback()
            logger.exception(f"更新任务状态失败: {e}")
            return False, None
        finally:
            session.close()

    @classmethod
    def add_task(cls, prompt, model, ratio, duration, video_nums):
        session = SQLAlchemyManager().get_session()
        try:
            task = VideoTaskExecution(
                task_id=str(uuid.uuid4()),
                prompt=prompt,
                model=model,
                ratio=ratio,
                video_duration=duration,
                video_nums=video_nums,
                task_status='pending',
                video_url=''
            )
            session.add(task)
            session.commit()
            return True, None
        except Exception as e:
            session.rollback()
            logger.exception(f"添加任务失败: {e}")
            return False, str(e)
        finally:
            session.close()

    @classmethod
    def get_task_by_id(cls, task_id):
        session = SQLAlchemyManager().get_session()
        try:
            task = session.query(VideoTaskExecution).filter_by(task_id=task_id).first()
            return task, session
        except Exception as e:
            session.close()
            logger.exception(f"根据ID获取任务失败: {e}")
            return None, None

    @classmethod
    def delete_task_by_id(cls, task_id):
        session = SQLAlchemyManager().get_session()
        try:
            task = session.query(VideoTaskExecution).filter_by(task_id=task_id).first()
            if task:
                session.delete(task)
                session.commit()
                return True, None
            else:
                logger.warning(f"删除任务失败，任务不存在: {task_id}")
                return False, '任务不存在'
        except Exception as e:
            session.rollback()
            logger.exception(f"删除任务失败: {e}")
            return False, str(e)
        finally:
            session.close()
