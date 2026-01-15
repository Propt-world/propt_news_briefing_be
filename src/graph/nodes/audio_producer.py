import boto3
import uuid
import traceback
import httpx
from datetime import datetime
from pprint import pprint
from io import BytesIO

from src.models.BriefingState import BriefingState
from src.config.settings import settings

async def audio_producer(state: BriefingState) -> dict:
    """
    Node 5: Audio Producer
    
    Responsibilities:
    1. Select the correct text source (Translated vs Original).
    2. Call OpenAI API directly for TTS (using 'gpt-4o-mini-tts').
    3. Upload the binary audio data to AWS S3.
    4. Generate and store the public S3 URL.
    """
    pprint("[NODE: AUDIO PRODUCER] 🎧 Starting audio generation...")
    
    try:
        # 1. Select Text Source
        # If translated text exists, use it. Otherwise, use the English final script.
        if state.translated_script_text:
            text_input = state.translated_script_text
            pprint("[NODE: AUDIO PRODUCER] Using TRANSLATED (Arabic) script.")
        elif state.final_script_text:
            text_input = state.final_script_text
            pprint("[NODE: AUDIO PRODUCER] Using ORIGINAL (English) script.")
        else:
            return {"error": "No script text found for audio generation."}

        # 2. Configuration
        voice_id = state.config.get("voice", settings.TTS_DEFAULT_VOICE)
        model_id = settings.TTS_MODEL # "gpt-4o-mini-tts"
        
        # 3. Call OpenAI TTS API
        # We use httpx directly because the LangChain wrapper for Audio is distinct/evolving.
        # This gives us precise control over the endpoint and model param.
        
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_id,
            "input": text_input,
            "voice": voice_id,
            "response_format": "mp3"
        }
        
        pprint(f"[NODE: AUDIO PRODUCER] 📡 Calling OpenAI ({model_id}) with voice '{voice_id}'...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech", 
                json=payload, 
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            audio_binary = response.content

        # 4. Upload to S3
        if not settings.AWS_ACCESS_KEY_ID:
            return {"error": "AWS Credentials missing. Cannot upload audio."}

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Generate Key: briefings/{user_id}/YYYY-MM-DD_{uuid}.mp3
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        file_name = f"briefings/{state.user_id}/{today_str}_{uuid.uuid4().hex[:8]}.mp3"
        
        pprint(f"[NODE: AUDIO PRODUCER] ☁️ Uploading to S3: {file_name}")
        
        s3_client.upload_fileobj(
            BytesIO(audio_binary),
            settings.S3_BUCKET_NAME,
            file_name,
            ExtraArgs={'ContentType': 'audio/mpeg'}
        )
        
        # 5. Construct URL
        s3_url = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
        pprint(f"[NODE: AUDIO PRODUCER] ✅ Audio published: {s3_url}")

        return {
            "audio_s3_url": s3_url,
            "final_audio_transcript": text_input
        }

    except Exception as e:
        pprint(f"[NODE: AUDIO PRODUCER] 💥 Error: {e}")
        traceback.print_exc()
        return {"error": str(e)}