# Psychology Shorts Auto Generator

Web app that generates vertical short-form videos (Reels/TikTok/Shorts) with psychology advice in a cold, calm, confident style.

## Features
- Auto text generation with Gemini API.
- Fixed script format:
  - Title: `How to make your personality strong`
  - 5-7 rules (boundaries, self-respect, emotional control, mental strength)
  - Closing: `If you want to be a strong person, follow these rules.`
- Mood selector (Cold / Dark / Calm) controls background style, voice pacing, music tone/volume, and caption behavior.
- Male English AI voice via ElevenLabs.
- Nature/cinematic background clips from Pexels (no hardcoded key).
- Video rendering pipeline: FFmpeg + ImageMagick caption assets.
- MP4 export + download endpoint.

## API keys and env vars
Use environment variables only:

```bash
PEXELS_API_KEY=your_pexels_key_here
GEMINI_API_KEY=your_gemini_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id_here
```

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Notes
- If API keys are missing, the app uses safe local fallbacks (silent voice + black background) so the pipeline remains testable.
- Requires `ffmpeg`, `ffprobe`, and `magick` installed on the host.
