import logging
import os
import time
from datetime import datetime, UTC

from geoalchemy2 import Geometry
from sqlalchemy import create_engine, Column, String, DateTime, text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

from sample_data import DB_LONDON_VALUES

logging.basicConfig(level=logging.INFO,
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
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

LOCATIONS_TABLE_NAME = "user_locations"
USERS_TABLE_NAME = "users"


class UserDB(Base):
    __tablename__ = USERS_TABLE_NAME

    user_id = Column(String, primary_key=True, index=True)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)


class UserLocation(Base):
    __tablename__ = LOCATIONS_TABLE_NAME

    user_id = Column(String, ForeignKey(f"{USERS_TABLE_NAME}.user_id"), primary_key=True, index=True, )
    location = Column(Geometry('POINT', srid=4326))
    last_updated = Column(DateTime, default=datetime.now(UTC))


def _init_postgis():
    """initialize PostGIS extension before creating tables"""
    num_attempts = 3
    sleep_time = 3
    for i in range(num_attempts):
        try:
            with engine.connect() as conn:
                log.info("initialize PostGIS extension")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                conn.commit()
                break
        except Exception as e:
            if i == num_attempts - 1:
                log.error(f"Error initializing PostGIS: {e}")
                raise e
            else:
                log.info(f"sleep {sleep_time}s before retry db engine.connect()")
                time.sleep(sleep_time)


def init_db():
    """create all tables (will not attempt to recreate tables already present)"""
    _init_postgis()
    log.info("create tables")
    Base.metadata.create_all(bind=engine)
    _create_spatial_indexes()


def _create_spatial_indexes():
    """Create optimized spatial indexes"""
    with engine.connect() as conn:
        conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS idx_{LOCATIONS_TABLE_NAME}_geometry 
        ON {LOCATIONS_TABLE_NAME} USING GIST (location);
        """))
        conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS idx_{LOCATIONS_TABLE_NAME}_geography 
        ON {LOCATIONS_TABLE_NAME} USING GIST ((location::geography));
        """))

        conn.commit()


def insert_location_data():
    """Insert sample data"""
    log.info("inserting sample data (London)")
    with SessionLocal() as session:
        # insert or update location data
        q = text(f""" INSERT INTO {LOCATIONS_TABLE_NAME} (user_id, location, last_updated) 
                    VALUES {DB_LONDON_VALUES}
                    ON CONFLICT (user_id)
                    DO UPDATE SET 
                        location = EXCLUDED.location,
                        last_updated = EXCLUDED.last_updated;
                """)
        session.execute(q)
        session.commit()
