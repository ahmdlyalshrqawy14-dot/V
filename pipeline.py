import os
import sys
import json
import shlex
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

# Branding / look constants
GOLD_HEX = "#FFD700"
FRAME_THICKNESS = 6
FPS = 25

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
        cmd = 'ffmpeg -y -f lavfi -i color=c=black@0.0:s=1080x1920:d=1 -vframes 1 dust.png'
        subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("[ASSETS] Generated fallback dust.png successfully.")

def ensure_watermark():
    """
    إنشاء واترمارك افتراضي شفاف لو مفيش واترمارك مخصص موجود.
    لو عايز شعارك الخاص، حط ملف watermark.png (شفاف) في نفس المجلد وهيتستخدم تلقائياً.
    """
    if not os.path.exists("watermark.png") or os.path.getsize("watermark.png") == 0:
        cmd = (
            'ffmpeg -y -f lavfi -i color=c=black@0.0:s=300x120 '
            f'-vf "drawtext=text=\'MATH HACKS\':fontcolor={GOLD_HEX}:fontsize=34:'
            'fontfile=fonts/Cairo-Bold.ttf:x=10:y=40:alpha=0.55" '
            '-vframes 1 watermark.png'
        )
        subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("[ASSETS] Generated fallback watermark.png successfully.")

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
    tracks = list(POPULAR_TRACKS)
    random.shuffle(tracks)
    cut_file = "bgm.wav"

    for track in tracks:
        raw_ext = "ogg" if track["url"].endswith(".ogg") else "mp3"
        raw_file = f"temp_{track['name']}.{raw_ext}"

        print(f"[AUDIO] Selected Track: {track['name']} (Drop at {track['start']}s)")

        if not os.path.exists(raw_file) or os.path.getsize(raw_file) < 50000:
            headers = {'User-Agent': 'MathShortsBot/1.0 (Educational Studio; contact@github.com)'}
            req = urllib.request.Request(track['url'], headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=25) as resp, open(raw_file, 'wb') as f:
                    f.write(resp.read())
            except Exception as e:
                print(f"[AUDIO WARN] Download failed for {track['name']}: {e}")
                continue

        if not os.path.exists(raw_file) or os.path.getsize(raw_file) < 50000:
            print(f"[AUDIO WARN] Downloaded file {raw_file} is too small or corrupt.")
            continue

        cmd = [
            "ffmpeg", "-y",
            "-i", raw_file,
            "-ss", str(track['start']),
            "-t", str(duration),
            "-ar", "24000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            cut_file
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            print(f"[AUDIO WARN] FFmpeg cut failed for {track['name']}: {e}")
            continue

        if os.path.exists(cut_file) and os.path.getsize(cut_file) > 10000:
            print(f"[AUDIO] bgm.wav ready using {track['name']} ({os.path.getsize(cut_file)} bytes)")
            return True

    print("[AUDIO WARN] All online BGM tracks failed or yielded empty files.")
    return False

# ============================================================
# 2.6 Asset Integrity Validation
# ============================================================
def validate_assets(content_data):
    sfx_file = "boom.wav" if content_data.get("effect_type") == "shock" else "ding.wav"
    required_files = [
        "chalkboard.png", "voice.mp3", "t_idle_closed.png", "t_idle_open.png",
        "t_point_closed.png", "t_point_open.png", "sticker_active.png", "dust.png",
        "watermark.png", sfx_file, "bgm.wav", "master_video.ass"
    ]
    missing_or_empty = [f for f in required_files if not os.path.exists(f) or os.path.getsize(f) == 0]
    if missing_or_empty:
        print(f"[FATAL] Missing/empty assets: {missing_or_empty}")
        sys.exit(1)
    print("[ASSETS] All required files validated ✓")

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
    ass_file = "master_video.ass"
    if not os.path.exists(ass_file) or os.path.getsize(ass_file) == 0:
        print("[WARN] master_video.ass missing! Creating empty subtitle file.")
        with open(ass_file, "w", encoding="utf-8") as f:
            f.write("[Script Info]\nTitle: Empty\n\n[V4+ Styles]\n\n[Events]\n")

    duration = timestamps["total"]
    print(f"[FFMPEG] Starting multi-layer composite render ({duration:.2f}s)...")

    sfx_file = "boom.wav" if content_data.get("effect_type") == "shock" else "ding.wav"
    t_s1 = timestamps["step1"]
    t_s2 = timestamps["step2"]
    t_res = timestamps["result"]
    sfx_delay_ms = int(t_res * 1000)

    # ---- Teacher sprite timeline conditions ----
    is_pointing = f"(between(t,{t_s1},{t_s2}) + between(t,{t_s2},{t_res}))"
    is_talking = "between(mod(t,0.28),0,0.14)"

    cond_idle_open = f"(not({is_pointing})) * ({is_talking})"
    cond_point_closed = f"({is_pointing}) * (not({is_talking}))"
    cond_point_open = f"({is_pointing}) * ({is_talking})"

    # ---- Teacher position: moved to LEFT side ----
    teacher_x = 80
    teacher_y = 1340

    # ---- Camera: eased pan (ease-in-out) instead of linear + micro shake at reveal ----
    progress = f"min(t/{duration:.2f},1)"
    ease = f"((1-cos(PI*{progress}))/2)"
    shake_window = f"between(t,{t_res},{t_res+0.3})"
    shake_x = f"(6*sin(60*t)*{shake_window})"
    shake_y = f"(4*cos(55*t)*{shake_window})"

    pan_x = f"max(0,min(70,70*{ease}+2*sin(2*PI*t*1.2)+{shake_x}))"
    pan_y = f"max(0,min(90,70*{ease}+2*sin(2*PI*t*0.8+1)+{shake_y}))"

    # ---- Fast zoom-out intro (first ~1s) via zoompan ----
    zoom_frames = FPS  # ~1 second worth of frames
    zoom_expr = f"if(lte(on,{zoom_frames}),1.15-0.15*on/{zoom_frames},1)"

    # ---- Tilt at reveal moment ----
    tilt_window_end = t_res + 0.3
    tilt_angle = f"if(between(t,{t_res},{tilt_window_end}),(3*PI/180)*sin(2*PI*(t-{t_res})*10),0)"

    # ---- Sticker: spring entrance + continuous gentle pulse ----
    sticker_scale_expr = (
        f"iw*(1+0.18*exp(-6*max(t-{t_res},0))*sin(25*max(t-{t_res},0))"
        f"+0.03*sin(2*PI*max(t-{t_res},0)*1.5))"
    )
    # sticker moved to the RIGHT side to balance the teacher on the left
    sticker_x = 560
    sticker_y = 1120

    vf = (
        # background zoom-out intro + eased pan
        f"[0:v]scale=1400:2400,zoompan=z='{zoom_expr}':d=1:s=1180x2020:fps={FPS},"
        f"crop=w=1080:h=1920:x='{pan_x}':y='{pan_y}'[bg_panned];"
        f"[bg_panned]rotate=a='{tilt_angle}':ow=iw:oh=ih:c=none[bg];"
        # teacher layers on the left
        f"[bg][2:v]overlay=x={teacher_x}:y={teacher_y}[t_base];"
        f"[t_base][3:v]overlay=x={teacher_x}:y={teacher_y}:enable='{cond_idle_open}'[t_id_op];"
        f"[t_id_op][4:v]overlay=x={teacher_x}:y={teacher_y}:enable='{cond_point_closed}'[t_pt_cl];"
        f"[t_pt_cl][5:v]overlay=x={teacher_x}:y={teacher_y}:enable='{cond_point_open}'[v_teacher];"
        # sticker with spring + pulse, moved right
        f"[6:v]scale=w='{sticker_scale_expr}':h=-1:eval=frame[stk_sized];"
        f"[stk_sized]fade=t=in:st={t_res}:d=0.2:alpha=1[stk_f];"
        f"[v_teacher][stk_f]overlay=x={sticker_x}:y={sticker_y}:enable='between(t,{t_res},{t_res+2.6})'[v_stk];"
        # dust scroll
        f"[v_stk][7:v]overlay=x='-mod(t*16,1080)':y=0:format=auto[v_dust];"
        # watermark (always visible, corner)
        f"[v_dust][10:v]overlay=x=40:y=40[v_wm];"
        # cinematic color grade + vignette + grain
        "[v_wm]eq=contrast=1.04:saturation=1.10:gamma=1.02,"
        "colorbalance=rs=-0.05:gs=0.01:bs=0.08:rm=-0.03:gm=0.01:bm=0.06,"
        "vignette=PI/5,"
        "noise=alls=6:allf=t,"
        # gold progress bar
        f"drawbox=x=80:y=1800:w=(iw-160)*t/{duration:.2f}:h=8:color={GOLD_HEX}:t=fill,"
        # thin gold frame border (constant, luxury branding)
        f"drawbox=x=0:y=0:w=iw:h=ih:color={GOLD_HEX}@0.55:t={FRAME_THICKNESS},"
        "subtitles=master_video.ass:fontsdir=fonts[outv]"
    )

    af = (
        f"[1:a]volume=1.0,apad[a_voice]; "
        f"[9:a]volume=0.25,apad[a_bgm]; "
        f"[8:a]adelay={sfx_delay_ms}|{sfx_delay_ms},volume=0.85,apad[a_sfx]; "
        f"[a_voice][a_bgm][a_sfx]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[outa]"
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
        f'-loop 1 -t {duration:.2f} -i watermark.png '
        f'-filter_complex "{vf}; {af}" '
        f'-map "[outv]" -map "[outa]" -c:v libx264 -preset ultrafast -crf 22 -c:a aac -t {duration:.2f} {output_filename}'
    )

    try:
        subprocess.run(shlex.split(cmd), check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[FFMPEG ERROR] Render failed!\nSTDERR:\n{e.stderr[-2000:]}")
        sys.exit(1)

    # Multi-frame thumbnail generation
    thumb_time = min(max(t_res, 1.0), duration - 0.5)
    thumb_cmd = f'ffmpeg -y -ss {thumb_time:.2f} -i {output_filename} -vframes 1 -q:v 2 thumbnail.jpg'
    subprocess.run(shlex.split(thumb_cmd), check=True)
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
    ensure_watermark()
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
        print("[AUDIO] Popular BGM unavailable, generating ambient fallback...")
        audio_engine.generate_ambient_bgm(timestamps["total"] + 2.5)

    # التحقق النهائي من وجود ملف صوتي سليم قبل الرندر
    if not os.path.exists("bgm.wav") or os.path.getsize("bgm.wav") < 5000:
        print("[AUDIO WARN] bgm.wav missing or invalid! Forcing fallback generation.")
        audio_engine.generate_ambient_bgm(timestamps["total"] + 2.5)
        if not os.path.exists("bgm.wav") or os.path.getsize("bgm.wav") < 1000:
            anull_cmd = f'ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t {timestamps["total"]+2.5} bgm.wav'
            subprocess.run(
                shlex.split(anull_cmd),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

    validate_assets(content_data)
    render_final_composition(content_data, timestamps, persona)

    # Commit progress to disk
    series_manager.mark_lesson_completed(ctx)
    print("[SUCCESS] Production pipeline finished without errors.")

if __name__ == "__main__":
    asyncio.run(main())
