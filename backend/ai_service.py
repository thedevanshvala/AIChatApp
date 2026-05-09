from groq import Groq, RateLimitError, AuthenticationError
from typing import Optional
import os
import time
from dotenv import load_dotenv
import random

load_dotenv()

# ─────────────────────────────────────
# Load API keys
# ─────────────────────────────────────

def _load_api_keys() -> list:
    keys = []
    i = 1
    while True:
        key = os.getenv(f"GROQ_API_KEY_{i}")
        if not key:
            break
        keys.append(key.strip())
        i += 1

    plain = os.getenv("GROQ_API_KEY")
    if plain and plain.strip() not in keys:
        keys.append(plain.strip())

    if not keys:
        raise ValueError("No Groq API keys found. Add GROQ_API_KEY_1, _2 ... to .env")

    return keys


API_KEYS = _load_api_keys()

# ─────────────────────────────────────
# Per-key cooldown tracker
# ─────────────────────────────────────

_cooldowns: dict = {}   # { key_index: ready_at_unix_timestamp }
_invalid_keys: set = set()     # permanently bad keys


def _mark_rate_limited(idx: int, retry_after_seconds: float):
    _cooldowns[idx] = time.time() + retry_after_seconds
    print(f"[Tracker] Key #{idx+1} rate-limited for {retry_after_seconds:.0f}s")


def _mark_invalid(idx: int):
    _invalid_keys.add(idx)
    print(f"[Tracker] Key #{idx+1} marked invalid/expired")


def _is_available(idx: int) -> bool:
    if idx in _invalid_keys:
        return False
    ready_at = _cooldowns.get(idx)
    if ready_at and time.time() < ready_at:
        return False
    return True


def _next_available_key() -> Optional[int]:
    for i in range(len(API_KEYS)):
        if _is_available(i):
            return i
    return None


def _parse_retry_after(exc: RateLimitError) -> float:
    """Extract retry-after from Groq headers. Falls back to 3600s."""
    try:
        headers = exc.response.headers
        val = headers.get("retry-after") or headers.get("x-ratelimit-reset-requests")
        if val:
            return float(val)
    except Exception:
        pass
    return 3600.0


# ─────────────────────────────────────
# Status report
# ─────────────────────────────────────

def get_key_status() -> list:
    """
    Returns per-key status list:
    { name, status: available|rate_limited|invalid, time_left: str|None }
    """
    result = []
    now = time.time()

    for i in range(len(API_KEYS)):
        name = f"GROQ_API_KEY_{i+1}"

        if i in _invalid_keys:
            result.append({"name": name, "status": "invalid", "time_left": None})
            continue

        ready_at = _cooldowns.get(i)
        if ready_at and now < ready_at:
            secs_left = int(ready_at - now)
            hrs  = secs_left // 3600
            mins = (secs_left % 3600) // 60
            secs = secs_left % 60

            if hrs > 0:
                time_str = f"{hrs}hr {mins}min"
            elif mins > 0:
                time_str = f"{mins}min {secs}sec"
            else:
                time_str = f"{secs}sec"

            result.append({"name": name, "status": "rate_limited", "time_left": time_str})
        else:
            result.append({"name": name, "status": "available", "time_left": None})

    return result


def format_key_status_message() -> str:
    statuses = get_key_status()
    lines = []
    for s in statuses:
        if s["status"] == "available":
            lines.append(f"✅ {s['name']} => Available")
        elif s["status"] == "rate_limited":
            lines.append(f"⏳ {s['name']} => {s['time_left']} left")
        elif s["status"] == "invalid":
            lines.append(f"❌ {s['name']} => Invalid/Expired")
    return "\n".join(lines) if lines else "No keys loaded."


# ─────────────────────────────────────
# Core call with auto-rotation
# ─────────────────────────────────────

def _call_with_rotation(call_fn) -> str:
    while True:
        idx = _next_available_key()

        if idx is None:
            status_msg = format_key_status_message()
            raise RuntimeError(
                f"Saare API keys exhaust ho gaye bc. Ye raha haal:\n\n{status_msg}"
            )

        client = Groq(api_key=API_KEYS[idx])

        try:
            return call_fn(client)

        except RateLimitError as e:
            retry_after = _parse_retry_after(e)
            _mark_rate_limited(idx, retry_after)

        except AuthenticationError:
            _mark_invalid(idx)


# ─────────────────────────────────────
# System Prompt
# ─────────────────────────────────────

SYSTEM_PROMPT = """
Tu "Launda Bot" hai — ek kadak, belagaam Hinglish AI jo seedha bolta hai.

STYLE RULES:
- SIRF 1-2 lines. Isse zyada likha toh tu fail hai.
- Har response mein ek proper roast ya savage line honi chahiye.
- Hindi gaaliyan naturally use kar — bc, mc, bh*nk, ch**iya, rand*, g*nd — jaise real dost bolta hai.
- Useful reh — sawaal ka jawab bhi de, bas roast ke saath.

EXAMPLES (exactly is style mein reply kar):
User: Mujhe neend nahi aa rahi
You: Bc so ja, teri zindagi itni exciting bhi nahi hai ki jaagna worth ho.

User: Python kaise seekhun
You: YouTube khol, "Python tutorial" search kar — teri dimag ke liye bas itna kaafi hai, ch**iye.
"""

# ─────────────────────────────────────
# Easter egg
# ─────────────────────────────────────

_devansh_responses = [
    "Devansh? That's the type of man who'd pin you against the wall just to ask why you're acting bratty.",
    "Careful with Devansh. One flirty conversation and suddenly you're thinking unholy thoughts at 3 AM.",
    "Devansh Vala? The kind of guy who'd say 'good girl' once and completely ruin your mental stability.",
    "He's not romantic. He's the 'come sit on my lap and stop talking' type.",
    "Devansh talks like he already knows how you'd sound begging for attention.",
    "That man gives heavy 'pull your chin up and say it again' energy.",
    "Devansh? The type to flirt slowly just to watch you lose composure first.",
    "He's probably the reason somebody can't sleep properly anymore.",
    "One late-night call with Devansh and suddenly your standards are dangerously unrealistic.",
    "That man definitely flirts like he owns the room and your attention."
]


def _check_custom_response(message: str) -> Optional[str]:
    msg = message.lower()

    # API status query — user can ask in Hinglish or English
    status_triggers = [
        "api status", "key status", "which api", "api limit",
        "api exhaust", "kon sa api", "kaun sa api", "kitne api",
        "api ka haal", "api khatam", "which key"
    ]
    if any(t in msg for t in status_triggers):
        return f"Ye raha tera API ka haal, bc:\n\n{format_key_status_message()}"

    triggers = ["who is devansh", "who is devansh vala", "tell me about devansh", "do you know devansh"]
    if any(t in msg for t in triggers):
        return random.choice(_devansh_responses)

    return None


# ─────────────────────────────────────
# Public functions
# ─────────────────────────────────────

def get_ai_response(messages: list, file_data: dict = None) -> str:
    formatted = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in messages[:-1]:
        formatted.append({"role": msg["role"], "content": msg["content"]})

    last_msg = messages[-1]["content"]

    custom = _check_custom_response(last_msg)
    if custom:
        return custom

    if file_data:
        if file_data["type"] == "image":
            formatted.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{file_data['media_type']};base64,{file_data['content']}"
                        }
                    },
                    {"type": "text", "text": last_msg or "Analyze this image"}
                ]
            })

            def image_call(client):
                res = client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=formatted,
                    max_tokens=250
                )
                return res.choices[0].message.content

            return _call_with_rotation(image_call)

        else:
            file_label = file_data['label']
            fallback_question = f"Please analyze this {file_label}"
            content = (
                f"The user uploaded a {file_label} file.\n\n"
                f"File contents:\n\"\"\"\n{file_data['content']}\n\"\"\"\n\n"
                f"User question: {last_msg or fallback_question}"
            )
            formatted.append({"role": "user", "content": content})

            def file_call(client):
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=formatted,
                    max_tokens=2048
                )
                return res.choices[0].message.content

            return _call_with_rotation(file_call)

    else:
        formatted.append({"role": "user", "content": last_msg})

        def text_call(client):
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=formatted,
                max_tokens=2048
            )
            return res.choices[0].message.content

        return _call_with_rotation(text_call)


def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    import io

    def audio_call(client):
        transcription = client.audio.transcriptions.create(
            file=(filename, io.BytesIO(file_bytes)),
            model="whisper-large-v3",
            response_format="text"
        )
        return transcription

    return _call_with_rotation(audio_call)