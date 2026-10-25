"""FastAPI web server.  Run:  uvicorn main:app --reload   then open http://127.0.0.1:8000

All logic lives in citypulse/service.py; this file only maps HTTP routes to those functions.
Interactive API docs (free, automatic): http://127.0.0.1:8000/docs
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from citypulse import config, service

app = FastAPI(title="CityPulse", description="Agentic AI: urban exposure -> healthier next-week actions", version="1.0.0")
STATIC = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


class PlanRequest(BaseModel):
    persona: str = "office"
    city: str = config.DEFAULT_CITY
    lang: str = "en"
    use_live: bool = True
    use_llm: bool = False
    workouts: int = config.DEFAULT_WORKOUTS
    user_id: str | None = None


class FeedbackRequest(BaseModel):
    user_id: str
    item_id: str
    accepted: bool


class ChatRequest(BaseModel):
    message: str
    lang: str = "en"
    user_id: str | None = None


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/api/options")
def get_options():
    return service.options()


@app.post("/api/plan")
def post_plan(req: PlanRequest):
    try:
        return service.make_plan(req.persona, req.city, req.lang, req.use_live, req.user_id,
                                 use_llm=req.use_llm, workouts=req.workouts)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/api/feedback")
def post_feedback(req: FeedbackRequest):
    return service.feedback(req.user_id, req.item_id, req.accepted)


@app.post("/api/chat")
def post_chat(req: ChatRequest):
    return service.chat(req.message, req.lang, req.user_id)


@app.get("/api/calendar/{user_id}.ics")
def get_calendar(user_id: str):
    path = service.ics_path(user_id)
    if not path:
        raise HTTPException(status_code=404, detail="No calendar yet - generate a plan first.")
    return FileResponse(path, media_type="text/calendar", filename="citypulse_plan.ics")
