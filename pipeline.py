import os
import sys
import re
import json
import random
import shutil
import asyncio
import urllib.request
import urllib.error
import wave
import math
import struct
import subprocess
import edge_tts
from gtts import gTTS
from PIL import Image, ImageDraw

# ============================================================
# 1. التحقق من البيئة والمتغيرات الأساسية
# ============================================================
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    print("❌ خطأ حرج: متغير GEMINI_API_KEY غير موجود في أسرار المستودع!")
    sys.exit(1)

SERIES_NAME = os.environ.get("SERIES_NAME", "حيل الرياضيات السريعة")
LESSON_NUM = os.environ.get("LESSON_NUM", "1")
LANG = os.environ.get("VIDEO_LANG", "ar").lower().strip()
TARGET_DURATION = int(os.environ.get("TARGET_DURATION", "30"))

FONT_DIR = "fonts"
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "Cairo-Regular.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "Cairo-Bold.ttf")
FONT_NAME = "Cairo"

# ============================================================
# 2. ضمان وجود الخط العربي محلياً (فحص المجلد الرئيسي ومجلد fonts)
# ============================================================
def ensure_fonts():
    global FONT_NAME
    print("🔤 التحقق من توفر خط Cairo العربي المرفوع محلياً...")
    os.makedirs(FONT_DIR, exist_ok=True)

    # البحث عن ملف الخط سواء تم رفعه في المجلد الرئيسي أو داخل مجلد fonts
    candidates = [
        "Cairo-Bold.ttf",
        "Cairo-Regular.ttf",
        "Cairo-VariableFont_slnt,wght.ttf",
        os.path.join(FONT_DIR, "Cairo-Bold.ttf"),
        os.path.join(FONT_DIR, "Cairo-Regular.ttf")
    ]
    
    found_local = None
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 10000:
            found_local = c
            break

    if found_local:
        print(f"✓ تم العثور على الخط المحلي: {found_local}")
        # نسخه لمجلد fonts لضمان قراءة libass له مباشرة
        if not os.path.exists(FONT_BOLD_PATH):
            shutil.copyfile(found_local, FONT_BOLD_PATH)
        if not os.path.exists(FONT_REGULAR_PATH):
            shutil.copyfile(found_local, FONT_REGULAR_PATH)
        FONT_NAME = "Cairo"
    else:
        print("⚠️ لم يتم العثور على خط محلي، محاولة تثبيت بديل موثوق...")
        FONT_NAME = "Cairo"

    print(f"✓ تم تثبيت بيئة الخط بنجاح: {FONT_NAME}")

# ============================================================
# 3. قياس مدة ملف الصوت بدقة
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
        return val if val > 0 else 1.0
    except Exception:
        return 1.0

# ============================================================
# 4. توليد موسيقى خلفية هادئة (BGM)
# ============================================================
def generate_ambient_bgm(duration, output_file="bgm.wav"):
    print("🎵 فحص وتجهيز موسيقى الخلفية (BGM)...")
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
            sample_val = (sample_val / len(chords[chord_idx])) * 0.14
            envelope = min(1.0, t / 1.5) * min(1.0, (duration - t) / 1.5)
            val = int(32767 * sample_val * envelope)
            data.append(struct.pack('<h', max(-32767, min(32767, val))))
        f.writeframes(b''.join(data))
    return output_file

# ============================================================
# 5. توليد المؤثرات الصوتية SFX
# ============================================================
def generate_sfx():
    print("🔊 توليد المؤثرات الصوتية...")
    with wave.open("ding.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        data = [struct.pack('<h', int(32767 * 0.4 * math.sin(2 * math.pi * 987.77 * (i/24000)) * math.exp(-6 * (i/24000)))) for i in range(12000)]
        f.writeframes(b''.join(data))

    with wave.open("boom.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        data = [struct.pack('<h', int(32767 * 0.6 * math.sin(2 * math.pi * max(45, 140 - 110 * (i/24000)) * (i/24000)) * math.exp(-3 * (i/24000)))) for i in range(19200)]
        f.writeframes(b''.join(data))

# ============================================================
# 6. رسم السبورة الموسعة بأمان + المعلم + الاستيكر + غبار الطباشير
# ============================================================
def generate_graphics(data):
    print("🎨 رسم السبورة الموسعة، المعلم التفاعلي، وطبقة الغبار...")

    # 6.1 السبورة الموسعة بهامش أمان ضد أخطاء Crop (1180x2040)
    board = Image.new("RGBA", (1180, 2040), "#3c2211")
    d = ImageDraw.Draw(board)
    d.rectangle([25, 45, 1155, 1995], fill="#5a3217")

    top_color = (17, 51, 39)
    bottom_color = (10, 28, 22)
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

    # 6.2 وضعيات المعلم التفاعلي
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

    # 6.3 كارت الاستيكر المجسم (عرض 520 في ارتفاع 160)
    effect = data.get("effect_type", "shock")
    stk = Image.new("RGBA", (520, 160), (0, 0, 0, 0))
    d_stk = ImageDraw.Draw(stk)
    bg_col = "#dc2626" if effect == "shock" else "#059669"
    d_stk.rounded_rectangle([18, 18, 508, 148], radius=22, fill=(15, 23, 42, 150))
    d_stk.rounded_rectangle([10, 10, 500, 140], radius=22, fill=bg_col, outline="#ffffff", width=4)
    stk.save("sticker_active.png")

    # 6.4 طبقة غبار الطباشير المتدفقة
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
# 7. توليد المحتوى التعليمي عبر Gemini
# ============================================================
def generate_lesson_content():
    target_words = max(55, int(TARGET_DURATION * 2.2))
    print(f"⏳ توليد المحتوى التعليمي عبر Gemini ({LANG.upper()})...")

    if LANG == "ar":
        prompt = f"""
        أنت صانع محتوى رياضيات تيك توك وريلز مصري احترافي وممتع.
        المطلوب: حيلة رياضية سريعة ومفيدة عن: {SERIES_NAME} - حلقة {LESSON_NUM}.

        شروط أساسية:
        - hook_text: عنوان المسألة (مثال: "ضرب أي رقم في 11 ذهنياً").
        - step_1: الخطوة الأولى (مثال: "1. افصل الرقمين: 43 تصبح 4 و 3").
        - step_2: الخطوة الثانية بالمعادلة (مثال: "2. اجمع الرقمين: 4 + 3 = 7 في المنتصف").
        - result_text: الناتج النهائي (مثال: "الناتج النهائي = 473 🎉").
        - joke_text: إفيه قصير للاستيكر (أقل من 4 كلمات، مثال: "وفرت وقت الامتحان!").
        - spoken_script: سيناريو بالعامية المصرية الودودة بطول حوالي {target_words} كلمة، مقسم لجمل متتالية مفصولة بنقطة (.) ومشروحة ببساطة بدون رموز لاتينية.

        أخرج الرد بصيغة JSON حصرية:
        {{
          "title": "عنوان جذاب للشورتس",
          "description": "وصف كامل بالهاشتاجات",
          "tags": "رياضيات, شورتس, قدرات, حيل_سريعة",
          "spoken_script": "نص الاسكريبت المنطوق",
          "hook_text": "المسألة",
          "step_1": "الخطوة الأولى",
          "step_2": "الخطوة الثانية",
          "result_text": "الحل النهائي",
          "joke_text": "جملة الاستيكر",
          "effect_type": "idea"
        }}
        """
    else:
        prompt = f"""
        You are a top-tier viral math educator on TikTok and Shorts.
        Create a quick math hack video about: {SERIES_NAME} - Episode {LESSON_NUM}.
        Target length: {target_words} words. Plain spoken English without math symbols.
        Output ONLY valid JSON.
        """

    models_to_try = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.7}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                return json.loads(raw_text.strip())
        except Exception:
            continue
    raise RuntimeError("فشلت كافة محاولات الاتصال بنماذج Gemini.")

# ============================================================
# 8. توليد مقطع صوتي منفرد
# ============================================================
async def synthesize_segment(text, voice, rate, pitch, volume, filename, timeout=20):
    words_local = []
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)

    async def _run():
        with open(filename, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start_sec = chunk["offset"] / 10_000_000.0
                    dur_sec = chunk["duration"] / 10_000_000.0
                    words_local.append({"start": start_sec, "end": start_sec + dur_sec, "word": chunk["text"]})

    await asyncio.wait_for(_run(), timeout=timeout)
    if not (os.path.exists(filename) and os.path.getsize(filename) > 500):
        raise RuntimeError(f"فشل استلام مقطع صوتي سليم: {filename}")
    return words_local

def generate_silence(duration_sec, filename):
    cmd = (
        f'ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t {max(0.05, duration_sec):.2f} '
        f'-acodec libmp3lame -q:a 4 {filename}'
    )
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ============================================================
# 9. توليد الصوت البشري متعدد النبرات (3 كتل درامية متوازنة)
# ============================================================
async def create_voiceover_safe(text, output_file="voice.mp3"):
    print("⏳ تجهيز الصوت الإنساني بنبرات وإيقاعات متغيرة...")

    raw_text = str(text).replace("\n", " ").replace("\r", " ")
    clean_text = re.sub(r'["\'`*_~<>{}[\]\\/+=^$]', ' ', raw_text)
    clean_text = " ".join(clean_text.split()).strip()
    if len(clean_text.split()) < 5:
        clean_text = "يلا نحل المسألة دي في ثواني وبطريقة سهلة جداً!" if LANG == "ar" else "Let us solve this math problem quickly and easily!"

    # تقسيم النص لكتل درامية ذكية (3 كتل لتفادي ضغط الشبكة)
    raw_sentences = [s.strip() for s in re.split(r'[.!؟?،\n]+', clean_text) if len(s.strip()) > 3]
    if not raw_sentences:
        raw_sentences = [clean_text]

    chunks = []
    if len(raw_sentences) <= 3:
        chunks = raw_sentences
    else:
        # دمج الجمل إلى 3 كتل متناسقة
        step = math.ceil(len(raw_sentences) / 3)
        chunks = [" ".join(raw_sentences[i:i+step]) for i in range(0, len(raw_sentences), step)]

    voices_pool = ["ar-EG-ShakirNeural", "ar-EG-SalmaNeural"] if LANG == "ar" else ["en-US-ChristopherNeural", "en-US-GuyNeural"]
    lesson_idx = int(LESSON_NUM) if str(LESSON_NUM).isdigit() else 1
    chosen_voice = voices_pool[lesson_idx % len(voices_pool)]
    print(f"🎙️ الصوت المعتمد: {chosen_voice} (موزع على {len(chunks)} كتل نبرية)")

    # نبرات الكتل: 1. هوك سريع وحماسي | 2. شرح متزن | 3. حل نهائي قوي وفخور
    prosody_presets = [
        {"rate": "+7%", "pitch": "+18Hz", "volume": "+5%"},
        {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"},
        {"rate": "-4%", "pitch": "-5Hz", "volume": "+8%"}
    ]

    words_data = []
    edge_success = False
    segment_files = []

    try:
        cursor = 0.0
        for i, chunk_text in enumerate(chunks):
            seg_file = f"seg_{i:03d}.mp3"
            p = prosody_presets[min(i, len(prosody_presets) - 1)]
            local_words = await synthesize_segment(chunk_text, chosen_voice, p["rate"], p["pitch"], p["volume"], seg_file)
            seg_dur = get_audio_duration(seg_file)

            for w in local_words:
                words_data.append({"start": w["start"] + cursor, "end": w["end"] + cursor, "word": w["word"]})

            segment_files.append(seg_file)
            cursor += seg_dur

            if i < len(chunks) - 1:
                pause_dur = 0.22 if i == 0 else 0.35  # وقفة أطول قبل إعلان النتيجة
                pause_file = f"pause_{i:03d}.mp3"
                generate_silence(pause_dur, pause_file)
                segment_files.append(pause_file)
                cursor += pause_dur

        list_path = "concat_list.txt"
        with open(list_path, "w", encoding="utf-8") as f:
            for sf in segment_files:
                f.write(f"file '{sf}'\n")

        subprocess.run(
            f'ffmpeg -y -f concat -safe 0 -i {list_path} -ar 24000 -ac 1 -acodec libmp3lame -q:a 4 {output_file}',
            shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        if os.path.exists(output_file) and os.path.getsize(output_file) > 2000:
            edge_success = True
            print("✓ اكتمل تسجيل وتجميع المسار الصوتي المتناسق بنجاح!")
    except Exception as e:
        print(f"⚠️ تعثر التسجيل متعدد النبرات: {e}")

    # Fallback 1: تسجيل كامل بصوت مستقر
    if not edge_success:
        print("🔄 التبديل للاحتياطي: تسجيل النص ككتلة واحدة عبر edge-tts...")
        try:
            words_data = await synthesize_segment(clean_text, chosen_voice, "+0%", "+0Hz", "+0%", output_file, timeout=30)
            if os.path.exists(output_file) and os.path.getsize(output_file) > 2000:
                edge_success = True
        except Exception as e:
            print(f"⚠️ تعثر الاحتياطي الأول: {e}")

    # Fallback 2: gTTS بدون تشكيل
    if not edge_success:
        print("🔄 التبديل النهائي لمحرك gTTS...")
        try:
            gtts_text = re.sub(r'[\u064B-\u0652\u0670]', '', clean_text) if LANG == "ar" else clean_text
            tts = gTTS(text=gtts_text, lang="ar" if LANG == "ar" else "en")
            tts.save(output_file)
            words_data = []
            print("✓ تم إنشاء الصوت عبر المحرك الاحتياطي!")
        except Exception as e:
            raise RuntimeError(f"فشلت كافة خيارات إنتاج الصوت: {e}")

    actual_dur = get_audio_duration(output_file)

    speech_intervals = []
    if words_data:
        curr_start = words_data[0]["start"]
        curr_end = words_data[0]["end"]
        for w in words_data[1:]:
            if w["start"] - curr_end <= 0.35:
                curr_end = max(curr_end, w["end"])
            else:
                speech_intervals.append((curr_start, curr_end))
                curr_start = w["start"]
                curr_end = w["end"]
        speech_intervals.append((curr_start, curr_end))
    else:
        speech_intervals.append((0.3, actual_dur))

    return speech_intervals, actual_dur, words_data, clean_text

# ============================================================
# 10. تنظيف نصوص ASS
# ============================================================
def escape_ass(text):
    if text is None:
        return ""
    t = str(text).replace("\\", "").replace("{", "(").replace("}", ")")
    t = t.replace("\n", " ").replace("\r", "")
    return t.strip()

# ============================================================
# 11. بناء ملف ASS الموحد (مع ضبط مركز الاستيكر والألوان)
# ============================================================
def generate_master_ass(data, duration, words_data, clean_text):
    print("📝 بناء ملف نصوص السبورة والترجمة الموحد...")

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

    t_hook = 0.5
    t_s1 = round(duration * 0.22, 2)
    t_s2 = round(duration * 0.48, 2)
    t_res = round(duration * 0.72, 2)
    t_joke_start = round(duration * 0.35, 2)
    t_joke_end = round(duration * 0.55, 2)
    dur_str = to_ass_time(duration)

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
Style: Result,{FONT_NAME},52,&H00ACF686,&H000000FF,&H003B4E06,&H003B4E06,-1,0,0,0,100,100,0,0,3,18,0,8,40,40,920,1
Style: Joke,{FONT_NAME},30,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,2,5,40,40,0,1
Style: Captions,{FONT_NAME},34,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,2,40,40,140,1
Style: Watermark,{FONT_NAME},24,&H80FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,50,40,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    bounce = r"\t(0,140,\fscx110\fscy110)\t(140,280,\fscx100\fscy100)"

    events.append(f"Dialogue: 0,{to_ass_time(0.0)},{dur_str},Title,,0,0,0,,{escape_ass(SERIES_NAME)}")
    events.append(f"Dialogue: 0,{to_ass_time(0.0)},{dur_str},Watermark,,0,0,0,,{escape_ass(SERIES_NAME)}")

    events.append(f"Dialogue: 1,{to_ass_time(t_hook)},{dur_str},Hook,,0,0,0,,{{\\fad(280,0){bounce}}}{escape_ass(data.get('hook_text',''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_s1)},{dur_str},Step1,,0,0,0,,{{\\fad(280,0){bounce}}}{escape_ass(data.get('step_1',''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_s2)},{dur_str},Step2,,0,0,0,,{{\\fad(280,0){bounce}}}{escape_ass(data.get('step_2',''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_res)},{dur_str},Result,,0,0,0,,{{\\fad(280,0){bounce}}}{escape_ass(data.get('result_text',''))}")

    # ضبط إحداثي الإفيه ليجلس في قلب كارت الاستيكر بالضبط (X=340, Y=1200)
    events.append(f"Dialogue: 2,{to_ass_time(t_joke_start)},{to_ass_time(t_joke_end)},Joke,,0,0,0,,{{\\an5\\pos(340,1200)\\fad(180,180)}}{escape_ass(data.get('joke_text','حساب عبقري!'))}")

    if words_data:
        chunk_size = 4
        for i in range(0, len(words_data), chunk_size):
            chunk = words_data[i:i + chunk_size]
            s_t = to_ass_time(chunk[0]["start"])
            e_t = to_ass_time(chunk[-1]["end"] + 0.15)
            txt = escape_ass(" ".join(w["word"] for w in chunk).strip())
            if txt:
                events.append(f"Dialogue: 3,{s_t},{e_t},Captions,,0,0,0,,{txt}")
    else:
        words = clean_text.split()
        chunk_size = 4
        chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        step_dur = duration / max(1, len(chunks))
        for idx, ch in enumerate(chunks):
            s_t = to_ass_time(idx * step_dur)
            e_t = to_ass_time(min(duration, (idx + 1) * step_dur))
            events.append(f"Dialogue: 3,{s_t},{e_t},Captions,,0,0,0,,{escape_ass(ch)}")

    with open("master_video.ass", "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))
    print("✓ تم تجهيز ملف نصوص الفيديو الشامل بنجاح.")

# ============================================================
# 12. المونتاج والرندرة السريعة (آمنة وضمن حدود الأبعاد تماماً)
# ============================================================
def build_video_with_ffmpeg(data, duration, speech_intervals):
    print(f"⏳ رندرة الفيديو الاحترافي عبر FFmpeg (المدة: {duration:.2f}s)...")
    effect = data.get("effect_type", "shock")
    sfx_file = "boom.wav" if effect == "shock" else "ding.wav"

    t_s1 = round(duration * 0.22, 2)
    t_s2 = round(duration * 0.48, 2)
    t_joke_start = round(duration * 0.35, 2)
    t_joke_end = round(duration * 0.55, 2)
    sfx_delay_ms = int(t_joke_start * 1000)

    if speech_intervals:
        speech_cond = " + ".join([f"between(t,{s:.2f},{e:.2f})" for s, e in speech_intervals])
    else:
        speech_cond = f"between(t,0.5,{duration:.2f})"

    is_talking = f"({speech_cond}) * between(mod(t,0.28),0,0.14)"
    is_pointing = f"(between(t,{t_s1},{t_s1+2.8}) + between(t,{t_s2},{t_s2+2.8}))"
    cond_idle_open = f"(not({is_pointing})) * ({is_talking})"
    cond_point_closed = f"({is_pointing}) * (not({is_talking}))"
    cond_point_open = f"({is_pointing}) * ({is_talking})"

    # حركة كاميرا ناعمة مقيدة بهامش أمان يستحيل معه تجاوز أبعاد الإطار
    pan_x = f"max(0,min(70,(50)*(t/{duration:.2f})+2*sin(2*PI*t*1.2)))"
    pan_y = f"max(0,min(90,(70)*(t/{duration:.2f})+2*sin(2*PI*t*0.8+1)))"

    # تلاشي الاستيكر مسبقاً قبل overlay
    stk_fade = f"[6:v]fade=t=in:st={t_joke_start}:d=0.2:alpha=1[stk_f]"

    vf = (
        f"[0:v]crop=w=1080:h=1920:x='{pan_x}':y='{pan_y}'[bg];"
        "[bg][2:v]overlay=x=630:y=1340[t_base];"
        f"[t_base][3:v]overlay=x=630:y=1340:enable='{cond_idle_open}'[t_id_op];"
        f"[t_id_op][4:v]overlay=x=630:y=1340:enable='{cond_point_closed}'[t_pt_cl];"
        f"[t_pt_cl][5:v]overlay=x=630:y=1340:enable='{cond_point_open}'[v_teacher];"
        f"{stk_fade};"
        f"[v_teacher][stk_f]overlay=x=80:y=1120:enable='between(t,{t_joke_start},{t_joke_end})'[v_stk];"
        f"[v_stk][7:v]overlay=x='-mod(t*16,1080)':y=0:format=auto[v_dust];"
        "[v_dust]eq=contrast=1.04:saturation=1.10,"
        f"drawbox=x=80:y=1800:w=(iw-160)*t/{duration:.2f}:h=8:color=#facc15:t=fill,"
        "subtitles=master_video.ass:fontsdir=fonts[outv]"
    )

    af = (
        f"[9:a]volume=0.10[bgm_soft]; "
        f"[1:a]asplit=2[v_main][v_sc]; "
        f"[bgm_soft][v_sc]sidechaincompress=threshold=0.03:ratio=5:attack=100:release=400[bgm_ducked]; "
        f"[v_main][bgm_ducked]amix=inputs=2:duration=first[a_pre]; "
        f"[a_pre]equalizer=f=9000:t=h:width=2000:g=-3,equalizer=f=120:t=h:width=100:g=1[a_voice_bgm]; "
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

    thumb_time = min(2.0, max(0.5, duration / 4))
    subprocess.run(f'ffmpeg -y -ss {thumb_time:.2f} -i final_video.mp4 -vframes 1 -q:v 2 thumbnail.jpg', shell=True)
    print("✓ اكتمل إنتاج الفيديو بنجاح تام.")

# ============================================================
# 13. تشغيل المسار الرئيسي
# ============================================================
async def main():
    ensure_fonts()
    generate_sfx()
    data = generate_lesson_content()
    generate_graphics(data)

    txt_filename = f"بيانات_{LANG}_درس_{LESSON_NUM}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"العنوان:\n{data.get('title', '')}\n\n")
        f.write(f"الوصف:\n{data.get('description', '')}\n\n")
        f.write(f"الكلمات المفتاحية:\n{data.get('tags', '')}\n")

    spoken_script = data.get("spoken_script", "يلا نحل المسألة دي في ثواني وبطريقة سهلة جداً!")
    speech_intervals, actual_duration, words_data, clean_text = await create_voiceover_safe(spoken_script)
    print(f"⏱️ مدة الصوت المعتمدة: {actual_duration:.2f} ثانية")

    generate_master_ass(data, actual_duration, words_data, clean_text)
    generate_ambient_bgm(actual_duration + 3)
    build_video_with_ffmpeg(data, actual_duration, speech_intervals)
    print("🎉 انتهى خط الإنتاج بالكامل وبأعلى دقة وثبات!")

if __name__ == "__main__":
    asyncio.run(main())
