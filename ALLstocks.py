import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from dotenv import load_dotenv, set_key
from kiteconnect import KiteConnect

load_dotenv()

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
ENV_PATH = ".env"

app = FastAPI()
kite = KiteConnect(api_key=API_KEY)


@app.get("/login")
def login():
    """Redirects you to Zerodha's official login page."""
    return RedirectResponse(url=kite.login_url())


@app.get("/callback")
def callback(request: Request):
    """Captures request_token after login and saves daily access_token to .env."""
    request_token = request.query_params.get("request_token")
    status = request.query_params.get("status")

    if status != "success" or not request_token:
        return HTMLResponse("<h3>Login failed or cancelled.</h3>", status_code=400)

    try:
        # Exchange request_token + API secret for the daily access_token
        session_data = kite.generate_session(request_token, api_secret=API_SECRET)
        access_token = session_data["access_token"]

        # Automatically update KITE_ACCESS_TOKEN inside .env
        set_key(ENV_PATH, "KITE_ACCESS_TOKEN", access_token)

        return HTMLResponse(
            "<h3>Success! Daily Zerodha access_token updated in .env.</h3>"
            "<p>Your market scanner is ready for today's session.</p>"
        )
    except Exception as e:
        return HTMLResponse(f"<h3>Token exchange failed: {e}</h3>", status_code=500)
