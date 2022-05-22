from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2, OAuth2PasswordRequestForm

from typing import Optional

from jose import JWTError, jwt
from datetime import datetime, timedelta

from ..users import create_user, User
from ..common import DefaultResponse, DefaultResponseStatus

from ..utils.auth import OAuth2PasswordBearerWithCookie

from .. import config_options

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config_options.SECRET_KEY, algorithm=config_options.JWT_ALGORITHMS[0])
    return encoded_jwt

def get_user_from_username(username : str):
    return User(
                username = username,
                index_name = config_options.ELASTICSEARCH_USER_INDEX,
                es_conn = config_options.es_conn 
           )

async def get_user_from_token(token : str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, config_options.SECRET_KEY, algorithms=config_options.JWT_ALGORITHMS)
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user : User = get_user_from_username(username = username)

    if not user.user_exist():
        raise credentials_exception

    return user

@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_user_from_token)):
    response.delete_cookie(key="access_token")
    return

@router.post("/login")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    current_user = get_user_from_username(form_data.username)
    if not current_user.user_exist():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with that username wasn't found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    elif not current_user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=config_options.ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )

    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, samesite="strict")

    return #{"access_token": access_token, "token_type": "bearer"}

@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model = DefaultResponse)
async def signup(form_data: OAuth2PasswordRequestForm = Depends()):
    current_user = get_user_from_username(form_data.username)
    if create_user(current_user, form_data.password):
        return DefaultResponse(status = DefaultResponseStatus.SUCCESS, msg = "User created")
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with that username already exists"
        )
