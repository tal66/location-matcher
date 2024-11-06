import logging
from datetime import datetime, UTC
from typing import List, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from db_ import LOCATIONS_TABLE_NAME, init_db, insert_location_data, USERS_TABLE_NAME, SessionLocal
from sec import create_initial_user, currUserDep, router as sec_router
from psi import router as psi_router

from sample_data import DB_LONDON_VALUES

MAX_NUM_USERS_NEARBY = 20

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s %(levelname)-8s %(module)s:%(funcName)s:%(lineno)d - %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(debug=True)
app.include_router(sec_router)
app.include_router(psi_router)


class LocationUpdate(BaseModel):
    user_id: str
    latitude: float
    longitude: float


@app.get("/users")
def get_all_users():
    with SessionLocal() as session:
        query = text(f"""SELECT user_id, ST_AsText(location) AS point FROM {LOCATIONS_TABLE_NAME};""")
        result = session.execute(query).fetchall()
        users = [{"user_id": row[0], "point": row[1]} for row in result]

    return users


@app.post("/locations", tags=["Locations"])
def update_location(location: LocationUpdate, current_user: currUserDep):
    if location.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    with SessionLocal() as session:
        stmt = text(f"""
        INSERT INTO {LOCATIONS_TABLE_NAME} (user_id, location, last_updated)
        VALUES (:user_id, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326), :timestamp)
        ON CONFLICT (user_id) 
        DO UPDATE SET 
            location = ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
            last_updated = :timestamp
        """)

        session.execute(stmt, {
            'user_id': location.user_id,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'timestamp': datetime.now(UTC)
        })
        session.commit()

        return {"status": "success", "latitude": location.latitude, "longitude": location.longitude}


# TODO: improve
@app.get("/locations/nearby_users", tags=["Locations"])
def get_nearby_users(user_id: str, max_distance: float = 5.0, current_user: currUserDep = None) -> List[
    Dict[str, object]]:
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    with SessionLocal() as session:
        # check exists
        query = text(f"SELECT EXISTS(SELECT 1 FROM {LOCATIONS_TABLE_NAME} WHERE user_id = :user_id)")
        result = session.execute(query, {"user_id": user_id }).scalar()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        query = text(f"""
        SELECT
            other.user_id,
            ST_Distance(other.location::geography, base.location::geography) / 1000 as distance_km,
            ST_X(other.location) as longitude, ST_Y(other.location) as latitude
        FROM 
            {LOCATIONS_TABLE_NAME} AS base
        JOIN 
            {LOCATIONS_TABLE_NAME} AS other ON other.user_id != base.user_id
        WHERE 
            base.user_id = :user_id
            AND ST_DWithin(
                other.location::geography, -- geography cast for accurate distance calculation
                base.location::geography,
                :max_distance * 1000  -- meters
            )
        ORDER BY distance_km
        LIMIT {MAX_NUM_USERS_NEARBY};
        """)

        result = session.execute(query, {
            'user_id': user_id,
            'max_distance': max_distance,
        })

        nearby_users = [
            {
                "user_id": row[0],
                "distance": round(row[1], 2),
                "location": {"latitude": row[3], "longitude": row[2]}
            }
            for row in result
        ]

        return nearby_users


def insert_initial_users():
    # get all usernames, add password to missing users
    sample_user_ids = []
    for line in DB_LONDON_VALUES.strip().splitlines():
        u = line.split(",")[0].strip("'")
        u = u.replace("('", "").strip()
        if u:
            sample_user_ids.append(u)

    log.info(f"insert {sample_user_ids} {len(sample_user_ids)} initial users")
    with SessionLocal() as session:
        q = text(f"""SELECT user_id FROM {USERS_TABLE_NAME};""")
        result = session.execute(q)
        user_ids_with_pw = [row.user_id for row in result]
        for user_id in sample_user_ids:
            if user_id not in user_ids_with_pw:
                create_initial_user(user_id=user_id, password="secret", session=session)
        session.commit()


if __name__ == "__main__":
    init_db()
    insert_initial_users()
    insert_location_data()
    uvicorn.run(app, host="0.0.0.0", port=8000)
