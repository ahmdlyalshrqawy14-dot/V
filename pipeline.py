import os
import sys
import re
import json
import asyncio
import urllib.request
import urllib.error
import wave
import math
import struct
import subprocess
import edge_tts
from gtts import gTTS
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

# 1. التحقق من البيئة
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_KEY:
    print("❌ خطأ حرج: متغير GEMINI_API_KEY غير موجود في أسرار المستودع!")
    sys.exit(1)

SERIES_NAME = os.environ.get("SERIES_NAME", "حيل الرياضيات السريعة")
LESSON_NUM = os.environ.get("LESSON_NUM", "1")
LANG = os.environ.get("VIDEO_LANG", "ar").lower().strip()
TARGET_DURATION = int(os.environ.get("TARGET_DURATION", "30"))

# 2. تشكيل الخط العربي
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

# 3. قياس مدة الصوت بدقة
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

# 4. توليد BGM
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
            sample_val = (sample_val / len(chords[chord_idx])) * 0.15
            envelope = min(1.0, t / 1.5) * min(1.0, (duration - t) / 1.5)
            val = int(32767 * sample_val * envelope)
            data.append(struct.pack('<h', max(-32767, min(32767, val))))
        f.writeframes(b''.join(data))
    return output_file

# 5. توليد المؤثرات الصوتية SFX
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

# 6. رسم السبورة وبطاقات النصوص
def generate_graphics_and_cards(data):
    print("🎨 رسم السبورة وبطاقات النصوص عبر Pillow...")
    board = Image.new("RGBA", (1080, 1920), "#452613")
    d = ImageDraw.Draw(board)
    d.rectangle([25, 45, 1055, 1875], fill="#693b1d")
    d.rectangle([55, 75, 1025, 1845], fill="#13382b", outline="#e5e7eb", width=3)
    d.rectangle([90, 1810, 990, 1835], fill="#854820")
    d.rectangle([150, 1805, 185, 1815], fill="#ffffff")
    d.rectangle([200, 1805, 235, 1815], fill="#fde047")
    d.rectangle([250, 1805, 285, 1815], fill="#67e8f9")
    
    font_title = get_font(48)
    d.text((540, 150), shape_text(SERIES_NAME), font=font_title, fill="#fef08a", anchor="mm")
    board.save("chalkboard.png")

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

    effect = data.get("effect_type", "shock")
    stk = Image.new("RGBA", (500, 150), (0, 0, 0, 0))
    d_stk = ImageDraw.Draw(stk)
    bg_col = "#dc2626" if effect == "shock" else "#059669"
    d_stk.rounded_rectangle([10, 10, 490, 140], radius=20, fill=bg_col, outline="#ffffff", width=4)
    d_stk.text((250, 75), shape_text(data.get("joke_text", "انتظر المفاجأة!")), font=get_font(30), fill="#ffffff", anchor="mm")
    stk.save("sticker_active.png")

# 7. توليد المحتوى عبر Gemini
def generate_lesson_content():
    target_words = max(55, int(TARGET_DURATION * 2.2))
    print(f"⏳ توليد محتوى {LANG.upper()} بطول مستهدف {target_words} كلمة...")
    
    if LANG == "ar":
        prompt = f"""
        أنت صانع محتوى رياضيات تيك توك وريلز مصري مضحك وسريع.
        المطلوب درس عن: {SERIES_NAME} - حلقة {LESSON_NUM}.
        
        شرط حاسم للمدة: يجب ألا يقل نص spoken_script عن {target_words} كلمة، لكي يستغرق التعليق الصوتي مدة كافية.
        تنبيه: اكتب نص spoken_script كسرد كلامي طبيعي بدون أي أقواس رياضية معقدة أو معادلات بصيغة LaTeX.
        
        أخرج الرد بصيغة JSON حصرية:
        {{
          "title": "عنوان جذاب مع إيموجي",
          "description": "وصف كامل بالهاشتاجات #رياضيات #شورتس",
          "tags": "رياضيات, قدرات, جبر, شورتس",
          "spoken_script": "نص الاسكريبت المنطوق بالعامية المصرية ومشكل بالحركات تماماً بطول حوالي {target_words} كلمة",
          "hook_text": "المسألة أو المعادلة الصادمة",
          "joke_text": "إفيه قصير جداً للاستيكر",
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
        
        CRITICAL DURATION RULE: spoken_script MUST contain at least {target_words} words.
        Write spoken_script as clean spoken plain English words (no math symbols like ^, $, sqrt, just spoken words).
        
        Output ONLY valid JSON:
        {{
          "title": "Catchy Title with Emojis",
          "description": "Shorts description with hashtags",
          "tags": "math hacks, algebra, quick tips, shorts",
          "spoken_script": "Spoken plain text script with AT LEAST {target_words} words. Punchy and humorous.",
          "hook_text": "The Problem",
          "joke_text": "Short funny caption",
          "step_1": "Step 1 Hack",
          "step_2": "Step 2 Hack",
          "result_text": "Final Answer 🎉",
          "effect_type": "idea"
        }}
        """

    models_to_try = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.75}
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
    raise RuntimeError("فشلت محاولات الاتصال بكافة نماذج Gemini.")

# 8. توليد الصوت الآمن مع التحويل الاحتياطي لمحرك gTTS
async def create_voiceover_safe(text, output_file="voice.mp3"):
    print("⏳ فحص النص وتنظيفه وتسجيل التعليق الصوتي...")
    
    # تنظيف النص بالكامل من الرموز والأسطر المزدوجة التي ترفضها خوادم الصوت
    raw_text = str(text).replace("\n", " ").replace("\r", " ")
    clean_text = re.sub(r'["\'`*_~<>{}[\]\\/+=^$]', ' ', raw_text)
    clean_text = " ".join(clean_text.split()).strip()
    
    if len(clean_text.split()) < 5:
        clean_text = "Let us solve this math problem quickly and easily!" if LANG != "ar" else "يلا نحل المسألة دي في ثواني وبطريقة سهلة جداً!"

    print(f"📝 النص النهائي ({len(clean_text.split())} كلمة): {clean_text[:70]}...")

    voices_pool = ["ar-EG-ShakirNeural", "ar-EG-SalmaNeural"] if LANG == "ar" else ["en-US-ChristopherNeural", "en-US-GuyNeural"]
    words_data = []
    edge_success = False

    # محاولة التسجيل عبر edge-tts أولاً
    for attempt in range(2):
        voice = voices_pool[attempt % len(voices_pool)]
        print(f"🎙️ محاولة edge-tts ({attempt + 1}/2) عبر: {voice}")
        try:
            communicate = edge_tts.Communicate(clean_text, voice)
            words_data.clear()

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

            await asyncio.wait_for(_fetch(), timeout=25)
            if os.path.exists(output_file) and os.path.getsize(output_file) > 2000:
                print("✓ تم التسجيل بنجاح عبر edge-tts!")
                edge_success = True
                break
        except Exception as e:
            print(f"⚠️ تعثر edge-tts: {e}")
            await asyncio.sleep(1)

    # التحويل التلقائي لمحرك gTTS الاحتياطي في حال حظر سيرفر مايكروسوفت
    if not edge_success:
        print("🔄 تعثر الاتصال بمايكروسوفت، جاري التبديل الفوري لمحرك الصوت البديل (gTTS)...")
        try:
            tts = gTTS(text=clean_text, lang="ar" if LANG == "ar" else "en")
            tts.save(output_file)
            print("✓ تم إنشاء الصوت بنجاح عبر المحرك البديل!")
        except Exception as e:
            raise RuntimeError(f"فشل إنشاء الصوت عبر كافة المحركات: {e}")

    actual_dur = get_audio_duration(output_file)

    def format_srt_time(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    srt_lines = []
    if words_data:
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
    else:
        # بناء الكابشنز برمجياً في حال استخدام المحرك البديل
        words = clean_text.split()
        chunk_size = 4
        chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        step_dur = actual_dur / max(1, len(chunks))
        for idx, ch in enumerate(chunks):
            s_t = format_srt_time(idx * step_dur)
            e_t = format_srt_time(min(actual_dur, (idx + 1) * step_dur))
            srt_lines.append(f"{idx+1}\n{s_t} --> {e_t}\n{ch}\n")

    with open("captions.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

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

    return speech_intervals, actual_dur

# 9. المونتاج والرندرة
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

    has_sub = os.path.exists("captions.srt") and os.path.getsize("captions.srt") > 15
    sub_filter = ",subtitles=captions.srt:force_style='FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,MarginV=190'" if has_sub else ""

    vf = (
        "[0:v]scale=1080:1920[bg];"
        "[bg][2:v]overlay=x=690:y=1380[v_base];"
        f"[v_base][3:v]overlay=x=690:y=1380:enable='{mouth_flap_expr}'[v_teacher];"
        f"[v_teacher][4:v]overlay=x=100:y=1120:enable='between(t,{t_joke_start},{t_joke_end})'[v_stk];"
        f"[v_stk][5:v]overlay=x=0:y=0:enable='between(t,{t_hook},{duration:.2f})'[v_h];"
        f"[v_h][6:v]overlay=x=0:y=0:enable='between(t,{t_s1},{duration:.2f})'[v_s1];"
        f"[v_s1][7:v]overlay=x=0:y=0:enable='between(t,{t_s2},{duration:.2f})'[v_s2];"
        f"[v_s2][8:v]overlay=x=0:y=0:enable='between(t,{t_res},{duration:.2f})'[v_res];"
        f"[v_res]drawbox=x=80:y=1800:w=(iw-160)*t/{duration:.2f}:h=8:color=#facc15:t=fill"
        f"{sub_filter}[outv]"
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

    speech_intervals, actual_duration = await create_voiceover_safe(data["spoken_script"])
    print(f"⏱️ مدة الصوت المعتمدة: {actual_duration:.2f} ثانية")
    
    generate_ambient_bgm(actual_duration + 3)
    build_video_with_ffmpeg(data, actual_duration, speech_intervals)
    print("🎉 انتهى خط الإنتاج بالكامل!")

if __name__ == "__main__":
    asyncio.run(main())
