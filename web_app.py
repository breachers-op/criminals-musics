import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pyrogram import Client
from pyrogram.errors import (
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    BadRequest,
)

app = FastAPI(title="Pyrogram Session Generator")

pending_sessions: dict = {}

_HTML = Path("templates/index.html").read_text()


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_HTML)


@app.post("/send-code")
async def send_code(
    api_id: int = Form(...),
    api_hash: str = Form(...),
    phone: str = Form(...),
):
    session_id = str(uuid.uuid4())

    client = Client(
        name=session_id,
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True,
    )

    try:
        await client.connect()
        sent = await client.send_code(phone)
        pending_sessions[session_id] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent.phone_code_hash,
        }
        return JSONResponse({"ok": True, "session_id": session_id})
    except BadRequest as e:
        await client.disconnect()
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except Exception as e:
        await client.disconnect()
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/verify-code")
async def verify_code(
    session_id: str = Form(...),
    code: str = Form(...),
    password: str = Form(""),
):
    data = pending_sessions.get(session_id)
    if not data:
        return JSONResponse(
            {"ok": False, "error": "Session expired or not found. Please start over."},
            status_code=400,
        )

    client: Client = data["client"]
    phone: str = data["phone"]
    phone_code_hash: str = data["phone_code_hash"]

    try:
        await client.sign_in(phone, phone_code_hash, code)
    except SessionPasswordNeeded:
        if not password:
            return JSONResponse(
                {"ok": False, "error": "2FA_REQUIRED"},
                status_code=200,
            )
        try:
            await client.check_password(password)
        except BadRequest as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except PhoneCodeInvalid:
        return JSONResponse(
            {"ok": False, "error": "Invalid OTP. Please try again."},
            status_code=400,
        )
    except PhoneCodeExpired:
        pending_sessions.pop(session_id, None)
        await client.disconnect()
        return JSONResponse(
            {"ok": False, "error": "OTP expired. Please start over."},
            status_code=400,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    try:
        session_string = await client.export_session_string()
        me = await client.get_me()
        name = me.first_name or ""
        if me.last_name:
            name += f" {me.last_name}"
        username = f"@{me.username}" if me.username else ""
    finally:
        pending_sessions.pop(session_id, None)
        await client.disconnect()

    return JSONResponse(
        {
            "ok": True,
            "session_string": session_string,
            "name": name,
            "username": username,
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=False)
