
from models.db.users import Users
from models.db.database_base import session_local

class UserDBService:
    @staticmethod
    def get_user_by_id(user_id: int):
        with session_local() as session:
            return session.query(Users).filter_by(id=user_id).first()

    @staticmethod
    def get_user_by_name(user_name: str):
        with session_local() as session:
            return session.query(Users).filter_by(username=user_name).first()

    @staticmethod
    def update_user(user_id: int, **kwargs):
        with session_local() as session:
            user = session.query(Users).filter_by(id=user_id).first()
            if not user:
                return None
            for key, value in kwargs.items():
                setattr(user, key, value)
            session.commit()
            return user

    @staticmethod
    def create_user(**kwargs):
        with session_local() as session:
            user = Users(**kwargs)
            session.add(user)
            session.commit()
            return user