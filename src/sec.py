"""
based on fastapi docs https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt but with db
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from db_ import engine, UserDB


@dataclass
class SolveBugBcryptWarning:
    # https://github.com/pyca/bcrypt/issues/684
    __version__: str = getattr(bcrypt, "__version__")


setattr(bcrypt, "__about__", SolveBugBcryptWarning())

# get rand string: openssl rand -hex 32
SECRET_KEY = "33e07a088f7151c808c149eb2485191d138a56983730487d13d93acfdc276804"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login_for_access_token")


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(user_id: str):
    with SessionLocal() as session:
        user = session.query(UserDB).filter(UserDB.user_id == user_id).first()
        return user



def authenticate_user(user_id: str, password: str):
    def verify_password(plain_password, hashed_password):
        """verify if a received password matches the hash stored"""
        return pwd_context.verify(plain_password, hashed_password)

    user = get_user(user_id)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # default expire time
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """retrieves user from JWT token.
    FastAPI will automatically extract the token from the request using the oauth2_scheme dependency,
    which looks for the token in the Authorization header."""

    # handle cases where the token is invalid or user cannot be authenticated
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # user from jwt
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # decode token, using secret key

        username: str = payload.get("sub")  # sub is the subject of the token, in this case the user's username
        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception

    # user from db
    user = get_user(user_id=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)], ):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user


############################

# User model with a dependency on a function:
# When a route handler includes currUserDep as a parameter,
# FastAPI will automatically call get_current_active_user
# to retrieve the current active user and pass it to the route handler.
currUserDep = Annotated[User, Depends(get_current_active_user)]


@router.post("/login_for_access_token", response_model=Token)  # path same as tokenUrl in OAuth2PasswordBearer
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:

    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.user_id}, expires_delta=access_token_expires)

    return Token(access_token=access_token, token_type="bearer")


@router.get("/users/me/")
async def read_users_me(current_user: currUserDep):
    return {"user_id": current_user.user_id, "disabled": current_user.disabled}


#############
def create_initial_user(user_id: str, password: str):
    hashed_password = get_password_hash(password)

    user_data = {
        "user_id": user_id,
        "hashed_password": hashed_password,
        "disabled": False
    }

    stmt = insert(UserDB).values(**user_data).on_conflict_do_update(
        index_elements=["user_id"],
        set_={"hashed_password": hashed_password, "disabled": False}
    )
    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()

        # return session.query(UserDB).filter_by(user_id=user_id).first()
