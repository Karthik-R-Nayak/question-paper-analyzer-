from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import UserAccount, UserSession
from app.schemas import Credentials, UserRead
from app.security import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    create_session,
    hash_password,
    hash_session_token,
    require_user,
    set_session_cookie,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: Credentials,
    response: Response,
    session: Session = Depends(get_session),
) -> UserAccount:
    username = payload.username.lower()
    try:
        with session.begin():
            if session.scalar(
                select(UserAccount.user_id).where(UserAccount.username == username)
            ) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username is already registered.",
                )
            user = UserAccount(
                username=username,
                password_hash=hash_password(payload.password),
            )
            session.add(user)
            session.flush()
            token = create_session(session, user)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered.",
        ) from exc

    set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserRead)
def login(
    payload: Credentials,
    response: Response,
    session: Session = Depends(get_session),
) -> UserAccount:
    with session.begin():
        user = session.scalar(
            select(UserAccount).where(UserAccount.username == payload.username.lower())
        )
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )
        token = create_session(session, user)
    set_session_cookie(response, token)
    return user


@router.get("/me", response_model=UserRead)
def current_user(
    user: UserAccount = Depends(require_user),
) -> UserAccount:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> Response:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        with session.begin():
            active_session = session.scalar(
                select(UserSession).where(
                    UserSession.token_hash == hash_session_token(token)
                )
            )
            if active_session is not None:
                session.delete(active_session)
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
