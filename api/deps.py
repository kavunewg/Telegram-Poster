from fastapi import Request, HTTPException
from repositories.user_repo import user_repo


def get_current_user(request: Request):
    user = getattr(request.state, "user", None)

    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return user


def get_admin_user(request: Request):
    user = get_current_user(request)

    if user.get("is_admin") != 1:
        raise HTTPException(status_code=403, detail="Forbidden")

    return user