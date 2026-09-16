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
# 1. Environment & Global Constants
# ============================================================
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    print("[FATAL] GEMINI_API_KEY environment variable is missing!")
    sys.exit(1)

SERIES_ID = os.environ.get("SERIES_NAME", "speed_math").strip().lower()
MANUAL_LESSON = os.environ.get("LESSON_NUM", None)
FONT_DIR = "fonts"
FONT_NAME = "Cairo"

# Branding & Visual Scaffolding
GOLD_HEX = "#FFD700"
FPS = 25

# Character Micro-Behaviors (حل المشكلة 16: ضبط الرمش)
BLINK_INTERVAL = 2.8
BLINK_DURATION = 0.16

# حل المشاكل 3 و25 و31 و44: تقليص وقت النهاية لمنع الصمت والوقت الميت
TAIL_PAD = 0.3

# Teacher Coordinate Anchors
TEACHER_X = 80
TEACHER_Y = 1340

# ============================================================
# 2. Typography Verification
# ============================================================
def ensure_fonts():
    os.makedirs(FONT_DIR, exist_ok=True)
    target = os.path.join(FONT_DIR, "Cairo-Bold.ttf")
    candidates = [
        target,
        "Cairo-Bold.ttf",
        "Cairo-Regular.ttf",
        os.path.join(FONT_DIR, "Cairo-Regular.ttf")
    ]
    found = next((c for c in candidates if os.path.exists(c) and os.path.getsize(c) > 5000), None)
    if not found:
        print("[FATAL] Cairo font is missing! Ensure Cairo-Bold.ttf is in fonts/ directory.")
        sys.exit(1)

    if found != target:
        shutil.copyfile(found, target)
    print(f"[FONTS] Font verified successfully: {found}")

# ============================================================
# 3. Audio & Music Pipeline
# ============================================================
POPULAR_TRACKS = [
    {
        "name": "sky_high_elektronomia",
        "start": 45,
        "url": "https://archive.org/download/elektronomia-sky-high-ncs-release_202403/Elektronomia%20-%20Sky%20High%20%5BNCS%20Release%5D.mp3"
    },
    {
        "name": "advertime",
        "start": 0,
        "url": "https://archive.org/download/happy-background-music/Advertime.mp3"
    },
    {
        "name": "city_sunshine",
        "start": 0,
        "url": "https://archive.org/download/happy-background-music/City%20Sunshine.mp3"
    },
    {
        "name": "invincible_deaf_kev",
        "start": 50,
        "url": "https://archive.org/download/deaf-kev-invincible-ncs-release/DEAF%20KEV%20-%20Invincible%20%5BNCS%20Release%5D.mp3"
    },
    {
        "name": "invincible_backup",
        "start": 50,
        "url": "https://archive.org/download/NCSandEDMMusic/DEAF%20KEV%20-%20Invincible.mp3"
    }
]

def prepare_random_bgm(duration=30):
    tracks = list(POPULAR_TRACKS)
    random.shuffle(tracks)
    cut_file = "bgm.wav"

    for track in tracks:
        raw_file = f"temp_{track['name']}.mp3"
        print(f"[AUDIO] Fetching background music: {track['name']} (Drop: {track['start']}s)")

        if not os.path.exists(raw_file) or os.path.getsize(raw_file) < 50000:
            headers = {'User-Agent': 'MathShortsBot/1.0 (Educational Studio; contact@github.com)'}
            req = urllib.request.Request(track['url'], headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=20) as resp, open(raw_file, 'wb') as f:
                    f.write(resp.read())
            except Exception as e:
                print(f"[AUDIO WARN] Download failed for {track['name']}: {e}")
                continue

        if not os.path.exists(raw_file) or os.path.getsize(raw_file) < 50000:
            continue

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(track['start']),
            "-t", str(duration),
            "-i", raw_file,
            "-c:a", "pcm_s16le",
            cut_file
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(cut_file) and os.path.getsize(cut_file) > 10000:
            print(f"[AUDIO] bgm.wav ready: {track['name']}")
            return True

    print("[AUDIO WARN] All online BGM tracks failed or unavailable.")
    return False

# ============================================================
# 4. Asset Integrity Verification
# ============================================================
def validate_assets():
    required_files = [
        "chalkboard.png", "voice.mp3", "bgm.wav", "master_video.ass",
        "t_idle_closed.png", "t_idle_open.png",
        "t_point_closed.png", "t_point_open.png",
        "t_thinking.png", "t_blink.png"
    ]
    missing = [f for f in required_files if not os.path.exists(f) or os.path.getsize(f) == 0]
    if missing:
        print(f"[FATAL] Missing required production assets: {missing}")
        sys.exit(1)
    print("[ASSETS] All production assets verified ✓")

# ============================================================
# 5. Script & Content Generation (Gemini)
# ============================================================
def generate_lesson_script(lesson_info, persona):
    topic = lesson_info.get("topic", "Multiply by 11 mentally")
    example = lesson_info.get("example", "43 x 11")
    teacher_name = persona.get("name", "Professor")

    print(f"[GEMINI] Generating lesson script for '{topic}'...")
        prompt = f"""
    You are {teacher_name}, an elite viral math educator on TikTok and YouTube Shorts.
    Create an ultra-retaining 25 to 30-second complete math hack breakdown.

    LESSON FOCUS:
    - Topic: {topic}
    - Problem Example: {example}

    WORD COUNT AND PACING RULES (TARGET: 65-75 TOTAL SPOKEN WORDS FOR 25-30 SECONDS):
    1. Hook (spoken_hook): Immediate punchy challenge, question, and motivation (12-16 words).
       Example: 'Stop doing long math! Can you square thirty-one in your head in just three seconds?'
    2. Step 1 (spoken_step1): Detailed explanation of the baseline mental trick and first calculation (18-22 words).
       Example: 'First, round down to thirty and square it to get nine hundred. Keep that big number locked in your head!'
    3. Step 2 (spoken_step2): Guiding the viewer through the middle calculation and combining the values (18-22 words).
       Example: 'Next, double thirty to get sixty, and add it to nine hundred, giving us nine hundred and sixty!'
    4. Result (spoken_result): The final touch, the reveal, and a direct challenge to the audience for comments (16-20 words).
       Example: 'Finally, just add one to get nine hundred sixty-one! Now, can you calculate forty-one? Tell me below!'

    FORMATTING RULES:
    5. Write out all spoken numbers as plain English words (e.g., 'forty-three', 'eleven', 'plus').
    6. Absolutely NO LaTeX or raw math syntax in spoken fields.
    7. Topic vs Hook: 'title' is the general category name. 'hook_text' MUST be the exact problem challenge (e.g., '{example} in 3 Seconds') and must NOT repeat the wording of 'title'.
    8. Visual Steps: 'step_1' and 'step_2' must show actual concise math calculation numbers (e.g., '1. 30² = 900'), NOT long descriptive text.
    9. Step Numbering: 'result_text' MUST start with '3. Final Answer = ' to maintain sequence.
    10. Do NOT use the pipe symbol '|' anywhere.
    11. CRITICAL: NEVER include exclamation marks '!' in equations or results.

    Output strictly valid JSON with this exact schema:
    {{
      "title": "Viral Math Hack Title with Emojis",
      "description": "Shorts description with hashtags #math #shorts #mathhacks",
      "tags": "math, shorts, math tricks, mental math, quick calculation",
      "hook_text": "Short Problem Title (e.g. 43 × 11 in 3 Seconds)",
      "spoken_hook": "Spoken hook text here.",
      "step_1": "1. First visual calculation rule",
      "spoken_step1": "Spoken step 1 text here.",
      "step_2": "2. Second visual calculation applied",
      "spoken_step2": "Spoken step 2 text here.",
      "result_text": "3. Final Answer = Result",
      "spoken_result": "Spoken result text and comment challenge here."
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
                    for k, v in parsed.items():
                        if isinstance(v, str):
                            parsed[k] = v.replace("|", "").replace("!", "").strip()

                    if not parsed.get("step_1"): parsed["step_1"] = "1. First step"
                    if not parsed.get("step_2"): parsed["step_2"] = "2. Second step"

                    res_str = parsed.get("result_text", "")
                    if not res_str.startswith("3."):
                        clean_res = res_str.lstrip("1234567890. ")
                        parsed["result_text"] = f"3. {clean_res}"

                    return parsed
        except Exception as e:
            print(f"[WARN] Model {model_name} attempt failed: {e}")
            continue

    raise RuntimeError("[FATAL] All Gemini synthesis attempts failed.")

# ============================================================
# 6. Compositor & FFmpeg Master Render
# ============================================================
def render_final_composition(content_data, timestamps, words_data, persona, output_filename="final_video.mp4"):
    duration = timestamps["total"]
    render_duration = duration + TAIL_PAD
    print(f"[FFMPEG] Starting master render ({render_duration:.2f}s | Audio sync duration: {duration:.2f}s)...")

    t_hook = timestamps.get("hook", 0.4)
    t_s1 = timestamps["step1"]
    t_s2 = timestamps["step2"]
    t_res = timestamps["result"]

    # Lip-sync
    if words_data:
        intervals = []
        c_start = words_data[0]["start"]
        c_end = words_data[0]["end"]
        for w in words_data[1:]:
            if w["start"] - c_end < 0.2:
                c_end = w["end"]
            else:
                intervals.append((round(c_start, 2), round(c_end, 2)))
                c_start = w["start"]
                c_end = w["end"]
        intervals.append((round(c_start, 2), round(c_end, 2)))

        speaking_active = "+".join([f"between(t\\,{s}\\,{e})" for s, e in intervals])
        is_talking = f"({speaking_active})*between(mod(t,0.28),0,0.14)"
    else:
        is_talking = "between(mod(t,0.28),0,0.14)"

    # Sprite timelines
    is_pointing = f"(between(t,{t_s1},{t_s2})+between(t,{t_s2},{t_res}))"
    is_thinking = f"lt(t,{t_hook})"

    cond_idle_open = f"(not({is_pointing}))*({is_talking})"
    cond_point_closed = f"({is_pointing})*(not({is_talking}))"
    cond_point_open = f"({is_pointing})*({is_talking})"
    cond_blink = f"between(mod(t,{BLINK_INTERVAL}),0,{BLINK_DURATION})"

    # Dynamic camera movements
    progress = f"min(t/{duration:.2f},1)"
    ease = f"((1-cos(PI*{progress}))/2)"
    shake_window = f"between(t,{t_res},{t_res+0.3})"
    shake_x = f"(6*sin(60*t)*{shake_window})"
    shake_y = f"(4*cos(55*t)*{shake_window})"

    pan_x = f"max(0,min(70,70*{ease}+2*sin(2*PI*t*1.2)+{shake_x}))"
    pan_y = f"max(0,min(90,70*{ease}+2*sin(2*PI*t*0.8+1)+{shake_y}))"

    # تصحيح الخطأ: استخدام إطارات 'on' بدلاً من 't' داخل zoompan
    f_hook = int(t_hook * FPS)
    f_res = int(t_res * FPS)
    f_res_end = int((t_res + 1.5) * FPS)
    zoom_expr = f"if(lte(on,{f_hook}),1.08,if(between(on,{f_res},{f_res_end}),1.06,1.0))"

    vf = (
        f"[0:v]scale=1400:2400,zoompan=z='{zoom_expr}':d=1:s=1180x2020:fps={FPS},"
        f"crop=w=1080:h=1920:x='{pan_x}':y='{pan_y}'[bg];"
        f"[bg][2:v]overlay=x={TEACHER_X}:y={TEACHER_Y}[t_base];"
        f"[t_base][3:v]overlay=x={TEACHER_X}:y={TEACHER_Y}:enable='{cond_idle_open}'[t_id_op];"
        f"[t_id_op][4:v]overlay=x={TEACHER_X}:y={TEACHER_Y}:enable='{cond_point_closed}'[t_pt_cl];"
        f"[t_pt_cl][5:v]overlay=x={TEACHER_X}:y={TEACHER_Y}:enable='{cond_point_open}'[t_pt_op];"
        f"[t_pt_op][6:v]overlay=x={TEACHER_X}:y={TEACHER_Y}:enable='{is_thinking}'[t_think];"
        f"[t_think][7:v]overlay=x={TEACHER_X}:y={TEACHER_Y}:enable='{cond_blink}'[v_teacher];"
        "[v_teacher]eq=contrast=1.04:saturation=1.10:gamma=1.02,"
        "colorbalance=rs=-0.05:gs=0.01:bs=0.08:rm=-0.03:gm=0.01:bm=0.06,"
        "vignette=PI/5,"
        f"drawbox=x=80:y=1740:w=(iw-160)*min(1\\,t/{duration:.2f}):h=8:color={GOLD_HEX}:t=fill,"
        "subtitles=master_video.ass:fontsdir=fonts[outv]"
    )

    af = (
        "[1:a]volume=1.0[a_voice]; "
        "[8:a]volume=0.25[a_bgm]; "
        "[a_voice][a_bgm]amix=inputs=2:duration=longest:dropout_transition=2:normalize=0[outa]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", f"{render_duration:.2f}", "-i", "chalkboard.png",
        "-i", "voice.mp3",
        "-loop", "1", "-t", f"{render_duration:.2f}", "-i", "t_idle_closed.png",
        "-loop", "1", "-t", f"{render_duration:.2f}", "-i", "t_idle_open.png",
        "-loop", "1", "-t", f"{render_duration:.2f}", "-i", "t_point_closed.png",
        "-loop", "1", "-t", f"{render_duration:.2f}", "-i", "t_point_open.png",
        "-loop", "1", "-t", f"{render_duration:.2f}", "-i", "t_thinking.png",
        "-loop", "1", "-t", f"{render_duration:.2f}", "-i", "t_blink.png",
        "-i", "bgm.wav",
        "-filter_complex", f"{vf}; {af}",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-t", f"{render_duration:.2f}",
        output_filename
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[FFMPEG ERROR] Render failed!\n{e.stderr[-2000:]}")
        sys.exit(1)

    thumb_time = min(max(t_res, 1.0), render_duration - 0.5)
    thumb_cmd = [
        "ffmpeg", "-y",
        "-ss", f"{thumb_time:.2f}",
        "-i", output_filename,
        "-vframes", "1",
        "-q:v", "2",
        "thumbnail.jpg"
    ]
    subprocess.run(thumb_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[FFMPEG] Render complete: {output_filename} + thumbnail.jpg")

# ============================================================
# 7. Production Master Pipeline
# ============================================================
async def main():
    print("==================================================")
    print("      MATH HACK STUDIO - PRODUCTION PIPELINE      ")
    print("==================================================")

    ensure_fonts()

    ctx = series_manager.resolve_lesson_and_persona(
        series_id=SERIES_ID,
        manual_lesson_id=MANUAL_LESSON
    )
    lesson = ctx["lesson"]
    persona = ctx["persona"]

    content_data = generate_lesson_script(lesson, persona)
    graphics_engine.build_all_graphics(persona, content_data, lesson_num=lesson["lesson_id"])

    meta_filename = f"details_lesson_{lesson['lesson_id']:03d}.txt"
    with open(meta_filename, "w", encoding="utf-8") as f:
        f.write(f"Title:\n{content_data.get('title')}\n\n")
        f.write(f"Teacher:\n{persona.get('name')} ({persona.get('tagline')})\n\n")
        f.write(f"Description:\n{content_data.get('description')}\n\n")
        f.write(f"Tags:\n{content_data.get('tags')}\n")

    timestamps, words_data = await audio_engine.build_complete_voiceover(content_data, persona)
    ass_engine.generate_master_ass(content_data, timestamps, words_data, persona, font_name=FONT_NAME)

    required_bgm_time = timestamps["total"] + 2.5
    bgm_ready = prepare_random_bgm(required_bgm_time)
    if not bgm_ready:
        print("[AUDIO] Generating ambient BGM fallback...")
        audio_engine.generate_ambient_bgm(required_bgm_time)

    if not os.path.exists("bgm.wav") or os.path.getsize("bgm.wav") < 1000:
        print("[AUDIO] Fallback to clean studio silence...")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(required_bgm_time), "bgm.wav"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )

    validate_assets()
    render_final_composition(content_data, timestamps, words_data, persona)

    series_manager.mark_lesson_completed(ctx)
    print("[SUCCESS] Production pipeline finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())
