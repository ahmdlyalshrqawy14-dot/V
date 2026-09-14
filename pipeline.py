import os
import sys
import json
import shutil
import random
import asyncio
import urllib.request
import subprocess

import series_manager
import audio_engine
import graphics_engine
import ass_engine

# ============================================================
# 1. Environment & API Key Validation
# ============================================================
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    print("[FATAL] GEMINI_API_KEY environment variable is missing!")
    sys.exit(1)

SERIES_ID = os.environ.get("SERIES_NAME", "speed_math").strip().lower()
MANUAL_LESSON = os.environ.get("LESSON_NUM", None)
FONT_DIR = "fonts"
FONT_NAME = "Cairo"

# ============================================================
# 2. Local Typography & Asset Safeguards
# ============================================================
def ensure_fonts():
    global FONT_NAME
    os.makedirs(FONT_DIR, exist_ok=True)
    candidates = [
        "Cairo-Bold.ttf",
        "Cairo-Regular.ttf",
        os.path.join(FONT_DIR, "Cairo-Bold.ttf"),
        os.path.join(FONT_DIR, "Cairo-Regular.ttf")
    ]
    found = next((c for c in candidates if os.path.exists(c) and os.path.getsize(c) > 10000), None)
    if found:
        target = os.path.join(FONT_DIR, "Cairo-Bold.ttf")
        if found != target:
            shutil.copyfile(found, target)
        print(f"[FONTS] Local font verified: {found}")
    FONT_NAME = "Cairo"

def ensure_dust_layer():
    """إنشاء طبقة غبار شفافة تلقائياً إذا لم تكن موجودة لتفادي توقف FFmpeg"""
    if not os.path.exists("dust.png") or os.path.getsize("dust.png") == 0:
        subprocess.run(
            'ffmpeg -y -f lavfi -i color=c=black@0.0:s=1080x1920:d=1 -vframes 1 dust.png',
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("[ASSETS] Generated fallback dust.png successfully.")

# ============================================================
# 2.5 Music Manager (Random Popular Tracks @ 25% Volume)
# ============================================================
POPULAR_TRACKS = [
    {
        "name": "monkeys_spinning",
        "start": 0,
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/4b/Monkeys_Spinning_Monkeys.ogg"
    },
    {
        "name": "sneaky_snitch",
        "start": 5,
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/ec/Sneaky_Snitch.ogg"
    },
    {
        "name": "invincible_ncs",
        "start": 50,
        "url": "https://archive.org/download/deaf-kev-invincible-ncs-release/DEAF%20KEV%20-%20Invincible%20%5BNCS%20Release%5D.mp3"
    },
    {
        "name": "xenogenesis",
        "start": 58,
        "url": "https://archive.org/download/thefatrat-xenogenesis/TheFatRat%20-%20Xenogenesis.mp3"
    },
    {
        "name": "sky_high_ncs",
        "start": 45,
        "url": "https://archive.org/download/elektronomia-sky-high-ncs-release/Elektronomia%20-%20Sky%20High%20%5BNCS%20Release%5D.mp3"
    }
]

def prepare_random_bgm(duration=30):
    track = random.choice(POPULAR_TRACKS)
    raw_ext = "ogg" if track["url"].endswith(".ogg") else "mp3"
    raw_file = f"temp_{track['name']}.{raw_ext}"
    cut_file = "bgm.wav"

    print(f"[AUDIO] Selected Track: {track['name']} (Drop at {track['start']}s)")

    if not os.path.exists(raw_file):
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(track['url'], headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp, open(raw_file, 'wb') as f:
                f.write(resp.read())
        except Exception as e:
            print(f"[AUDIO WARN] Download failed for {track['name']}: {e}")
            return False

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(track['start']),
        "-t", str(duration),
        "-i", raw_file,
        "-c:a", "pcm_s16le",
        cut_file
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"[AUDIO WARN] FFmpeg cut failed: {e}")
        return False

# ============================================================
# 3. Gemini Structured Lesson Generation
# ============================================================
def generate_lesson_script(lesson_info, persona):
    topic = lesson_info.get("topic", "Multiply by 11 mentally")
    example = lesson_info.get("example", "43 x 11")
    teacher_name = persona.get("name", "Professor")

    print(f"[GEMINI] Generating structured lesson script for '{topic}'...")
    prompt = f"""
    You are {teacher_name}, an elite viral math educator on TikTok and YouTube Shorts.
    Create an ultra-retaining 25 to 30-second math hack.

    LESSON FOCUS:
    - Topic: {topic}
    - Problem Example: {example}

    SCRIPTING RULES:
    1. Hook (spoken_hook): Immediate challenge or question. No fluff, no greetings (18-24 words).
    2. Step 1 (spoken_step1): First calculation action (18-24 words).
    3. Step 2 (spoken_step2): Second action and equation calculation (18-24 words).
    4. Result (spoken_result): Big reveal and call to follow (15-20 words).
    5. Write out all spoken numbers as plain English words (e.g., 'forty-three', 'eleven', 'plus').
    6. Absolutely NO LaTeX or raw math syntax in spoken fields.

    Output strictly valid JSON with this exact schema:
    {{
      "title": "Viral Math Hack Title with Emojis",
      "description": "Shorts description with hashtags #math #shorts #mathhacks",
      "tags": "math, shorts, math tricks, mental math, quick calculation",
      "hook_text": "Short Problem Title (e.g. 43 × 11 in 3 Seconds)",
      "spoken_hook": "Spoken hook text here.",
      "step_1": "1. First visual hack rule",
      "spoken_step1": "Spoken step 1 text here.",
      "step_2": "2. Equation calculation applied",
      "spoken_step2": "Spoken step 2 text here.",
      "result_text": "Final Answer = Result 🎉",
      "spoken_result": "Spoken result text here.",
      "joke_text": "Punchy Sticker Tagline (e.g. Math Genius!)",
      "effect_type": "shock"
    }}
    """

    models = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.1-flash",
        "gemini-3.5-flash-lite"
    ]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.7}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                parsed = json.loads(raw_text.strip())
                if "spoken_hook" in parsed and "step_1" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini model {model_name} attempt failed: {e}")
            continue

    raise RuntimeError("[FATAL] All Gemini synthesis attempts failed.")

# ============================================================
# 4. Final Video Assembly (FFmpeg Multipass Compositor)
# ============================================================
def render_final_composition(content_data, timestamps, persona, output_filename="final_video.mp4"):
    duration = timestamps["total"]
    print(f"[FFMPEG] Starting multi-layer composite render ({duration:.2f}s)...")

    sfx_file = "boom.wav" if content_data.get("effect_type") == "shock" else "ding.wav"
    t_s1 = timestamps["step1"]
    t_s2 = timestamps["step2"]
    t_res = timestamps["result"]
    sfx_delay_ms = int(t_res * 1000)

    # Teacher sprite timeline conditions
    is_pointing = f"(between(t,{t_s1},{t_s2}) + between(t,{t_s2},{t_res}))"
    is_talking = "between(mod(t,0.28),0,0.14)"

    cond_idle_open = f"(not({is_pointing})) * ({is_talking})"
    cond_point_closed = f"({is_pointing}) * (not({is_talking}))"
    cond_point_open = f"({is_pointing}) * ({is_talking})"

    # Fluid Ken Burns zoom & micro-camera motion
    pan_x = f"max(0,min(70,(50)*(t/{duration:.2f})+2*sin(2*PI*t*1.2)))"
    pan_y = f"max(0,min(90,(70)*(t/{duration:.2f})+2*sin(2*PI*t*0.8+1)))"

    # Sticker fade-in transition
    stk_fade = f"[6:v]fade=t=in:st={t_res}:d=0.2:alpha=1[stk_f]"

    vf = (
        f"[0:v]crop=w=1080:h=1920:x='{pan_x}':y='{pan_y}'[bg];"
        "[bg][2:v]overlay=x=630:y=1340[t_base];"
        f"[t_base][3:v]overlay=x=630:y=1340:enable='{cond_idle_open}'[t_id_op];"
        f"[t_id_op][4:v]overlay=x=630:y=1340:enable='{cond_point_closed}'[t_pt_cl];"
        f"[t_pt_cl][5:v]overlay=x=630:y=1340:enable='{cond_point_open}'[v_teacher];"
        f"{stk_fade};"
        f"[v_teacher][stk_f]overlay=x=80:y=1120:enable='between(t,{t_res},{t_res+2.6})'[v_stk];"
        f"[v_stk][7:v]overlay=x='-mod(t*16,1080)':y=0:format=auto[v_dust];"
        "[v_dust]eq=contrast=1.04:saturation=1.10,"
        f"drawbox=x=80:y=1800:w=(iw-160)*t/{duration:.2f}:h=8:color=#facc15:t=fill,"
        "subtitles=master_video.ass:fontsdir=fonts[outv]"
    )

    af = (
        f"[9:a]volume=0.25[bgm_soft]; "
        f"[1:a]asplit=2[v_main][v_sc]; "
        f"[bgm_soft][v_sc]sidechaincompress=threshold=0.03:ratio=5:attack=100:release=400[bgm_ducked]; "
        f"[v_main][bgm_ducked]amix=inputs=2:duration=first[a_voice_bgm]; "
        f"[8:a]adelay={sfx_delay_ms}|{sfx_delay_ms},volume=0.85[a_sfx]; "
        f"[a_voice_bgm][a_sfx]amix=inputs=2:duration=first[outa]"
    )

    cmd = (
        f'ffmpeg -y '
        f'-loop 1 -t {duration:.2f} -i chalkboard.png '
        f'-i voice.mp3 '
        f'-loop 1 -t {duration:.2f} -i t_idle_closed.png '
        f'-loop 1 -t {duration:.2f} -i t_idle_open.png '
        f'-loop 1 -t {duration:.2f} -i t_point_closed.png '
        f'-loop 1 -t {duration:.2f} -i t_point_open.png '
        f'-loop 1 -t {duration:.2f} -i sticker_active.png '
        f'-loop 1 -t {duration:.2f} -i dust.png '
        f'-i {sfx_file} '
        f'-i bgm.wav '
        f'-filter_complex "{vf}; {af}" '
        f'-map "[outv]" -map "[outa]" -c:v libx264 -preset ultrafast -crf 22 -c:a aac -t {duration:.2f} {output_filename}'
    )
    subprocess.run(cmd, shell=True, check=True)

    # Multi-frame thumbnail generation
    thumb_time = min(max(t_res, 1.0), duration - 0.5)
    subprocess.run(f'ffmpeg -y -ss {thumb_time:.2f} -i {output_filename} -vframes 1 -q:v 2 thumbnail.jpg', shell=True)
    print(f"[FFMPEG] Render complete: {output_filename} + thumbnail.jpg")

# ============================================================
# 5. Master Pipeline Execution
# ============================================================
async def main():
    print("==================================================")
    print("      MATH HACK STUDIO - AUTOMATED PIPELINE       ")
    print("==================================================")

    ensure_fonts()
    ensure_dust_layer()
    audio_engine.generate_sfx()

    # Resolve context from active series
    ctx = series_manager.resolve_lesson_and_persona(
        series_id=SERIES_ID,
        manual_lesson_id=MANUAL_LESSON
    )
    lesson = ctx["lesson"]
    persona = ctx["persona"]

    # Generate script and visuals
    content_data = generate_lesson_script(lesson, persona)
    graphics_engine.build_all_graphics(persona, content_data, lesson_num=lesson["lesson_id"])

    # Export metadata manifest
    meta_filename = f"details_lesson_{lesson['lesson_id']:03d}.txt"
    with open(meta_filename, "w", encoding="utf-8") as f:
        f.write(f"Title:\n{content_data.get('title')}\n\n")
        f.write(f"Teacher:\n{persona.get('name')} ({persona.get('tagline')})\n\n")
        f.write(f"Description:\n{content_data.get('description')}\n\n")
        f.write(f"Tags:\n{content_data.get('tags')}\n")

    # Synthesize audio, build typography, and render
    timestamps, words_data = await audio_engine.build_complete_voiceover(content_data, persona)
    ass_engine.generate_master_ass(content_data, timestamps, words_data, persona, font_name=FONT_NAME)
    
    # Download and prepare random popular BGM (drop cut)
    bgm_ready = prepare_random_bgm(timestamps["total"] + 2.5)
    if not bgm_ready:
        audio_engine.generate_ambient_bgm(timestamps["total"] + 2.5)

    render_final_composition(content_data, timestamps, persona)

    # Commit progress to disk
    series_manager.mark_lesson_completed(ctx)
    print("[SUCCESS] Production pipeline finished without errors.")

if __name__ == "__main__":
    asyncio.run(main())
