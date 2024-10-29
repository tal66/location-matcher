import logging
import os
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import create_engine, Column, String, DateTime, text, Boolean
from sqlalchemy.orm import declarative_base


logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s %(levelname)-8s %(module)s:%(funcName)s:%(lineno)d - %(message)s")
log = logging.getLogger(__name__)

# db config
DATABASE_URL = os.getenv("DATABASE_URL", None)
if not DATABASE_URL:  # local
    user = "postgres"
    password = "postgres"
    db = "postgres"
    DATABASE_URL = f"postgresql+psycopg://{user}:{password}@localhost:5432/{db}"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

LOCATIONS_TABLE_NAME = "user_locations"
USERS_TABLE_NAME = "users"

class UserLocation(Base):
    __tablename__ = LOCATIONS_TABLE_NAME

    user_id = Column(String, primary_key=True)
    location = Column(Geometry('POINT', srid=4326))
    last_updated = Column(DateTime, default=datetime.utcnow)


class UserInfo(Base):
    __tablename__ = USERS_TABLE_NAME

    user_id = Column(String, primary_key=True)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)


def init_postgis():
    """initialize PostGIS extension before creating tables"""
    with engine.connect() as conn:
        log.info("initialize PostGIS extension")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()


def init_db():
    """create all tables (will not attempt to recreate tables already present)"""
    log.info("create tables")
    Base.metadata.create_all(bind=engine)