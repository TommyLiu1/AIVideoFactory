from models.db.user_settings import UserSettings
from models.db.database_base import session_local

class UserSettingsDBService:
    @staticmethod
    def create_user_settings(user_id: int, token: str, save_video_path: str = None) -> UserSettings:
        with session_local as session:
            settings = UserSettings(
                user_id=user_id,
                token=token,
                save_video_path=save_video_path
            )
            session.add(settings)
            session.commit()
            return settings

    @staticmethod
    def get_user_settings(user_id: int) -> UserSettings | None:
        with session_local as session:
            return session.query(UserSettings).filter_by(user_id=user_id).first()

    @staticmethod
    def update_user_settings(user_id: int, token: str = None, save_video_path: str = None) -> UserSettings | None:
        with session_local as session:
            settings = session.query(UserSettings).filter_by(user_id=user_id).first()
            if not settings:
                return None
            if token:
                settings.token = token
            if save_video_path:
                settings.save_video_path = save_video_path
            session.commit()
            return settings