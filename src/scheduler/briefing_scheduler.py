import json
import redis
import traceback
from datetime import datetime, timedelta, timezone
from pymongo.database import Database
from src.config.settings import settings

def check_briefing_schedules(db: Database, redis_client: redis.Redis):
    """
    Cron-like function that runs every minute.
    Triggers audio briefings 30 minutes before the user's scheduled time.
    """
    try:
        # 1. Calculate the target time window (Now + 30 mins)
        # We work in UTC to maintain consistency across timezones
        now_utc = datetime.now(timezone.utc)
        target_time = now_utc + timedelta(minutes=30)
        
        # Format: "08:30" (Matches the regex in your API model)
        target_time_str = target_time.strftime("%H:%M")
        
        # Format: "2024-01-15" (Used as a key to prevent double-runs today)
        today_str = now_utc.strftime("%Y-%m-%d")

        # 2. Query MongoDB for matching schedules
        # Criteria: Active, Scheduled for this minute, Has NOT run today
        collection = db["briefing_schedules"]
        query = {
            "is_active": True,
            "scheduled_time_utc": target_time_str,
            "last_run_date": {"$ne": today_str}
        }

        due_schedules = list(collection.find(query))

        if not due_schedules:
            # Silence is golden; avoid log spam if nothing is due
            return

        print(f"[SCHEDULER] ⏰ Found {len(due_schedules)} briefings scheduled for {target_time_str} UTC.")

        # 3. Submit Jobs to Redis
        for schedule in due_schedules:
            user_id = schedule["_id"]
            
            # Construct the Job Payload
            # This 'job_type' tells the Worker to use the Audio Graph, not the Scraping Graph
            job_payload = {
                "job_type": "briefing_generation", 
                "job_id": f"briefing-{user_id}-{today_str}",
                "user_id": user_id,
                "config": {
                    "duration": schedule.get("duration", 5),
                    "voice": schedule.get("voice", "marin"),
                    "language": schedule.get("language", "eng")
                },
                "timestamp": str(now_utc.timestamp())
            }

            try:
                # A. Push to Redis Queue
                redis_client.lpush(settings.REDIS_QUEUE_NAME, json.dumps(job_payload))
                
                # B. Create Status Key (for visibility/debugging)
                redis_client.hset(
                    f"job:{job_payload['job_id']}",
                    mapping={
                        "status": "queued",
                        "type": "briefing",
                        "user_id": user_id,
                        "created_at": str(now_utc)
                    }
                )
                # Expire status key after 48 hours to save RAM
                redis_client.expire(f"job:{job_payload['job_id']}", 172800)

                # C. Update DB (Mark as run for today)
                collection.update_one(
                    {"_id": user_id},
                    {"$set": {"last_run_date": today_str}}
                )
                
                print(f"[SCHEDULER] 🚀 Queued Briefing for User: {user_id}")

            except Exception as e:
                print(f"[SCHEDULER] ❌ Error submitting job for {user_id}: {e}")
                traceback.print_exc()

    except Exception as e:
        print(f"[SCHEDULER] 💥 Critical Error in briefing cycle: {e}")
        traceback.print_exc()