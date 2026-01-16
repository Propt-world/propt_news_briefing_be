import json
import asyncio
import redis.asyncio as redis
import traceback
from pprint import pprint
from pymongo import MongoClient

from src.config.settings import settings
from src.graph.graph import BriefingWorkflow
from src.models.BriefingState import BriefingState
from src.utils.email_utils import send_error_email

async def update_job_status(r, job_id, status, result=None, error=None):
    """
    Updates the job status in Redis for observability.
    """
    try:
        mapping = {"status": status}
        if result:
            mapping["result"] = json.dumps(result)
        if error:
            mapping["error"] = str(error)

        await r.hset(f"job:{job_id}", mapping=mapping)
        pprint(f"[REDIS] Job {job_id} -> {status}")
    except Exception as e:
        print(f"[ERROR] Failed to update Redis status: {e}")

# --- DB CALLBACK HELPER ---
def mark_briefing_complete(user_id: str, run_date: str):
    """
    Callback: Updates the user's schedule in MongoDB to confirm the job ran successfully.
    """
    try:
        client = MongoClient(settings.DATABASE_URL)
        db = client[settings.MONGO_DB_NAME]
        collection = db["briefing_schedules"]
        
        result = collection.update_one(
            {"_id": user_id},
            {"$set": {"last_run_date": run_date}}
        )
        client.close()
        
        if result.modified_count > 0:
            print(f"[WORKER] 💾 DB Updated: Marked {user_id} as complete for {run_date}")
        else:
            print(f"[WORKER] ⚠️ DB Update: No document modified for {user_id}")
            
    except Exception as e:
        print(f"[WORKER] ❌ DB Callback Failed: {e}")

async def run_worker():
    """
    Main Worker Loop for NewsCast.
    """
    # 1. Initialize Redis
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        print(f"--- 🎧 NewsCast Audio Worker Started ---")
        print(f"--- Listening on Queue: {settings.REDIS_QUEUE_NAME} ---")
    except Exception as e:
        print(f"[FATAL] Could not connect to Redis: {e}")
        return

    # 2. Build the Graph ONCE
    workflow_builder = BriefingWorkflow()
    app_graph = workflow_builder.create_workflow()

    # 3. Main Loop
    while True:
        try:
            # Block until a job is available
            result = await r.blpop(settings.REDIS_QUEUE_NAME, timeout=0)
            if not result:
                continue
            
            queue_name, job_data_raw = result
            job_data = json.loads(job_data_raw)
            job_id = job_data.get("job_id")
            user_id = job_data.get("user_id")

            # Extract date from job_id (Format: briefing-USER-YYYY-MM-DD)
            job_date_str = job_id[-10:] 
            
            print(f"[WORKER] 🎙️ Processing Job: {job_id}")
            await update_job_status(r, job_id, "processing")

            # 4. Initialize State
            initial_state = BriefingState(
                user_id=user_id,
                config=job_data.get("config", {})
            )

            # 5. Execute Graph
            try:
                final_state = await app_graph.ainvoke(initial_state)
                
                error_message = final_state.get("error")

                if error_message:
                    # --- LOGICAL FAILURE ---
                    print(f"[JOB {job_id}] ❌ Logic Failed: {error_message}")
                    await update_job_status(r, job_id, "failed", error=error_message)
                else:
                    # --- SUCCESS ---
                    print(f"[JOB {job_id}] ✅ Briefing Generated Successfully.")
                    
                    result_payload = {
                        "audio_url": final_state.get("audio_s3_url"),
                        "transcript": final_state.get("final_audio_transcript")
                    }
                    await update_job_status(r, job_id, "completed", result=result_payload)
                    
                    # --- EXECUTE CALLBACK ---
                    # Run synchronous DB update in a thread
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, mark_briefing_complete, user_id, job_date_str)

            except Exception as execution_error:
                # --- CRITICAL CRASH ---
                error_msg_str = str(execution_error)
                print(f"[JOB {job_id}] 💥 Execution Error: {error_msg_str}")
                traceback.print_exc()
                await update_job_status(r, job_id, "crashed", error=error_msg_str)
                
                # Send Alert
                send_error_email(job_id=job_id, source_url="N/A", error_details=error_msg_str)

        except redis.exceptions.ConnectionError:
            print("[ERROR] Lost connection to Redis. Retrying in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[ERROR] Worker loop error: {e}")
            traceback.print_exc()
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_worker())