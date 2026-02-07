import json
import os
import re
import shlex
import subprocess
import textwrap
import uuid
from pathlib import Path

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
PEXELS_URL = "https://api.pexels.com/videos/search"
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

DEFAULT_RULES = [
    "Don't call anyone more than twice.",
    "Don't start conversations first.",
    "Never apologize to someone who disrespected you just because you love them.",
    "Don't insist on people.",
    "If someone wants to talk to you, they will.",
]

MOOD_CONFIG = {
    "cold": {
        "query": "dark calm nature cinematic no people",
        "voice_speed": "0.86",
        "music_volume": 0.10,
        "caption_font_size": 50,
        "music_tone": 140,
    },
    "dark": {
        "query": "night shadow nature cinematic no people",
        "voice_speed": "0.92",
        "music_volume": 0.20,
        "caption_font_size": 54,
        "music_tone": 120,
    },
    "calm": {
        "query": "soft nature sunrise cinematic no people",
        "voice_speed": "0.98",
        "music_volume": 0.16,
        "caption_font_size": 48,
        "music_tone": 220,
    },
}


def run(cmd: str):
    subprocess.run(cmd, shell=True, check=True)


def generate_script(mood: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return format_script(DEFAULT_RULES)

    prompt = textwrap.dedent(
        f"""
        Generate short psychology advice text in English only.
        Tone: cold, calm, confident. No emojis.
        Topics: boundaries, self-respect, emotional control, mental strength.
        Give only a JSON object with keys: title, rules (array with 5 to 7 short direct lines), closing.
        Fixed format requirements:
        - title must be exactly: How to make your personality strong
        - closing must be exactly: If you want to be a strong person, follow these rules.
        - keep sentences short and direct.
        Mood context: {mood}
        """
    ).strip()

    resp = requests.post(
        f"{GEMINI_URL}?key={api_key}",
        timeout=45,
        json={"contents": [{"parts": [{"text": prompt}]}]},
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    json_text = extract_json(text)

    try:
        payload = json.loads(json_text)
        rules = payload.get("rules") or DEFAULT_RULES
        rules = [clean_line(line) for line in rules][:7]
        if len(rules) < 5:
            rules = DEFAULT_RULES
    except Exception:
        rules = DEFAULT_RULES

    return format_script(rules)


def clean_line(line: str) -> str:
    line = re.sub(r"\s+", " ", str(line)).strip()
    return line.rstrip(".") + "."


def extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Gemini did not return JSON.")
    return text[start : end + 1]


def format_script(rules: list[str]) -> str:
    lines = ["How to make your personality strong", ""]
    for rule in rules:
        lines.append(rule)
    lines.extend(["", "If you want to be a strong person, follow these rules."])
    return "\n".join(lines)


def generate_voice(script: str, mood: str, cache_dir: Path) -> Path:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "VR6AewLTigWG4xSOukaG")
    out = cache_dir / f"voice_{uuid.uuid4().hex}.mp3"

    if not api_key:
        text_file = cache_dir / f"script_{uuid.uuid4().hex}.txt"
        text_file.write_text(script, encoding="utf-8")
        run(
            "ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t 28 "
            f"-q:a 9 -acodec libmp3lame {shlex.quote(str(out))}"
        )
        return out

    payload = {
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.8, "similarity_boost": 0.85, "style": 0.0},
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    resp = requests.post(
        f"{ELEVENLABS_URL}/{voice_id}?optimize_streaming_latency=0&output_format=mp3_44100_128",
        timeout=90,
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()
    out.write_bytes(resp.content)

    adjusted = cache_dir / f"voice_adj_{uuid.uuid4().hex}.mp3"
    run(
        f"ffmpeg -y -i {shlex.quote(str(out))} -filter:a atempo={MOOD_CONFIG[mood]['voice_speed']} "
        f"{shlex.quote(str(adjusted))}"
    )
    return adjusted


def fetch_pexels_background(mood: str, cache_dir: Path) -> Path:
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        out = cache_dir / f"bg_{uuid.uuid4().hex}.mp4"
        run(
            "ffmpeg -y -f lavfi -i color=c=black:s=1080x1920:r=30 -t 30 "
            f"{shlex.quote(str(out))}"
        )
        return out

    headers = {"Authorization": api_key}
    params = {
        "query": MOOD_CONFIG[mood]["query"],
        "orientation": "portrait",
        "per_page": 15,
    }
    resp = requests.get(PEXELS_URL, timeout=45, headers=headers, params=params)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos:
        raise RuntimeError("No Pexels videos found.")

    selected = None
    for item in videos:
        if item.get("user"):
            pass
        files = item.get("video_files", [])
        portrait = [f for f in files if f.get("height", 0) >= f.get("width", 0)]
        choice = (portrait or files)
        if choice:
            selected = choice[0]["link"]
            break
    if not selected:
        raise RuntimeError("No downloadable Pexels file available.")

    out = cache_dir / f"bg_{uuid.uuid4().hex}.mp4"
    with requests.get(selected, timeout=90, stream=True) as dl:
        dl.raise_for_status()
        with open(out, "wb") as f:
            for chunk in dl.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return out


def generate_music(mood: str, duration: float, cache_dir: Path) -> Path:
    out = cache_dir / f"music_{uuid.uuid4().hex}.mp3"
    tone = MOOD_CONFIG[mood]["music_tone"]
    run(
        "ffmpeg -y -f lavfi "
        f"-i " + shlex.quote(f"sine=frequency={tone}:sample_rate=44100") +
        f" -t {duration:.2f} -filter:a volume={MOOD_CONFIG[mood]['music_volume']} "
        f"{shlex.quote(str(out))}"
    )
    return out


def media_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.check_output(cmd).decode().strip()
    return float(result)


def create_captions(script: str, duration: float, mood: str, cache_dir: Path) -> list[tuple[Path, float, float]]:
    lines = [line.strip() for line in script.splitlines() if line.strip()]
    slots = duration / max(len(lines), 1)
    assets = []

    for i, line in enumerate(lines):
        start = i * slots
        end = min(duration, (i + 1) * slots)
        img = cache_dir / f"caption_{i}_{uuid.uuid4().hex}.png"
        size = MOOD_CONFIG[mood]["caption_font_size"]
        cmd = (
            "magick -size 1000x260 xc:none "
            "-gravity center -fill white -stroke black -strokewidth 2 "
            f"-pointsize {size} "
            f"-annotate +0+0 {shlex.quote(line)} {shlex.quote(str(img))}"
        )
        run(cmd)
        assets.append((img, start, end))
    return assets


def build_video(mood: str, output_dir: Path) -> dict:
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)

    script = generate_script(mood)
    voice = generate_voice(script, mood, cache_dir)
    duration = media_duration(voice)
    background = fetch_pexels_background(mood, cache_dir)
    music = generate_music(mood, duration + 1.0, cache_dir)
    caption_assets = create_captions(script, duration, mood, cache_dir)

    output_name = f"short_{mood}_{uuid.uuid4().hex[:8]}.mp4"
    output_file = output_dir / output_name

    input_args = [f"-i {shlex.quote(str(background))}", f"-i {shlex.quote(str(voice))}", f"-i {shlex.quote(str(music))}"]
    for cap, _, _ in caption_assets:
        input_args.append(f"-i {shlex.quote(str(cap))}")

    filter_parts = [
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p[v0]",
        "[2:a][1:a]sidechaincompress=threshold=0.03:ratio=8[ducked]",
        "[ducked][1:a]amix=inputs=2:normalize=0[aout]",
    ]

    current_video = "v0"
    base_y = {"cold": 1500, "dark": 1440, "calm": 1520}[mood]
    for idx, (_, start, end) in enumerate(caption_assets, start=3):
        next_label = f"v{idx}"
        filter_parts.append(
            f"[{current_video}][{idx}:v]overlay=(W-w)/2:{base_y}:enable='between(t,{start:.2f},{end:.2f})'[{next_label}]"
        )
        current_video = next_label

    filter_complex = ";".join(filter_parts)
    cmd = (
        "ffmpeg -y "
        + " ".join(input_args)
        + f" -filter_complex \"{filter_complex}\" "
        + f"-map [{current_video}] -map [aout] -t {duration:.2f} -r 30 "
        + f"-c:v libx264 -pix_fmt yuv420p -c:a aac -shortest {shlex.quote(str(output_file))}"
    )
    run(cmd)

    return {
        "message": "Video generated successfully.",
        "script": script,
        "file": output_name,
        "download_url": f"/download/{output_name}",
    }
