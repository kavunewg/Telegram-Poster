from fastapi.responses import RedirectResponse, JSONResponse


def redirect(url: str):
    return RedirectResponse(url=url, status_code=303)


def error_json(message: str, code: int = 400):
    return JSONResponse({"error": message}, status_code=code)