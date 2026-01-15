import requests
import traceback
from pprint import pprint
from src.models.BriefingState import BriefingState
from src.config.settings import settings

def notify_briefing_webhook(state: BriefingState) -> BriefingState:
    """
    Final Node: Sends the S3 Audio URL to the configured Webhook.
    """
    pprint("[NODE: NOTIFY WEBHOOK] 🚀 Sending briefing payload...")

    if not settings.WEBHOOK_URL:
        pprint("[NODE: NOTIFY WEBHOOK] No WEBHOOK_URL configured. Skipping.")
        return state

    try:
        # Prepare Payload
        payload = {
            "type": "audio_briefing",
            "user_id": state.user_id,
            "status": "success" if state.audio_s3_url else "failed",
            "audio_url": state.audio_s3_url,
            "transcript": state.final_audio_transcript,
            "error": state.error
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NewsCast/1.0"
        }
        if settings.WEBHOOK_SECRET:
            headers["X-Webhook-Secret"] = settings.WEBHOOK_SECRET

        response = requests.post(
            settings.WEBHOOK_URL,
            json=payload,
            headers=headers,
            timeout=15
        )

        if response.status_code in [200, 201, 202]:
            pprint(f"[NODE: NOTIFY WEBHOOK] ✅ Success! Downstream acknowledged.")
        else:
            pprint(f"[NODE: NOTIFY WEBHOOK] ⚠️ Service returned {response.status_code}: {response.text}")

    except Exception as e:
        pprint(f"[NODE: NOTIFY WEBHOOK] 💥 Error: {e}")
        traceback.print_exc()

    return state