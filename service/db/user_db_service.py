from utils.sqlite_manager import SQLAlchemyManager
from models.db.user import User

class UserDBService:
    @classmethod
    def get_user(cls):
        db_manager = SQLAlchemyManager()
        session = db_manager.get_session()
        user = session.query(User).first()
        session.close()
        return user

    @classmethod
    def update_user(cls, username, password, user_type):
        db_manager = SQLAlchemyManager()
        session = db_manager.get_session()
        user = session.query(User).first()
        if user:
            user.username = username
            user.password = password
            user.user_type = user_type
            session.commit()
        else:
            new_user = User(username=username, password=password, user_type=user_type)
            session.add(new_user)
            session.commit()
        session.close()
    @classmethod
    def update_token_and_video_path(cls, token, video_path):
        db_manager = SQLAlchemyManager()
        session = db_manager.get_session()
        user = session.query(User).first()
        if user:
            user.token = token
            user.video_save_path = video_path
            session.commit()


