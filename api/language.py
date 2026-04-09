from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/language")

@router.get("/get")
async def get_language(request: Request):
    lang = request.cookies.get("lang", "ru")
    return {"language": lang}

from fastapi import APIRouter, Request, Response


@router.get("/get")
async def get_language(request: Request):
    lang = request.cookies.get("lang", "ru")
    return {"success": True, "language": lang}


@router.post("/toggle")
async def toggle_language(request: Request, response: Response):
    current_lang = request.cookies.get("lang", "ru")

    new_lang = "en" if current_lang == "ru" else "ru"

    response.set_cookie(key="lang", value=new_lang)

    return {"success": True, "language": new_lang}