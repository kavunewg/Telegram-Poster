from fastapi import APIRouter, Request, Response

router = APIRouter(prefix="/api/language")


@router.get("/get")
async def get_language(request: Request):
    lang = request.cookies.get("language") or request.cookies.get("lang") or "ru"
    return {"success": True, "language": lang}


@router.post("/toggle")
async def toggle_language(request: Request, response: Response):
    current_lang = request.cookies.get("language") or request.cookies.get("lang") or "ru"
    new_lang = "en" if current_lang == "ru" else "ru"
    response.set_cookie(key="language", value=new_lang)
    response.set_cookie(key="lang", value=new_lang)
    return {"success": True, "language": new_lang}
