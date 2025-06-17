from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import config

SQLALCHEMY_DATABASE_URL = config.mysql_connection_string

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_recycle=3600
)

session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()