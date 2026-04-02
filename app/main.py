from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api.auth import router as auth_router
from app.api.surveys import router as survey_router
from app.api.answers import router as answer_router
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    await connect_to_mongo()
    yield
    # Shutdown: Close MongoDB connection
    await close_mongo_connection()

app = FastAPI(title="Survey System API", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(survey_router, prefix="/api/v1")
app.include_router(answer_router, prefix="/api/v1")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/editor/{survey_id}", response_class=HTMLResponse)
async def editor_page(request: Request, survey_id: str):
    return templates.TemplateResponse(request=request, name="editor.html", context={"survey_id": survey_id})

@app.get("/survey/{survey_id}", response_class=HTMLResponse)
async def survey_fill_page(request: Request, survey_id: str):
    return templates.TemplateResponse(request=request, name="survey_fill.html", context={"survey_id": survey_id})

@app.get("/health")
async def health():
    return {"status": "ok"}
