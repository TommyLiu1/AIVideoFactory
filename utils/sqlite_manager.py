from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models.db.user import User, user_table_base
from models.db.video_task_excutions import task_base


class SQLAlchemyManager:
    _instance = None
    _engine = None
    _Session = None
    _db_path = None

    def __new__(cls, db_path='app_data.db'):
        if cls._instance is None or (db_path and db_path != cls._db_path):
            cls._instance = super(SQLAlchemyManager, cls).__new__(cls)
            cls._db_path = db_path
            cls._instance._engine = None
            cls._instance._Session = None
            cls._instance.initialize_db()
        return cls._instance

    def initialize_db(self):
        """初始化SQLAlchemy引擎和数据表"""
        if self._engine is None:
            try:
                db_url = f'sqlite:///{self._db_path}'
                self._engine = create_engine(db_url, echo=False)
                user_table_base.metadata.create_all(self._engine)
                task_base.metadata.create_all(self._engine)
                logger.info(f"Database engine created and tables initialized: {self._db_path}")
                self._Session = sessionmaker(bind=self._engine)
                self._add_default_user()
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemy initialization error: {e}")
                self._engine = None

    def _add_default_user(self):
        """Adds a default admin user if the users table is empty."""
        session = self.get_session()
        try:
            if session.query(User).count() == 0:
                admin_user = User(username='admin', password='password123', user_type=0)
                session.add(admin_user)
                session.commit()
                logger.info("Default user 'admin' added to database.")
            else:
                logger.info("Users table already contains data. Skipping default user creation.")
        except SQLAlchemyError as e:
            session.rollback()
            logger.info(f"Error adding default user: {e}")
        finally:
            session.close()

    def get_session(self):
        """Returns a new SQLAlchemy session."""
        if self._Session is None:
            raise RuntimeError("Database engine not initialized. Call initialize_db first.")
        return self._Session()



