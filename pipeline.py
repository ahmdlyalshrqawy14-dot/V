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

# 2. قراءة الخط العربي المحلي المرفوع في المستودع
def get_font(size):
    candidates = [
        "Cairo-Bold.ttf",
        "fonts/Cairo-Bold.ttf",
        "font.ttf",
        "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    if os.path.exists("fonts"):
        for f in os.listdir("fonts"):
            if f.lower().endswith(".ttf"):
                candidates.insert(0, os.path.join("fonts", f))
                
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

# 3. تشكيل وضبط اتجاه الحروف العربية
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

# 4. قياس مدة الصوت بدقة
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

# 5. توليد موسيقى خلفية هادئة (BGM)
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

# 6. توليد المؤثرات الصوتية SFX
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

# 7. رسم الجرافيك ووضعيات المعلم التفاعلي
def generate_graphics_and_cards(data):
    print("🎨 رسم السبورة الموسعة ووضعيات المعلم التفاعلي...")
    board = Image.new("RGBA", (1140, 2020), "#3c2211")
    d = ImageDraw.Draw(board)
    d.rectangle([25, 45, 1115, 1975], fill="#5a3217")
    d.rectangle([55, 75, 1085, 1945], fill="#113327", outline="#d1d5db", width=3)
    d.rectangle([90, 1900, 1050, 1925], fill="#7c3f1d")
    d.rectangle([160, 1895, 195, 1905], fill="#ffffff")
    d.rectangle([210, 1895, 245, 1905], fill="#fde047")
    d.rectangle([260, 1895, 295, 1905], fill="#67e8f9")
    
    font_title = get_font(48)
    d.text((570, 150), shape_text(SERIES_NAME), font=font_title, fill="#fef08a", anchor="mm")
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

    def make_text_overlay(text, font_size, fill_color, y_pos, filename, bg_box=False, prefix=""):
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        font = get_font(font_size)
        display_str = f"{prefix} {text}".strip() if prefix else str(text).strip()
        shaped = shape_text(display_str)
        
        if bg_box:
            bbox = dr.textbbox((540, y_pos), shaped, font=font, anchor="mm")
            pad_x, pad_y = 35, 18
            dr.rounded_rectangle([bbox[0]-pad_x, bbox[1]-pad_y, bbox[2]+pad_x, bbox[3]+pad_y], radius=18, fill="#064e3b", outline="#86efac", width=3)
            dr.text((540, y_pos), shaped, font=font, fill="#86efac", anchor="mm")
        else:
            dr.text((540, y_pos), shaped, font=font, fill=fill_color, anchor="mm")
        img.save(filename)

    make_text_overlay(data.get("hook_text", ""), 48, "#ffffff", 360, "card_hook.png")
    make_text_overlay(data.get("step_1", ""), 42, "#fef08a", 540, "card_step1.png", prefix="1.")
    make_text_overlay(data.get("step_2", ""), 42, "#67e8f9", 720, "card_step2.png", prefix="2.")
    make_text_overlay(data.get("result_text", ""), 50, "#86efac", 920, "card_result.png", bg_box=True)

    effect = data.get("effect_type", "shock")
    stk = Image.new("RGBA", (520, 160), (0, 0, 0, 0))
    d_stk = ImageDraw.Draw(stk)
    bg_col = "#dc2626" if effect == "shock" else "#059669"
    d_stk.rounded_rectangle([18, 18, 508, 148], radius=22, fill="#0f172a@150")
    d_stk.rounded_rectangle([10, 10, 500, 140], radius=22, fill=bg_col, outline="#ffffff", width=4)
    joke_txt = shape_text(data.get("joke_text", "حساب عبقري!"))
    d_stk.text((255, 75), joke_txt, font=get_font(28), fill="#ffffff", anchor="mm")
    stk.save("sticker_active.png")

# 8. صياغة البرومبت بدقة تعليمية
def generate_lesson_content():
    target_words = max(55, int(TARGET_DURATION * 2.2))
    print(f"⏳ توليد المحتوى التعليمي عبر Gemini ({LANG.upper()})...")
    
    if LANG == "ar":
        prompt = f"""
        أنت صانع محتوى رياضيات تيك توك وريلز مصري احترافي وممتع.
        المطلوب: شرح حيلة رياضية سريعة ومفيدة عن: {SERIES_NAME} - حلقة {LESSON_NUM}.
        
        شروط الجودة البصرية:
        - ممنوع خلط الرموز الإنجليزية مع الكلمات العربية في نفس السطر.
        - hook_text: المسألة أو الفكرة باختصار (مثال: "ضرب أي رقم في 11 ذهنياً").
        - step_1: الخطوة الأولى واضحة (مثال: "افصل الرقمين: 35 تصبح 3 و 5").
        - step_2: الخطوة الثانية المباشرة (مثال: "اجمع الرقمين: 3 + 5 = 8").
        - result_text: الناتج النهائي المباشر (مثال: "الناتج النهائي = 385 🎉").
        - joke_text: إفيه أو تشجيع قصير للاستيكر (أقل من 5 كلمات).
        - spoken_script: سيناريو بالعامية المصرية الودودة بطول حوالي {target_words} كلمة، مشكول بالحركات تماماً لسلامة النطق الصوتي وبدون رموز لاتينية.
        
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
        Target length: {target_words} words. All board texts concise and crystal clear.
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

# 9. تسجيل الصوت مع المحرك الاحتياطي
async def create_voiceover_safe(text, output_file="voice.mp3"):
    print("⏳ فحص النص وتنظيفه وتسجيل الصوت...")
    
    raw_text = str(text).replace("\n", " ").replace("\r", " ")
    clean_text = re.sub(r'["\'`*_~<>{}[\]\\/+=^$]', ' ', raw_text)
    clean_text = " ".join(clean_text.split()).strip()
    
    if len(clean_text.split()) < 5:
        clean_text = "يلا نحل المسألة دي في ثواني وبطريقة سهلة جداً!" if LANG == "ar" else "Let us solve this math problem quickly and easily!"

    voices_pool = ["ar-EG-ShakirNeural", "ar-EG-SalmaNeural"] if LANG == "ar" else ["en-US-ChristopherNeural", "en-US-GuyNeural"]
    words_data = []
    edge_success = False

    for attempt in range(2):
        voice = voices_pool[attempt % len(voices_pool)]
        print(f"🎙️ محاولة تسجيل الصوت ({attempt + 1}/2) عبر: {voice}")
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

    if not edge_success:
        print("🔄 التبديل لمحرك gTTS الاحتياطي...")
        try:
            gtts_text = re.sub(r'[\u064B-\u0652\u0670]', '', clean_text) if LANG == "ar" else clean_text
            tts = gTTS(text=gtts_text, lang="ar" if LANG == "ar" else "en")
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

# 10. المونتاج الحركي والرندرة
def build_video_with_ffmpeg(data, duration, speech_intervals):
    print(f"⏳ رندرة الفيديو الاحترافي عبر FFmpeg (المدة: {duration:.2f}s)...")
    effect = data.get("effect_type", "shock")
    sfx_file = "boom.wav" if effect == "shock" else "ding.wav"

    t_hook = 0.5
    t_s1 = round(duration * 0.22, 2)
    t_s2 = round(duration * 0.48, 2)
    t_res = round(duration * 0.72, 2)
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

    def make_slide_fade(t_start):
        alpha_expr = f"min(1,max(0,(t-{t_start})/0.35))"
        y_expr = f"-25*max(0,1-(t-{t_start})/0.35)"
        return f"overlay=x=0:y='{y_expr}':enable='between(t,{t_start},{duration:.2f})':alpha='{alpha_expr}'"

    has_sub = os.path.exists("captions.srt") and os.path.getsize("captions.srt") > 15
    sub_filter = (
        ",subtitles=captions.srt:force_style='"
        "PlayResX=1080,PlayResY=1920,FontName=Cairo,FontSize=34,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,"
        "MarginV=140,Alignment=2'"
    ) if has_sub else ""

    vf = (
        f"[0:v]crop=w=1080:h=1920:x='(in_w-1080)*(t/{duration:.2f})':y='(in_h-1920)*(t/{duration:.2f})'[bg];"
        "[bg][2:v]overlay=x=630:y=1340[t_base];"
        f"[t_base][3:v]overlay=x=630:y=1340:enable='{cond_idle_open}'[t_id_op];"
        f"[t_id_op][4:v]overlay=x=630:y=1340:enable='{cond_point_closed}'[t_pt_cl];"
        f"[t_pt_cl][5:v]overlay=x=630:y=1340:enable='{cond_point_open}'[v_teacher];"
        f"[v_teacher][6:v]overlay=x=80:y=1120:enable='between(t,{t_joke_start},{t_joke_end})':alpha='min(1,(t-{t_joke_start})/0.25)'[v_stk];"
        f"[v_stk][7:v]{make_slide_fade(t_hook)}[v_h];"
        f"[v_h][8:v]{make_slide_fade(t_s1)}[v_s1];"
        f"[v_s1][9:v]{make_slide_fade(t_s2)}[v_s2];"
        f"[v_s2][10:v]{make_slide_fade(t_res)}[v_res];"
        f"[v_res]drawbox=x=80:y=1800:w=(iw-160)*t/{duration:.2f}:h=8:color=#facc15:t=fill"
        f"{sub_filter}[outv]"
    )

    af = (
        f"[12:a]volume=0.10[bgm_soft]; "
        f"[1:a]asplit=2[v_main][v_sc]; "
        f"[bgm_soft][v_sc]sidechaincompress=threshold=0.03:ratio=5:attack=100:release=400[bgm_ducked]; "
        f"[v_main][bgm_ducked]amix=inputs=2:duration=first[a_voice_bgm]; "
        f"[11:a]adelay={sfx_delay_ms}|{sfx_delay_ms},volume=0.85[a_sfx]; "
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

# 11. تشغيل المسار
async def main():
    generate_sfx()
    data = generate_lesson_content()
    generate_graphics_and_cards(data)
    
    txt_filename = f"بيانات_{LANG}_درس_{LESSON_NUM}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"العنوان:\n{data.get('title', '')}\n\n")
        f.write(f"الوصف:\n{data.get('description', '')}\n\n")
        f.write(f"الكلمات المفتاحية:\n{data.get('tags', '')}\n")

    spoken_script = data.get("spoken_script", "يلا نحل المسألة دي في ثواني وبطريقة سهلة جداً!")
    speech_intervals, actual_duration = await create_voiceover_safe(spoken_script)
    print(f"⏱️ مدة الصوت المعتمدة: {actual_duration:.2f} ثانية")
    
    generate_ambient_bgm(actual_duration + 3)
    build_video_with_ffmpeg(data, actual_duration, speech_intervals)
    print("🎉 انتهى خط الإنتاج بالكامل بمستوى بصري احترافي!")

if __name__ == "__main__":
    asyncio.run(main())
