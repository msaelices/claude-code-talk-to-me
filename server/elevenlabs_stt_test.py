# example.py
from io import BytesIO

import requests
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

elevenlabs = ElevenLabs(
    api_key="7f186896036241301149d47c06cd35f6",
)

audio_url = "https://storage.googleapis.com/eleven-public-cdn/audio/marketing/nicole.mp3"
response = requests.get(audio_url)
audio_data = BytesIO(response.content)

transcription = elevenlabs.speech_to_text.convert(
    file=audio_data,
    model_id="scribe_v2",  # Model to use
    tag_audio_events=True,  # Tag audio events like laughter, applause, etc.
    language_code="eng",  # Language of the audio file. If set to None, the model will detect the language automatically.
    diarize=True,  # Whether to annotate who is speaking
)

print(transcription)
