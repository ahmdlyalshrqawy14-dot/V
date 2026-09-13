import os
import sys
import json
import asyncio
import urllib.request
import urllib.error
import wave
import math
import struct
import subprocess
import edge_tts
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

# 1. التحقق الصارم من البيئة والمدخلات
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    print("❌ خطأ حرج: متغير GEMINI_API_KEY غير موجود في أسرار المستودع (GitHub Secrets)!")
    sys.exit(1)

SERIES_NAME = os.environ.get("SERIES_NAME", "حيل الرياضيات السريعة")
LESSON_NUM = os.environ.get("LESSON_NUM", "1")
LANG = os.environ.get("VIDEO_LANG", "ar").lower().strip()
TARGET_DURATION = int(os.environ.get("TARGET_DURATION", "35"))

# 2. معالجة النصوص وتشكيل الخط العربي لمنع تقطيع الحروف
def shape_text(text):
    if not text:
        return ""
    if LANG == "ar":
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except Exception:
            return str(text)
    return str(text)

def get_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

# 3. حساب مدة الصوت بدقة
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
        return val if val > 0 else float(TARGET_DURATION)
    except Exception:
        return float(TARGET_DURATION)

# 4. توليد BGM هادئ متوافق مع المدة
def generate_ambient_bgm(duration, output_file="bgm.wav"):
    print("🎵 فحص وتجهيز موسيقى الخلفية الهادئة (BGM)...")
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
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        data = []
        chord_len = int(sample_rate * 3.5)
        for i in range(total_samples):
            t = i / sample_rate
            chord_idx = (i // chord_len) % len(chords)
            sample_val = sum(math.sin(2 * math.pi * freq * t) for freq in chords[chord_idx])
            sample_val = (sample_val / len(chords[chord_idx])) * 0.16
            envelope = min(1.0, t / 1.5) * min(1.0, (duration - t) / 1.5)
            val = int(32767 * sample_val * envelope)
            data.append(struct.pack('<h', max(-32767, min(32767, val))))
        f.writeframes(b''.join(data))
    return output_file

# 5. توليد المؤثرات الصوتية
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

# 6. رسم السبورة، المعلم، وبطاقات النصوص المعالجة باللغة العربية عبر Pillow
def generate_graphics_and_cards(data):
    print("🎨 رسم السبورة وبطاقات النصوص العربية المصححة عبر Pillow...")
    
    # 6.1 السبورة الخلفية
    board = Image.new("RGBA", (1080, 1920), "#452613")
    d = ImageDraw.Draw(board)
    d.rectangle([25, 45, 1055, 1875], fill="#693b1d")
    d.rectangle([55, 75, 1025, 1845], fill="#13382b", outline="#e5e7eb", width=3)
    d.rectangle([90, 1810, 990, 1835], fill="#854820")
    d.rectangle([150, 1805, 185, 1815], fill="#ffffff")
    d.rectangle([200, 1805, 235, 1815], fill="#fde047")
    d.rectangle([250, 1805, 285, 1815], fill="#67e8f9")
    
    # عنوان السلسلة في أعلى السبورة
    font_title = get_font(48)
    title_txt = shape_text(SERIES_NAME)
    d.text((540, 150), title_txt, font=font_title, fill="#fef08a", anchor="mm")
    board.save("chalkboard.png")

    # 6.2 المعلم الكرتوني
    def draw_teacher(mouth_open=False):
        img = Image.new("RGBA", (340, 420), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.rectangle([90, 250, 250, 420], fill="#1d4ed8")
        dr.polygon([(170, 250), (150, 310), (170, 370), (190, 310)], fill="#b91c1c")
        dr.ellipse([100, 80, 240, 235], fill="#fed7aa")
        dr.chord([100, 60, 240, 160], 180, 360, fill="#3b2219")
        dr.rectangle([115, 125, 160, 155], outline="#0f172a", width=4)
        dr.rectangle([180, 125, 225, 155], outline="#0f172a", width=4)
        dr.line([160, 140, 180, 140], fill="#0f172a", width=4)
        dr.ellipse([132, 135, 142, 145], fill="#0f172a")
        dr.ellipse([197, 135, 207, 145], fill="#0f172a")
        if mouth_open:
            dr.ellipse([155, 185, 185, 210], fill="#881337")
        else:
            dr.line([155, 195, 185, 195], fill="#881337", width=4)
        return img

    draw_teacher(mouth_open=False).save("teacher_closed.png")
    draw_teacher(mouth_open=True).save("teacher_open.png")

    # 6.3 بطاقات النصوص الشفافة (تمنع التقطيع وتمنع مشاكل الحروف تماماً)
    def make_text_overlay(text, font_size, fill_color, y_pos, filename, bg_box=False):
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        font = get_font(font_size)
        shaped = shape_text(text)
        
        if bg_box:
            bbox = dr.textbbox((540, y_pos), shaped, font=font, anchor="mm")
            pad = 20
            dr.rounded_rectangle([bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad], radius=15, fill="#064e3b", outline="#86efac", width=3)
            dr.text((540, y_pos), shaped, font=font, fill="#86efac", anchor="mm")
        else:
            dr.text((540, y_pos), shaped, font=font, fill=fill_color, anchor="mm")
        img.save(filename)

    make_text_overlay(data.get("hook_text", ""), 52, "#ffffff", 380, "card_hook.png")
    make_text_overlay(data.get("step_1", ""), 46, "#fef08a", 620, "card_step1.png")
    make_text_overlay(data.get("step_2", ""), 46, "#67e8f9", 840, "card_step2.png")
    make_text_overlay(data.get("result_text", ""), 56, "#86efac", 1060, "card_result.png", bg_box=True)

    # 6.4 الاستيكر مع الإفيه مكتوب بداخله بالعربي السليم
    effect = data.get("effect_type", "shock")
    stk = Image.new("RGBA", (500, 150), (0, 0, 0, 0))
    d_stk = ImageDraw.Draw(stk)
    bg_col = "#dc2626" if effect == "shock" else "#059669"
    d_stk.rounded_rectangle([10, 10, 490, 140], radius=20, fill=bg_col, outline="#ffffff", width=4)
    
    joke_txt = shape_text(data.get("joke_text", "انتظر المفاجأة!"))
    d_stk.text((250, 75), joke_txt, font=get_font(30), fill="#ffffff", anchor="mm")
    stk.save("sticker_active.png")

# 7. توليد المحتوى عبر Gemini مع احترام المدة المطلوبة
def generate_lesson_content():
    print(f"⏳ توليد المحتوى ليتناسب مع مدة {TARGET_DURATION} ثانية عبر Gemini ({LANG.upper()})...")
    
    # حساب عدد الكلمات المستهدف: بمعدل 2.2 كلمة لكل ثانية
    target_words = int(TARGET_DURATION * 2.2)
    
    if LANG == "ar":
        prompt = f"""
        أنت صانع محتوى رياضيات تيك توك وريلز مصري مضحك وسريع.
        المطلوب درس ترفيهي عن: {SERIES_NAME} - حلقة {LESSON_NUM}.
        
        المدة المستهدفة للفيديو: {TARGET_DURATION} ثانية بالضبط (حوالي {target_words} كلمة في الاسكريبت).
        
        الشروط:
        1. ابدأ بهوك صادم وفكاهي يسخر من صعوبة الطرق التقليدية.
        2. الإفيه قصير جداً (أقل من 5 كلمات) ليناسب الاستيكر.
        3. نصوص السبورة (الهوك، الخطوة 1، الخطوة 2، النتيجة) قصيرة جداً (أقل من 6 كلمات لكل منها).
        4. اختر effect_type إما "shock" أو "idea".
        
        أخرج الرد بصيغة JSON حصرية:
        {{
          "title": "عنوان جذاب مع إيموجي",
          "description": "وصف كامل بالهاشتاجات #رياضيات #شورتس",
          "tags": "رياضيات, قدرات, جبر, شورتس",
          "spoken_script": "نص الاسكريبت المنطوق بالعامية المصرية ومشكل بالحركات تماماً بطول حوالي {target_words} كلمة",
          "hook_text": "المسألة أو المعادلة الصادمة",
          "joke_text": "إفيه قصير للاستيكر",
          "step_1": "الحيلة الأولى",
          "step_2": "التطبيق الفوري",
          "result_text": "الحل النهائي في ثانية 🎉",
          "effect_type": "shock"
        }}
        """
    else:
        prompt = f"""
        You are a funny, high-energy viral math Shorts creator.
        Create an entertaining reel about: {SERIES_NAME} - Episode {LESSON_NUM}.
        Target Duration: {TARGET_DURATION} seconds (approx {target_words} words).
        All board texts must be concise (under 30 characters).
        
        Output ONLY valid JSON:
        {{
          "title": "Catchy Title with Emojis",
          "description": "Shorts description with hashtags",
          "tags": "math hacks, algebra, quick tips, shorts",
          "spoken_script": "Spoken script matching exactly {target_words} words. Humorous and fast.",
          "hook_text": "The Problem",
          "joke_text": "Short funny sticker caption",
          "step_1": "Step 1 Hack",
          "step_2": "Step 2 Hack",
          "result_text": "Final Answer 🎉",
          "effect_type": "idea"
        }}
        """

    models_to_try = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.8}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    last_error = None
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
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"فشلت المحاولات مع كافة النماذج: {last_error}")

# 8. توليد الصوت مع Timeout ومعالجة Fallback للكابشنز
async def create_voiceover_safe(text, output_file="voice.mp3"):
    print("⏳ تسجيل التعليق الصوتي واستخراج التوقيتات بأمان...")
    
    lesson_idx = int(LESSON_NUM) if str(LESSON_NUM).isdigit() else 1
    if LANG == "ar":
        voices = ["ar-EG-ShakirNeural", "ar-EG-SalmaNeural"]
    else:
        voices = ["en-US-ChristopherNeural", "en-US-JennyNeural", "en-US-GuyNeural"]
    chosen_voice = voices[lesson_idx % len(voices)]
    print(f"🎙️ الصوت المعتمد: {chosen_voice}")

    communicate = edge_tts.Communicate(text, chosen_voice)
    words_data = []

    async def _fetch():
        with open(output_file, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start_sec = chunk["offset"] / 10_000_000.0
                    dur_sec = chunk["duration"] / 10_000_000.0
                    words_data.append({
                        "start": start_sec,
                        "end": start_sec + dur_sec,
                        "word": chunk["text"]
                    })

    try:
        # مهلة زمنية 50 ثانية كحد أقصى لمنع التعليق
        await asyncio.wait_for(_fetch(), timeout=50)
    except asyncio.TimeoutError:
        raise RuntimeError("انتهت مهلة اتصال خدمة edge-tts دون استجابة!")

    # بناء الكابشنز
    def format_srt_time(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    srt_lines = []
    chunk_size = 4
    sub_idx = 1
    for i in range(0, len(words_data), chunk_size):
        chunk = words_data[i:i + chunk_size]
        start_ts = format_srt_time(chunk[0]["start"])
        end_ts = format_srt_time(chunk[-1]["end"] + 0.15)
        txt = " ".join(w["word"] for w in chunk).strip()
        if txt:
            srt_lines.append(f"{sub_idx}\n{start_ts} --> {end_ts}\n{txt}\n")
            sub_idx += 1

    with open("captions.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    # استخراج فترات الكلام لحركة الفم
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

    return speech_intervals

# 9. المونتاج والرندرة الكاملة عبر بطاقات الصور (خالي تماماً من مشاكل drawtext واللغة العربية)
def build_video_with_ffmpeg(data, duration, speech_intervals):
    print(f"⏳ رندرة الفيديو الاحترافي عبر FFmpeg (المدة: {duration:.2f}s)...")
    
    effect = data.get("effect_type", "shock")
    sfx_file = "boom.wav" if effect == "shock" else "ding.wav"

    t_hook = 0.5
    t_s1 = round(duration * 0.25, 2)
    t_s2 = round(duration * 0.52, 2)
    t_joke_start = round(duration * 0.35, 2)
    t_joke_end = round(duration * 0.50, 2)
    t_res = round(duration * 0.75, 2)
    sfx_delay_ms = int(t_joke_start * 1000)

    if speech_intervals:
        speech_cond = " + ".join([f"between(t,{s:.2f},{e:.2f})" for s, e in speech_intervals])
    else:
        speech_cond = f"between(t,0.5,{duration:.2f})"
    mouth_flap_expr = f"({speech_cond}) * between(mod(t,0.28),0,0.14)"

    # المدخلات (كل النصوص مجهزة مسبقاً كصور PNG شفافة عبر Pillow لضمان سلامة التشكيل العربي 100%):
    # 0: chalkboard.png
    # 1: voice.mp3
    # 2: teacher_closed.png
    # 3: teacher_open.png
    # 4: sticker_active.png
    # 5: card_hook.png
    # 6: card_step1.png
    # 7: card_step2.png
    # 8: card_result.png
    # 9: sfx_file
    # 10: bgm.wav
    vf = (
        "[0:v]scale=1080:1920[bg];"
        "[bg][2:v]overlay=x=690:y=1380[v_base];"
        f"[v_base][3:v]overlay=x=690:y=1380:enable='{mouth_flap_expr}'[v_teacher];"
        f"[v_teacher][4:v]overlay=x=100:y=1120:enable='between(t,{t_joke_start},{t_joke_end})'[v_stk];"
        f"[v_stk][5:v]overlay=x=0:y=0:enable='between(t,{t_hook},{duration:.2f})'[v_h];"
        f"[v_h][6:v]overlay=x=0:y=0:enable='between(t,{t_s1},{duration:.2f})'[v_s1];"
        f"[v_s1][7:v]overlay=x=0:y=0:enable='between(t,{t_s2},{duration:.2f})'[v_s2];"
        f"[v_s2][8:v]overlay=x=0:y=0:enable='between(t,{t_res},{duration:.2f})'[v_res];"
        f"[v_res]drawbox=x=80:y=1800:w=(iw-160)*t/{duration:.2f}:h=8:color=#facc15:t=fill,"
        "subtitles=captions.srt:force_style='FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,MarginV=190'[outv]"
    )

    af = (
        f"[10:a]volume=0.10[bgm_soft]; "
        f"[1:a]asplit=2[v_main][v_sc]; "
        f"[bgm_soft][v_sc]sidechaincompress=threshold=0.03:ratio=5:attack=100:release=400[bgm_ducked]; "
        f"[v_main][bgm_ducked]amix=inputs=2:duration=first[a_voice_bgm]; "
        f"[9:a]adelay={sfx_delay_ms}|{sfx_delay_ms},volume=0.85[a_sfx]; "
        f"[a_voice_bgm][a_sfx]amix=inputs=2:duration=first[outa]"
    )

    cmd = (
        f'ffmpeg -y '
        f'-loop 1 -t {duration:.2f} -i chalkboard.png '
        f'-i voice.mp3 '
        f'-loop 1 -t {duration:.2f} -i teacher_closed.png '
        f'-loop 1 -t {duration:.2f} -i teacher_open.png '
        f'-loop 1 -t {duration:.2f} -i sticker_active.png '
        f'-loop 1 -t {duration:.2f} -i card_hook.png '
        f'-loop 1 -t {duration:.2f} -i card_step1.png '
        f'-loop 1 -t {duration:.2f} -i card_step2.png '
        f'-loop 1 -t {duration:.2f} -i card_result.png '
        f'-i {sfx_file} '
        f'-i bgm.wav '
        f'-filter_complex "{vf}; {af}" '
        f'-map "[outv]" -map "[outa]" -c:v libx264 -preset ultrafast -crf 22 -c:a aac -t {duration:.2f} final_video.mp4'
    )
    subprocess.run(cmd, shell=True, check=True)
    
    thumb_time = min(2.0, max(0.5, duration / 4))
    subprocess.run(f'ffmpeg -y -ss {thumb_time:.2f} -i final_video.mp4 -vframes 1 -q:v 2 thumbnail.jpg', shell=True)
    print("✓ اكتمل إنتاج الفيديو بنجاح تام.")

# 10. تشغيل المسار الرئيسي
async def main():
    generate_sfx()
    data = generate_lesson_content()
    generate_graphics_and_cards(data)
    
    txt_filename = f"بيانات_{LANG}_درس_{LESSON_NUM}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"العنوان:\n{data.get('title', '')}\n\n")
        f.write(f"الوصف:\n{data.get('description', '')}\n\n")
        f.write(f"الكلمات المفتاحية:\n{data.get('tags', '')}\n")

    speech_intervals = await create_voiceover_safe(data["spoken_script"])
    actual_duration = get_audio_duration("voice.mp3")
    print(f"⏱️ مدة الصوت الفعلية: {actual_duration:.2f} ثانية")
    
    generate_ambient_bgm(actual_duration + 3)
    build_video_with_ffmpeg(data, actual_duration, speech_intervals)
    print("🎉 انتهى خط الإنتاج بالكامل!")

if __name__ == "__main__":
    asyncio.run(main())
