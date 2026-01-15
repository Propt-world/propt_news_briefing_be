import redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pymongo import MongoClient

from src.config.settings import settings
from src.scheduler.briefing_scheduler import check_briefing_schedules
from src.models.BriefingScheduleRequest import BriefingScheduleRequest
from src.models.UserBriefingSchedule import UserBriefingSchedule
from src.models.Responses import GenericResponse, SchedulerHealthResponse

# --- Infrastructure ---
client = MongoClient(settings.DATABASE_URL)
db = client[settings.MONGO_DB_NAME]
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
scheduler = AsyncIOScheduler()

# --- Job Wrapper ---
async def run_briefing_cycle():
    """
    Checks for due briefings every minute.
    """
    check_briefing_schedules(db, redis_client)

# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register the briefing job (Runs every 1 minute)
    scheduler.add_job(run_briefing_cycle, IntervalTrigger(minutes=1))
    scheduler.start()
    
    print("--- 🗓️ NewsCast Scheduler Started ---")
    yield
    scheduler.shutdown()

app = FastAPI(title="NewsCast Scheduler", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.post(
    "/schedules/briefing",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse,
    tags=["Schedules"]
)
async def upsert_briefing_schedule(request: BriefingScheduleRequest):
    """
    Create or Update a user's Daily Briefing Schedule.
    """
    collection = db["briefing_schedules"]
    
    schedule_entry = UserBriefingSchedule(
        id=request.user_id,
        duration=request.duration,
        is_active=request.enable_daily_briefing,
        voice=request.voice,
        scheduled_time_utc=request.time,
        language=request.language
    )
    
    result = collection.update_one(
        {"_id": request.user_id},
        {"$set": schedule_entry.dict(by_alias=True, exclude={"id", "last_run_date"})},
        upsert=True
    )
    
    action = "Created" if result.upserted_id else "Updated"
    return {
        "status": "success", 
        "message": f"Schedule {action} for user {request.user_id}"
    }

@app.get("/health", response_model=SchedulerHealthResponse)
async def health_check():
    # Basic connectivity check
    db_status = "connected"
    try:
        client.admin.command('ping')
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "scheduler": "running" if scheduler.running else "stopped",
        "browserless": "N/A", # Not used in this service
        "main_api": "N/A",
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    uvicorn.run(app, host="0.0.0.0", port=8001)