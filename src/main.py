import logging
import uuid
from datetime import datetime
from typing import List, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from db_ import engine, LOCATIONS_TABLE_NAME, init_postgis, init_db, create_spatial_indexes, insert_location_data, \
    USERS_TABLE_NAME
from sec import create_initial_user, currUserDep, router as sec_router

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s %(levelname)-8s %(module)s:%(funcName)s:%(lineno)d - %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(debug=True)
app.include_router(sec_router)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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


@app.post("/locations")
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
            'timestamp': datetime.utcnow()
        })
        session.commit()

        return {"status": "success", "latitude": location.latitude, "longitude": location.longitude}


@app.get("/locations/nearby_users")
def get_nearby_users(user_id: str, max_distance: float = 6.0, current_user: currUserDep = None) -> List[
    Dict[str, object]]:
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    with SessionLocal() as session:
        # check exists
        query = text(f"SELECT EXISTS(SELECT 1 FROM {LOCATIONS_TABLE_NAME} WHERE user_id = :user_id)")
        result = session.execute(query, {"user_id": user_id}).scalar()  # Use scalar to get a single value
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        query = text(f"""
        SELECT 
            other.user_id,
            ST_Distance(other.location::geography, base.location::geography) / 1000 as distance_km
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
        ORDER BY distance_km;
        """)

        result = session.execute(query, {
            'user_id': user_id,
            'max_distance': max_distance
        })

        nearby_users = [
            {
                "user_id": row[0],
                "distance": round(row[1], 2)
            }
            for row in result
        ]

        return nearby_users


########### psi

# in-memory storage for session messages
user_sessions: Dict[str, Dict] = {}


class InitiateRequest(BaseModel):
    blinded_values: List[int]
    user_id: str


class JoinRequest(BaseModel):
    session_id: str
    response_values: List[int]
    user_id: str


class IntersectionUpdateRequest(BaseModel):
    user_id: str
    other_user_id: str
    len_intersection: int


@app.post("/psi/init", status_code=201)
async def initiate_psi(request: InitiateRequest):
    """store initiator's blinded values and create session."""
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = {
        "initiator_values": request.blinded_values,
        "status": 1,
        "user_id": request.user_id
    }
    return {"session_id": session_id}


@app.post("/psi/{session_id}/join")
async def join_psi(session_id: str, request: JoinRequest):
    """store joiner's response values and update session status."""
    session = user_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != 1:
        raise HTTPException(status_code=400, detail="Invalid session status")

    if not session.get("response_values"):
        session["response_values"] = dict()
    session["response_values"][request.user_id] = request.response_values

    session["status"] = 2

    return {"status": "join successful", "session_id": session_id}


@app.get("/psi/{session_id}")
async def get_values(session_id: str):
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = user_sessions[session_id]

    if session["status"] == 1:
        return {"values": session["initiator_values"], "status": 1}
    elif session["status"] == 2:
        return {"values": session["response_values"], "status": 2}

    raise HTTPException(status_code=400, detail="Invalid session status")


@app.patch("/psi/{session_id}/intersection")
async def update_intersection_result(session_id: str, request: IntersectionUpdateRequest):
    """update the number of intersections with other user"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = user_sessions[session_id]

    if session["status"] != 2:
        raise HTTPException(status_code=400, detail="Invalid session status")

    if not session.get("intersection"):
        session["intersection"] = dict()
    session["intersection"][request.other_user_id] = request.len_intersection

    return {"status": f"Intersection updated to {request.len_intersection}"}


###########


if __name__ == "__main__":
    init_postgis()
    init_db()
    create_spatial_indexes()
    insert_location_data()

    # get all usernames, add password to missing users
    with SessionLocal() as session:
        q = text(f"""SELECT user_id FROM {LOCATIONS_TABLE_NAME};""")
        result = session.execute(q)
        user_ids = [row.user_id for row in result]
        q = text(f"""SELECT user_id FROM {USERS_TABLE_NAME};""")
        result = session.execute(q)
        user_ids_with_pw = [row.user_id for row in result]
        for user_id in user_ids:
            if user_id not in user_ids_with_pw:
                create_initial_user(user_id=user_id, password="secret")
        # session.commit()

    uvicorn.run(app, host="0.0.0.0", port=8000)
