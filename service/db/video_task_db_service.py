from models.db.video_task_excutions import VideoTaskExecution
from loguru import logger
from models.db.database_base import session_local
from utils import utils


class VideoTaskDBService:
    @staticmethod
    def create_video_task_execution(
        user_id: int,
        prompt: str,
        model: str,
        model_supply: str,
        ratio: str,
        video_duration: int,
        video_nums: int,
        task_status: str,
        video_url: str = None,
        failed_reason: str = None
    ) -> VideoTaskExecution | None:
        """
        创建视频任务执行记录
        """
        try:
            execution = VideoTaskExecution(
                task_id=str(utils.get_uuid()),
                user_id=user_id,
                prompt=prompt,
                model=model,
                model_supply=model_supply,
                ratio=ratio,
                video_duration=video_duration,
                video_nums=video_nums,
                task_status=task_status,
                video_url=video_url,
                failed_reason=failed_reason
            )
            with session_local() as session:
                session.add(execution)
                session.commit()
                session.refresh(execution)
                logger.info(f"创建视频任务执行记录成功: task_id={execution.task_id}, user_id={user_id}, model={model}, status={task_status}")
                return execution
        except Exception as e:
            logger.error(f"创建视频任务执行记录失败: {e}")
        return None

    @staticmethod
    def get_video_task_execution_by_task_id(task_id: str) -> VideoTaskExecution | None:
        """
        根据任务ID获取视频任务执行记录
        """
        try:
            with session_local() as session:
                execution = session.query(VideoTaskExecution).filter_by(task_id=task_id).first()
                if execution:
                    logger.info(f"获取视频任务执行记录成功: task_id={task_id}")
                else:
                    logger.warning(f"未找到视频任务执行记录: task_id={task_id}")
                return execution
        except Exception as e:
            logger.error(f"获取视频任务执行记录失败: {e}")
        return None

    @staticmethod
    def update_video_task_execution(
        task_id: str,
        **kwargs
    ) -> VideoTaskExecution | None:
        """
        更新视频任务执行记录
        """
        try:
            with session_local() as session:
                execution = session.query(VideoTaskExecution).filter_by(task_id=task_id).first()
                if not execution:
                    logger.warning(f"未找到视频任务执行记录: task_id={task_id}")
                    return None
                for key, value in kwargs.items():
                    setattr(execution, key, value)
                session.commit()
                session.refresh(execution)
                logger.info(f"更新视频任务执行记录成功: task_id={task_id}, updated_fields={kwargs}")
                return execution
        except Exception as e:
            logger.error(f"更新视频任务执行记录失败: {e}")
        return None

    @staticmethod
    def get_video_task_executions_by_user_id(user_id: int) -> list[VideoTaskExecution]:
        """
        根据用户ID获取所有视频任务执行记录
        """
        try:
            with session_local() as session:
                executions = session.query(VideoTaskExecution).filter_by(user_id=user_id).all()
                logger.info(f"获取用户{user_id}的视频任务执行记录成功, count={len(executions)}")
                return executions
        except Exception as e:
            logger.error(f"获取用户{user_id}的视频任务执行记录失败: {e}")
        return []

    @staticmethod
    def delete_video_task_execution(user_id:int, task_id: str) -> bool:
        """
        删除视频任务执行记录
        """
        try:
            with session_local() as session:
                execution = session.query(VideoTaskExecution).filter_by(task_id=task_id, user_id=user_id).first()
                if not execution:
                    logger.warning(f"未找到视频任务执行记录: task_id={task_id}")
                    return False
                session.delete(execution)
                session.commit()
                logger.info(f"删除视频任务执行记录成功: task_id={task_id}")
                return True
        except Exception as e:
            logger.error(f"删除视频任务执行记录失败: {e}")
        return False

    @staticmethod
    def batch_delete_video_task_executions(user_id: str, task_ids: list[str]) -> bool:
        """
        批量删除视频任务执行记录
        """
        try:
            with session_local() as session:
                executions = session.query(VideoTaskExecution).filter(
                    VideoTaskExecution.task_id.in_(task_ids),
                    VideoTaskExecution.user_id == user_id
                ).all()
                if not executions:
                    logger.warning(f"未找到视频任务执行记录: task_ids={task_ids}")
                    return False
                for execution in executions:
                    session.delete(execution)
                session.commit()
                logger.info(f"批量删除视频任务执行记录成功: task_ids={task_ids}")
                return True
        except Exception as e:
            logger.error(f"批量删除视频任务执行记录失败: {e}")
        return False
