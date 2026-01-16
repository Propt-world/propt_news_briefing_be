import json
import redis
import traceback
from datetime import datetime, timedelta, timezone
from pymongo.database import Database
from src.config.settings import settings

def check_briefing_schedules(db: Database, redis_client: redis.Redis):
    """
    Cron-like function that runs every minute.
    - Triggers briefings 30 minutes before the user's scheduled time.
    - Catches up on any missed briefings for the current day.
    """
    try:
        # 1. Setup Time Boundaries
        now_utc = datetime.now(timezone.utc)
        today_str = now_utc.strftime("%Y-%m-%d")
        
        # Lookahead window: Check for anything due between [Beginning of Time] and [Now + 30 mins]
        lookahead_limit = now_utc + timedelta(minutes=30)
        
        # 2. Query MongoDB (Active users who haven't run today)
        collection = db["briefing_schedules"]
        query = {
            "is_active": True,
            "last_run_date": {"$ne": today_str}
        }
        candidates = list(collection.find(query))

        if not candidates:
            return

        # 3. Filter Candidates & Queue
        for schedule in candidates:
            try:
                user_id = schedule["_id"]
                scheduled_time_str = schedule.get("scheduled_time_utc", "08:00")
                
                # Parse the "HH:MM" string
                try:
                    h, m = map(int, scheduled_time_str.split(":"))
                except ValueError:
                    print(f"[SCHEDULER] ⚠️ Invalid time format for user {user_id}: {scheduled_time_str}")
                    continue

                # Create a datetime object for THIS schedule on TODAY'S date
                schedule_dt = now_utc.replace(hour=h, minute=m, second=0, microsecond=0)
                
                # Logic: If schedule is due (or past due), trigger it
                if schedule_dt <= lookahead_limit:
                    
                    # Construct Job ID
                    job_id = f"briefing-{user_id}-{today_str}"
                    
                    # --- FIX: IDEMPOTENCY CHECK ---
                    # Check if this job is already in Redis to prevent duplicates
                    if redis_client.exists(f"job:{job_id}"):
                        continue

                    # --- SUBMIT JOB ---
                    job_payload = {
                        "job_type": "briefing_generation", 
                        "job_id": job_id,
                        "user_id": user_id,
                        "config": {
                            "duration": schedule.get("duration", 5),
                            "voice": schedule.get("voice", "marin"),
                            "language": schedule.get("language", "eng")
                        },
                        "timestamp": str(now_utc.timestamp())
                    }

                    # A. Push to Queue
                    redis_client.lpush(settings.REDIS_QUEUE_NAME, json.dumps(job_payload))
                    
                    # B. Create Status Key
                    redis_client.hset(
                        f"job:{job_id}",
                        mapping={
                            "status": "queued",
                            "type": "briefing",
                            "user_id": user_id,
                            "created_at": str(now_utc)
                        }
                    )
                    redis_client.expire(f"job:{job_id}", 172800) # 48h TTL

                    is_catchup = schedule_dt < now_utc
                    timeliness = "CATCH-UP" if is_catchup else "SCHEDULED"
                    print(f"[SCHEDULER] 🚀 Queued {timeliness} briefing for {user_id} (Due: {scheduled_time_str})")
                    
                    # NOTE: We do NOT update 'last_run_date' here anymore. 
                    # The Worker will do it upon success.

            except Exception as inner_e:
                print(f"[SCHEDULER] ⚠️ Error processing candidate {schedule.get('_id')}: {inner_e}")

    except Exception as e:
        print(f"[SCHEDULER] 💥 Critical Error in briefing cycle: {e}")
        traceback.print_exc()