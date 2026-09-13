import os
import json
import asyncio
import urllib.request
import urllib.error
import wave
import math
import struct
import subprocess
import edge_tts
from PIL import Image, ImageDraw

# 1. تهيئة المتغيرات
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
SERIES_NAME = os.environ.get("SERIES_NAME", "حيل الرياضيات السريعة")
LESSON_NUM = os.environ.get("LESSON_NUM", "1")
LANG = os.environ.get("VIDEO_LANG", "ar").lower().strip()

# 2. قياس مدة الصوت بدقة عبر ffprobe
def get_audio_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 35.0

# 3. توليد مسار موسيقى خلفية هادئ (Lo-Fi Synth Pad) برمجياً
def generate_ambient_bgm(duration, output_file="bgm.wav"):
    print("🎵 جاري تجهيز موسيقى الخلفية الهادئة (BGM)...")
    if os.path.exists("bgm.mp3"):
        return "bgm.mp3"
    
    sample_rate = 24000
    total_samples = int(duration * sample_rate)
    chords = [
        [130.81, 164.81, 196.00, 246.94],  # Cmaj7
        [110.00, 130.81, 164.81, 196.00],  # Am7
        [87.31,  110.00, 130.81, 164.81],  # Fmaj7
        [98.00,  123.47, 146.83, 174.61],  # G7
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
            active_chord = chords[chord_idx]
            
            # مزج الترددات بنعومة
            sample_val = 0.0
            for freq in active_chord:
                sample_val += math.sin(2 * math.pi * freq * t)
            sample_val = (sample_val / len(active_chord)) * 0.18
            
            # تلاشي البداية والنهاية
            envelope = min(1.0, t / 1.5) * min(1.0, (duration - t) / 1.5)
            val = int(32767 * sample_val * envelope)
            data.append(struct.pack('<h', max(-32767, min(32767, val))))
            
        f.writeframes(b''.join(data))
    return output_file

# 4. توليد المؤثرات الصوتية SFX
def generate_sfx():
    print("🔊 جاري توليد المؤثرات الصوتية الحركية (SFX)...")
    with wave.open("ding.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        data = []
        for i in range(12000):
            t = i / 24000
            val = int(32767 * 0.4 * math.sin(2 * math.pi * 987.77 * t) * math.exp(-6 * t))
            data.append(struct.pack('<h', val))
        f.writeframes(b''.join(data))

    with wave.open("boom.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        data = []
        for i in range(19200):
            t = i / 24000
            freq = max(45, 140 - 110 * t)
            val = int(32767 * 0.6 * math.sin(2 * math.pi * freq * t) * math.exp(-3 * t))
            data.append(struct.pack('<h', val))
        f.writeframes(b''.join(data))

# 5. بناء أصول الجرافيك (السبورة، المعلم، الاستيكرات)
def generate_graphics():
    print("🎨 رسم السبورة والمعلم واستيكرات الميمز...")
    board = Image.new("RGBA", (1080, 1920), "#452613")
    d = ImageDraw.Draw(board)
    d.rectangle([25, 45, 1055, 1875], fill="#693b1d")
    d.rectangle([55, 75, 1025, 1845], fill="#13382b", outline="#e5e7eb", width=3)
    d.rectangle([90, 1810, 990, 1835], fill="#854820")
    d.rectangle([150, 1805, 185, 1815], fill="#ffffff")
    d.rectangle([200, 1805, 235, 1815], fill="#fde047")
    d.rectangle([250, 1805, 285, 1815], fill="#67e8f9")
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

    stk1 = Image.new("RGBA", (460, 150), (0, 0, 0, 0))
    ImageDraw.Draw(stk1).rounded_rectangle([10, 10, 450, 140], radius=25, fill="#dc2626", outline="#ffffff", width=4)
    stk1.save("sticker_shock.png")

    stk2 = Image.new("RGBA", (460, 150), (0, 0, 0, 0))
    ImageDraw.Draw(stk2).rounded_rectangle([10, 10, 450, 140], radius=25, fill="#059669", outline="#fef08a", width=4)
    stk2.save("sticker_idea.png")

# 6. توليد السيناريو عبر Gemini مع قيود الطول
def generate_lesson_content():
    print(f"⏳ توليد المحتوى الذكي عبر Gemini ({LANG.upper()})...")
    
    if LANG == "ar":
        prompt = f"""
        أنت صانع محتوى تيك توك وريلز مصري فكاهي ومحترف رياضيات.
        المطلوب سيناريو شورتس سريع ومضحك في 30-35 ثانية عن: {SERIES_NAME} - درس {LESSON_NUM}.
        
        شروط أساسية لعدم خروج النص عن الشاشة:
        - كل جملة سبورة يجب ألا تتعدى 5 إلى 6 كلمات فقط.
        - ابدأ بهوك فكاهي صادم.
        - حدد effect_type إما "shock" أو "idea".
        
        أخرج الرد بصيغة JSON حصرية بدون ماركداون:
        {{
          "title": "عنوان جذاب مع إيموجي",
          "description": "وصف كامل بالهاشتاجات #رياضيات #شورتس",
          "tags": "رياضيات, قدرات, جبر, شورتس, حيل",
          "spoken_script": "نص الشرح المنطوق باللغة العربية مشكل بالكامل لسلامة النطق الصوتي وبدون مقدمات",
          "hook_text": "المسألة الصادمة (أقل من 30 حرف)",
          "joke_text": "إفيه قصير جداً للاستيكر",
          "step_1": "الحيلة الذكية الأولى",
          "step_2": "التطبيق السريع",
          "result_text": "الحل في ثانية واحدة 🎉",
          "effect_type": "shock"
        }}
        """
    else:
        prompt = f"""
        You are a viral TikTok math creator known for humor and mental hacks.
        Create an entertaining 30-35 second math hack Short about: {SERIES_NAME} - Ep {LESSON_NUM}.
        Keep all board texts under 35 characters.
        
        Output ONLY valid JSON:
        {{
          "title": "Catchy Title with Emojis",
          "description": "Shorts description with hashtags #math #lifehacks #shorts",
          "tags": "math hacks, algebra, quick tips, shorts",
          "spoken_script": "High-energy humorous spoken script in English. Fast and punchy.",
          "hook_text": "The Problem (under 30 chars)",
          "joke_text": "Short funny caption",
          "step_1": "Trick Step 1",
          "step_2": "Trick Step 2",
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
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                print(f"✓ تم استخراج السيناريو بنجاح عبر: {model_name}")
                return json.loads(raw_text.strip())
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"فشلت المحاولات مع كافة النماذج: {last_error}")

# 7. تحويل النص لصوت مع تدوير الأصوات واستخراج الكلمات والتوقيتات
async def create_voiceover_with_subtitles(text, output_file="voice.mp3"):
    print("⏳ تسجيل التعليق الصوتي واستخراج التوقيتات الدقيقة...")
    
    # تدوير الأصوات حسب رقم الحلقة
    lesson_idx = int(LESSON_NUM) if LESSON_NUM.isdigit() else 1
    if LANG == "ar":
        voices = ["ar-EG-ShakirNeural", "ar-EG-SalmaNeural"]
    else:
        voices = ["en-US-ChristopherNeural", "en-US-JennyNeural", "en-US-GuyNeural"]
    chosen_voice = voices[lesson_idx % len(voices)]
    print(f"🎙️ الصوت المختار للحلقة: {chosen_voice}")

    communicate = edge_tts.Communicate(text, chosen_voice)
    words_data = []

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

    # بناء ملف الترجمة SRT
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

    # استخراج فترات الكلام الفعلي (لتشغيل حركة الفم وقت الكلام فقط)
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

# 8. المونتاج الحركي المتزامن والرندرة عبر FFmpeg
def build_video_with_ffmpeg(data, duration, speech_intervals):
    print("⏳ جاري المونتاج والرندرة مع مزامنة الصوت التلقائية وAudio Ducking...")
    
    def clean(t): return str(t).replace("'", "").replace(":", " - ").replace('"', '')
    hook = clean(data.get("hook_text", "Problem"))
    joke = clean(data.get("joke_text", "Wait for it!"))
    s1 = clean(data.get("step_1", "Step 1"))
    s2 = clean(data.get("step_2", "Step 2"))
    res = clean(data.get("result_text", "Solved!"))
    effect = data.get("effect_type", "shock")

    sticker_file = "sticker_shock.png" if effect == "shock" else "sticker_idea.png"
    sfx_file = "boom.wav" if effect == "shock" else "ding.wav"

    # حساب التوقيتات نسبياً مع مدة الصوت الفعلية
    t_hook = 0.5
    t_s1 = round(duration * 0.25, 2)
    t_s2 = round(duration * 0.52, 2)
    t_joke_start = round(duration * 0.35, 2)
    t_joke_end = round(duration * 0.50, 2)
    t_res = round(duration * 0.75, 2)
    sfx_delay_ms = int(t_joke_start * 1000)

    # بناء شرط حركة الفم (يعمل فقط أثناء فترات الكلام الفعلي)
    if speech_intervals:
        speech_cond = " + ".join([f"between(t,{s:.2f},{e:.2f})" for s, e in speech_intervals])
    else:
        speech_cond = "between(t,0.5,60)"
    mouth_flap_expr = f"({speech_cond}) * between(mod(t,0.28),0,0.14)"

    vf = (
        "[0:v]scale=1080:1920[bg];"
        # طبقة المعلم بفم مغلق كأساس
        "[bg][2:v]overlay=x=690:y=1380[v_base];"
        # إظهار الفم المفتوح فقط أثناء فترات الكلام الفعلي
        f"[v_base][3:v]overlay=x=690:y=1380:enable='{mouth_flap_expr}'[v_teacher];"
        # استيكر الميم التفاعلي في التوقيت المحسوب
        f"[v_teacher][4:v]overlay=x=100:y=1120:enable='between(t,{t_joke_start},{t_joke_end})'[v2];"
        # نصوص السبورة بالتوقيتات الديناميكية
        f"[v2]drawtext=text='{clean(SERIES_NAME)}':fontcolor=#fef08a:fontsize=50:x=(w-text_w)/2:y=150,"
        f"drawtext=text='{hook}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=360:enable='between(t,{t_hook},60)',"
        f"drawtext=text='{s1}':fontcolor=#fef08a:fontsize=46:x=(w-text_w)/2:y=600:enable='between(t,{t_s1},60)',"
        f"drawtext=text='{s2}':fontcolor=#67e8f9:fontsize=46:x=(w-text_w)/2:y=840:enable='between(t,{t_s2},60)',"
        f"drawtext=text='{joke}':fontcolor=white:fontsize=36:x=130:y=1175:enable='between(t,{t_joke_start},{t_joke_end})',"
        f"drawtext=text='{res}':fontcolor=#86efac:fontsize=58:box=1:boxcolor=#064e3b@0.85:boxborderw=15:x=(w-text_w)/2:y=1050:enable='between(t,{t_res},60)',"
        f"drawbox=x=80:y=1800:w=(iw-160)*t/{duration:.2f}:h=8:color=#facc15:t=fill,"
        # حرق الترجمة (الكابشنز) بخط واضح في أسفل الشاشة
        "subtitles=captions.srt:force_style='FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,MarginV=190'[outv]"
    )

    # فلاتر الصوت: Audio Ducking للموسيقى ودمج الـ SFX
    af = (
        f"[6:a]volume=0.12[bgm_soft]; "
        f"[1:a]asplit=2[v_main][v_sc]; "
        f"[bgm_soft][v_sc]sidechaincompress=threshold=0.03:ratio=5:attack=100:release=400[bgm_ducked]; "
        f"[v_main][bgm_ducked]amix=inputs=2:duration=first[a_voice_bgm]; "
        f"[5:a]adelay={sfx_delay_ms}|{sfx_delay_ms},volume=0.85[a_sfx]; "
        f"[a_voice_bgm][a_sfx]amix=inputs=2:duration=first[outa]"
    )

    cmd = (
        f'ffmpeg -y -loop 1 -i chalkboard.png '
        f'-i voice.mp3 '
        f'-loop 1 -i teacher_closed.png '
        f'-loop 1 -i teacher_open.png '
        f'-loop 1 -i {sticker_file} '
        f'-i {sfx_file} '
        f'-stream_loop -1 -i bgm.wav '
        f'-filter_complex "{vf}; {af}" '
        f'-map "[outv]" -map "[outa]" -c:v libx264 -preset fast -crf 20 -c:a aac -shortest final_video.mp4'
    )
    os.system(cmd)
    
    # استخراج صورة مصغرة (Thumbnail) بدقة عالية في الثانية 2
    os.system('ffmpeg -y -ss 00:00:02 -i final_video.mp4 -vframes 1 -q:v 2 thumbnail.jpg')
    print("✓ تم إنتاج الفيديو والصورة المصغرة والترجمة بنجاح.")

# 9. نقطة الانطلاق الرئيسية
async def main():
    generate_sfx()
    generate_graphics()
    data = generate_lesson_content()
    
    txt_filename = f"بيانات_{LANG}_درس_{LESSON_NUM}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"العنوان المقترح:\n{data.get('title', '')}\n\n")
        f.write(f"الوصف والهاشتاجات:\n{data.get('description', '')}\n\n")
        f.write(f"الكلمات المفتاحية:\n{data.get('tags', '')}\n")

    speech_intervals = await create_voiceover_with_subtitles(data["spoken_script"])
    actual_duration = get_audio_duration("voice.mp3")
    print(f"⏱️ مدة الصوت المحسوبة: {actual_duration:.2f} ثانية")
    
    generate_ambient_bgm(actual_duration + 2)
    build_video_with_ffmpeg(data, actual_duration, speech_intervals)
    print("🎉 تم اكتمال المعالجة بالكامل!")

if __name__ == "__main__":
    asyncio.run(main())
