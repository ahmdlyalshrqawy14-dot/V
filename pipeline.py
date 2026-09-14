import os
import sys
import re
import json
import random
import shutil
import asyncio
import urllib.request
import wave
import math
import struct
import subprocess
import edge_tts
from gtts import gTTS
from PIL import Image, ImageDraw

# ============================================================
# 1. Environment & Global Settings (English Only)
# ============================================================
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    print("❌ Critical Error: GEMINI_API_KEY is not set!")
    sys.exit(1)

SERIES_NAME = os.environ.get("SERIES_NAME", "Quick Math Hacks")
LESSON_NUM = os.environ.get("LESSON_NUM", "1")
LANG = "en"
TARGET_DURATION = int(os.environ.get("TARGET_DURATION", "30"))

FONT_DIR = "fonts"
FONT_NAME = "Cairo"

# ============================================================
# 2. Local Font Verification
# ============================================================
def ensure_fonts():
    global FONT_NAME
    os.makedirs(FONT_DIR, exist_ok=True)
    candidates = [
        "Cairo-Bold.ttf",
        "Cairo-Regular.ttf",
        os.path.join(FONT_DIR, "Cairo-Bold.ttf")
    ]
    found = next((c for c in candidates if os.path.exists(c) and os.path.getsize(c) > 10000), None)
    if found:
        target = os.path.join(FONT_DIR, "Cairo-Bold.ttf")
        if found != target:
            shutil.copyfile(found, target)
    FONT_NAME = "Cairo"
    print(f"✓ Font configured: {FONT_NAME}")

# ============================================================
# 3. Accurate Duration Probe
# ============================================================
def get_audio_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        val = float(res.stdout.strip())
        return max(val, 0.5)
    except Exception:
        return 2.0

# ============================================================
# 4. Ambient BGM Generator
# ============================================================
def generate_ambient_bgm(duration, output_file="bgm.wav"):
    if os.path.exists(output_file):
        return output_file
    sample_rate = 24000
    total_samples = int(duration * sample_rate)
    chords = [
        [130.81, 164.81, 196.00, 246.94],
        [110.00, 130.81, 164.81, 196.00],
        [87.31,  110.00, 130.81, 164.81],
        [98.00,  123.47, 146.83, 174.61],
    ]
    with wave.open(output_file, "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sample_rate)
        data = []
        chord_len = int(sample_rate * 3.5)
        for i in range(total_samples):
            t = i / sample_rate
            chord_idx = (i // chord_len) % len(chords)
            sample_val = sum(math.sin(2 * math.pi * freq * t) for freq in chords[chord_idx])
            sample_val = (sample_val / len(chords[chord_idx])) * 0.12
            envelope = min(1.0, t / 1.5) * min(1.0, (duration - t) / 1.5)
            val = int(32767 * sample_val * envelope)
            data.append(struct.pack('<h', max(-32767, min(32767, val))))
        f.writeframes(b''.join(data))
    return output_file

# ============================================================
# 5. SFX Generator
# ============================================================
def generate_sfx():
    with wave.open("ding.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        data = [struct.pack('<h', int(32767 * 0.4 * math.sin(2 * math.pi * 987.77 * (i/24000)) * math.exp(-6 * (i/24000)))) for i in range(12000)]
        f.writeframes(b''.join(data))

    with wave.open("boom.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        data = [struct.pack('<h', int(32767 * 0.6 * math.sin(2 * math.pi * max(45, 140 - 110 * (i/24000)) * (i/24000)) * math.exp(-3 * (i/24000)))) for i in range(19200)]
        f.writeframes(b''.join(data))

# ============================================================
# 6. Visual Graphics (Board, Teacher, Particles)
# ============================================================
def generate_graphics(data):
    board = Image.new("RGBA", (1180, 2040), "#3c2211")
    d = ImageDraw.Draw(board)
    d.rectangle([25, 45, 1155, 1995], fill="#5a3217")
    top_color, bottom_color = (17, 51, 39), (10, 28, 22)
    gx0, gy0, gx1, gy1 = 55, 75, 1125, 1965
    gh = gy1 - gy0
    for y in range(gh):
        ratio = y / gh
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        d.line([(gx0, gy0 + y), (gx1, gy0 + y)], fill=(r, g, b))
    d.rectangle([gx0, gy0, gx1, gy1], outline="#d1d5db", width=3)
    d.rectangle([90, 1920, 1090, 1945], fill="#7c3f1d")
    d.rectangle([160, 1915, 195, 1925], fill="#ffffff")
    d.rectangle([210, 1915, 245, 1925], fill="#fde047")
    d.rectangle([260, 1915, 295, 1925], fill="#67e8f9")
    board.save("chalkboard.png")

    def draw_character(mouth_open=False, is_pointing=False):
        img = Image.new("RGBA", (450, 480), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        if is_pointing:
            dr.line([(180, 320), (60, 160)], fill="#1d4ed8", width=26)
            dr.ellipse([(45, 140), (75, 170)], fill="#fed7aa")
            dr.line([(60, 150), (40, 120)], fill="#fed7aa", width=8)
        dr.rectangle([170, 290, 330, 480], fill="#1d4ed8")
        dr.polygon([(250, 290), (230, 350), (250, 410), (270, 350)], fill="#b91c1c")
        dr.ellipse([180, 120, 320, 275], fill="#fed7aa")
        dr.chord([180, 100, 320, 200], 180, 360, fill="#3b2219")
        dr.rectangle([195, 165, 240, 195], outline="#0f172a", width=4)
        dr.rectangle([260, 165, 305, 195], outline="#0f172a", width=4)
        dr.line([240, 180, 260, 180], fill="#0f172a", width=4)
        dr.ellipse([212, 175, 222, 185], fill="#0f172a")
        dr.ellipse([277, 175, 287, 185], fill="#0f172a")
        if mouth_open:
            dr.ellipse([235, 225, 265, 250], fill="#881337")
        else:
            dr.line([235, 235, 265, 235], fill="#881337", width=4)
        return img

    draw_character(mouth_open=False, is_pointing=False).save("t_idle_closed.png")
    draw_character(mouth_open=True, is_pointing=False).save("t_idle_open.png")
    draw_character(mouth_open=False, is_pointing=True).save("t_point_closed.png")
    draw_character(mouth_open=True, is_pointing=True).save("t_point_open.png")

    effect = data.get("effect_type", "shock")
    stk = Image.new("RGBA", (520, 160), (0, 0, 0, 0))
    d_stk = ImageDraw.Draw(stk)
    bg_col = "#dc2626" if effect == "shock" else "#059669"
    d_stk.rounded_rectangle([18, 18, 508, 148], radius=22, fill=(15, 23, 42, 150))
    d_stk.rounded_rectangle([10, 10, 500, 140], radius=22, fill=bg_col, outline="#ffffff", width=4)
    stk.save("sticker_active.png")

    tile_w, h = 1080, 1920
    tile = Image.new("RGBA", (tile_w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(tile)
    random.seed(int(LESSON_NUM) if str(LESSON_NUM).isdigit() else 1)
    for _ in range(50):
        x = random.randint(0, tile_w)
        y = random.randint(0, h)
        r = random.randint(1, 3)
        a = random.randint(20, 65)
        dr.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    dust = Image.new("RGBA", (tile_w * 2, h), (0, 0, 0, 0))
    dust.paste(tile, (0, 0))
    dust.paste(tile, (tile_w, 0))
    dust.save("dust.png")

# ============================================================
# 7. Gemini Structured Prompt (Section-Locked)
# ============================================================
def generate_lesson_content():
    print("⏳ Generating structured lesson plan from Gemini...")
    prompt = f"""
    You are an elite, high-energy viral math educator on TikTok and Shorts.
    Create a 30-second math hack for: {SERIES_NAME} - Episode {LESSON_NUM}.

    CRITICAL RULES:
    1. Separate the voiceover into 4 distinct speaking parts corresponding exactly to visual steps.
    2. spoken_hook must introduce the trick enthusiastically (18-25 words).
    3. spoken_step1 must explain step 1 clearly (20-25 words).
    4. spoken_step2 must explain step 2 calculation (20-25 words).
    5. spoken_result must deliver the final answer and wrap up (15-20 words).
    6. Write plain conversational English words (no math symbols like ^, $, sqrt).

    Output ONLY valid JSON with EXACTLY this structure:
    {{
      "title": "Viral Math Trick Title with Emojis",
      "description": "Shorts description with hashtags #math #shorts",
      "tags": "math hacks, algebra, quick tips, shorts",
      "hook_text": "Multiply Any 2-Digit Number by 11",
      "spoken_hook": "Can you multiply forty-three by eleven in three seconds? Here is the secret trick you were never taught in school!",
      "step_1": "1. Split the digits: 4 and 3",
      "spoken_step1": "Step one. Just take the number forty-three, and separate the four and the three with a space in the middle.",
      "step_2": "2. Add digits: 4 + 3 = 7",
      "spoken_step2": "Step two. Add those two digits together. Four plus three equals seven. Place that seven right in between!",
      "result_text": "Final Answer: 473 🎉",
      "spoken_result": "And boom, your final answer is four hundred and seventy-three! Share this with your friends and follow for more hacks!",
      "joke_text": "Math Wizard! 🧙‍♂️",
      "effect_type": "shock"
    }}
    """
    models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.7}
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                raw_text = json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                return json.loads(raw_text.strip())
        except Exception:
            continue
    raise RuntimeError("Failed to generate content from Gemini.")

# ============================================================
# 8. Section-by-Section Audio Synthesis & Perfect Sync Engine
# ============================================================
async def synthesize_chunk(text, voice, out_file):
    clean = re.sub(r'["\'`*_~<>{}[\]\\/+=^$]', ' ', str(text))
    clean = " ".join(clean.split()).strip()
    words = []
    try:
        comm = edge_tts.Communicate(clean, voice)
        with open(out_file, "wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    words.append({
                        "start": chunk["offset"] / 10_000_000.0,
                        "end": (chunk["offset"] + chunk["duration"]) / 10_000_000.0,
                        "word": chunk["text"]
                    })
    except Exception as e:
        print(f"⚠️ Falling back to gTTS for chunk: {e}")
        tts = gTTS(text=clean, lang="en")
        tts.save(out_file)
    dur = get_audio_duration(out_file)
    return words, dur, clean

async def build_synchronized_audio(data):
    print("🎙️ Synthesizing section audio and calculating precise timestamps...")
    voices = ["en-US-ChristopherNeural", "en-US-GuyNeural"]
    chosen_voice = voices[int(LESSON_NUM) % len(voices) if str(LESSON_NUM).isdigit() else 0]

    sections = [
        ("hook", data.get("spoken_hook", "")),
        ("step1", data.get("spoken_step1", "")),
        ("step2", data.get("spoken_step2", "")),
        ("result", data.get("spoken_result", ""))
    ]

    all_words = []
    timestamps = {}
    current_time = 0.4  # Initial breathing space
    input_files = []

    for key, script in sections:
        file_name = f"{key}.mp3"
        words, dur, clean_txt = await synthesize_chunk(script, chosen_voice, file_name)
        input_files.append(file_name)

        timestamps[key] = round(current_time, 2)
        if words:
            for w in words:
                all_words.append({
                    "start": round(w["start"] + current_time, 2),
                    "end": round(w["end"] + current_time, 2),
                    "word": w["word"]
                })
        else:
            w_list = clean_txt.split()
            step_dur = dur / max(1, len(w_list))
            for idx, wrd in enumerate(w_list):
                all_words.append({
                    "start": round(current_time + (idx * step_dur), 2),
                    "end": round(current_time + ((idx + 1) * step_dur), 2),
                    "word": wrd
                })

        current_time += dur + 0.3  # Add natural 0.3s inter-step pause

    # Merge audio files seamlessly with FFmpeg concat filter
    filter_inputs = "".join([f"[{i}:a]" for i in range(len(input_files))])
    concat_cmd = (
        f'ffmpeg -y '
        f'-i hook.mp3 -i step1.mp3 -i step2.mp3 -i result.mp3 '
        f'-filter_complex "{filter_inputs}concat=n=4:v=0:a=1[outa]" '
        f'-c:a libmp3lame -q:a 2 voice.mp3'
    )
    subprocess.run(concat_cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    total_dur = get_audio_duration("voice.mp3") + 0.5
    timestamps["total"] = round(total_dur, 2)

    print(f"✓ Timestamps locked: Hook={timestamps['hook']}s, Step1={timestamps['step1']}s, Step2={timestamps['step2']}s, Result={timestamps['result']}s")
    return timestamps, all_words

# ============================================================
# 9. ASS Subtitles & Screen Overlay (HarfBuzz Locked)
# ============================================================
def escape_ass(text):
    if not text:
        return ""
    return str(text).replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ").strip()

def generate_master_ass(data, timestamps, words_data):
    print("📝 Building frame-accurate ASS subtitle script...")
    def to_ass_time(sec):
        sec = max(0.0, float(sec))
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        cs = int(round((sec - int(sec)) * 100))
        if cs >= 100:
            s += 1
            cs = 0
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    t_hook = timestamps["hook"]
    t_s1 = timestamps["step1"]
    t_s2 = timestamps["step2"]
    t_res = timestamps["result"]
    dur_str = to_ass_time(timestamps["total"])

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{FONT_NAME},46,&H008AE0FE,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,2,8,40,40,150,1
Style: Hook,{FONT_NAME},48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,3,8,40,40,360,1
Style: Step1,{FONT_NAME},44,&H008AE0FE,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,3,8,40,40,540,1
Style: Step2,{FONT_NAME},44,&H00F9E867,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,3,8,40,40,720,1
Style: Result,{FONT_NAME},52,&H00ACF686,&H000000FF,&H00064E3B,&H00064E3B,-1,0,0,0,100,100,0,0,3,18,0,8,40,40,920,1
Style: Joke,{FONT_NAME},30,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,2,5,40,40,0,1
Style: Captions,{FONT_NAME},36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,40,40,150,1
Style: Watermark,{FONT_NAME},24,&H80FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,50,40,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    bounce = r"\t(0,140,\fscx110\fscy110)\t(140,280,\fscx100\fscy100)"

    # Static Headers
    events.append(f"Dialogue: 0,{to_ass_time(0.0)},{dur_str},Title,,0,0,0,,{escape_ass(SERIES_NAME)}")
    events.append(f"Dialogue: 0,{to_ass_time(0.0)},{dur_str},Watermark,,0,0,0,,{escape_ass(SERIES_NAME)}")

    # Visual Cards synched strictly to audio starts
    events.append(f"Dialogue: 1,{to_ass_time(t_hook)},{dur_str},Hook,,0,0,0,,{{\\fad(280,0){bounce}}}{escape_ass(data.get('hook_text',''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_s1)},{dur_str},Step1,,0,0,0,,{{\\fad(280,0){bounce}}}{escape_ass(data.get('step_1',''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_s2)},{dur_str},Step2,,0,0,0,,{{\\fad(280,0){bounce}}}{escape_ass(data.get('step_2',''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_res)},{dur_str},Result,,0,0,0,,{{\\fad(280,0){bounce}}}{escape_ass(data.get('result_text',''))}")

    # Sticker appears right when result is announced
    events.append(f"Dialogue: 2,{to_ass_time(t_res)},{to_ass_time(t_res + 2.5)},Joke,,0,0,0,,{{\\an5\\pos(340,1200)\\fad(180,180)}}{escape_ass(data.get('joke_text','Math Magic! 🚀'))}")

    # Captions chunked into 2-3 words for high energy and exact sync
    chunk_size = 3
    for i in range(0, len(words_data), chunk_size):
        chunk = words_data[i:i + chunk_size]
        s_t = to_ass_time(chunk[0]["start"])
        e_t = to_ass_time(chunk[-1]["end"] + 0.1)
        txt = escape_ass(" ".join(w["word"] for w in chunk))
        if txt:
            events.append(f"Dialogue: 3,{s_t},{e_t},Captions,,0,0,0,,{txt}")

    with open("master_video.ass", "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))

# ============================================================
# 10. Motion FFmpeg Render
# ============================================================
def build_video_with_ffmpeg(data, timestamps):
    duration = timestamps["total"]
    print(f"⏳ Rendering synchronized video via FFmpeg (Duration: {duration:.2f}s)...")
    sfx_file = "boom.wav" if data.get("effect_type") == "shock" else "ding.wav"

    t_s1 = timestamps["step1"]
    t_s2 = timestamps["step2"]
    t_res = timestamps["result"]
    sfx_delay_ms = int(t_res * 1000)

    # Teacher points exclusively while explaining Step 1 & Step 2
    is_pointing = f"(between(t,{t_s1},{t_s2}) + between(t,{t_s2},{t_res}))"
    is_talking = "between(mod(t,0.28),0,0.14)"

    cond_idle_open = f"(not({is_pointing})) * ({is_talking})"
    cond_point_closed = f"({is_pointing}) * (not({is_talking}))"
    cond_point_open = f"({is_pointing}) * ({is_talking})"

    pan_x = f"max(0,min(70,(50)*(t/{duration:.2f})+2*sin(2*PI*t*1.2)))"
    pan_y = f"max(0,min(90,(70)*(t/{duration:.2f})+2*sin(2*PI*t*0.8+1)))"
    stk_fade = f"[6:v]fade=t=in:st={t_res}:d=0.2:alpha=1[stk_f]"

    vf = (
        f"[0:v]crop=w=1080:h=1920:x='{pan_x}':y='{pan_y}'[bg];"
        "[bg][2:v]overlay=x=630:y=1340[t_base];"
        f"[t_base][3:v]overlay=x=630:y=1340:enable='{cond_idle_open}'[t_id_op];"
        f"[t_id_op][4:v]overlay=x=630:y=1340:enable='{cond_point_closed}'[t_pt_cl];"
        f"[t_pt_cl][5:v]overlay=x=630:y=1340:enable='{cond_point_open}'[v_teacher];"
        f"{stk_fade};"
        f"[v_teacher][stk_f]overlay=x=80:y=1120:enable='between(t,{t_res},{t_res+2.5})'[v_stk];"
        f"[v_stk][7:v]overlay=x='-mod(t*16,1080)':y=0:format=auto[v_dust];"
        "[v_dust]eq=contrast=1.04:saturation=1.10,"
        f"drawbox=x=80:y=1800:w=(iw-160)*t/{duration:.2f}:h=8:color=#facc15:t=fill,"
        "subtitles=master_video.ass:fontsdir=fonts[outv]"
    )

    af = (
        f"[9:a]volume=0.09[bgm_soft]; "
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
        f'-map "[outv]" -map "[outa]" -c:v libx264 -preset ultrafast -crf 22 -c:a aac -t {duration:.2f} final_video.mp4'
    )
    subprocess.run(cmd, shell=True, check=True)
    subprocess.run(f'ffmpeg -y -ss {min(2.0, duration/3):.2f} -i final_video.mp4 -vframes 1 -q:v 2 thumbnail.jpg', shell=True)
    print("✓ Video production completed with frame-accurate audio sync!")

# ============================================================
# 11. Pipeline Entrypoint
# ============================================================
async def main():
    ensure_fonts()
    generate_sfx()
    data = generate_lesson_content()
    generate_graphics(data)

    txt_filename = f"details_en_lesson_{LESSON_NUM}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"Title:\n{data.get('title', '')}\n\nDescription:\n{data.get('description', '')}\n\nTags:\n{data.get('tags', '')}\n")

    timestamps, words_data = await build_synchronized_audio(data)
    generate_master_ass(data, timestamps, words_data)
    generate_ambient_bgm(timestamps["total"] + 2)
    build_video_with_ffmpeg(data, timestamps)
    print("🎉 Pipeline run successfully finished!")

if __name__ == "__main__":
    asyncio.run(main())
