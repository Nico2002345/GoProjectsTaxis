from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import auth, drivers, trips, ws

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="TaxisMitu")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(auth.router)
app.include_router(drivers.router)
app.include_router(trips.router)
app.include_router(ws.router)


@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/verify")
def verify_page(request: Request):
    return templates.TemplateResponse(request, "verify.html")


@app.get("/terms")
def terms_page(request: Request):
    return templates.TemplateResponse(request, "terms.html")


@app.get("/passenger")
def passenger_page(request: Request):
    return templates.TemplateResponse(request, "passenger.html")


@app.get("/driver")
def driver_page(request: Request):
    return templates.TemplateResponse(request, "driver.html")


@app.get("/health")
def health():
    return {"status": "ok"}
