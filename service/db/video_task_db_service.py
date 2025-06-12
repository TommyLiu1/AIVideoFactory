from utils.sqlite_manager import SQLAlchemyManager
from models.db.video_task_excutions import VideoTaskExecution
import uuid

class VideoTaskDBService:
    @classmethod
    def query_all_task(cls):
        session = SQLAlchemyManager().get_session()
        try:
            tasks = session.query(VideoTaskExecution).order_by(VideoTaskExecution.created_at.desc()).all()
            return [task.to_dict() for task in tasks]
        except Exception as e:
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
            return True, None
        except Exception as e:
            session.rollback()
            return False, str(e)
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
                video_nums=1,
                task_status='pending',
                video_url=''
            )
            session.add(task)
            session.commit()
            return True, None
        except Exception as e:
            session.rollback()
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
                return False, '任务不存在'
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()
