import os
import json
import asyncio
import urllib.request
import urllib.error
import wave
import math
import struct
import edge_tts
from PIL import Image, ImageDraw

# 1. تهيئة المتغيرات والمدخلات
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
SERIES_NAME = os.environ.get("SERIES_NAME", "حيل الرياضيات السريعة")
LESSON_NUM = os.environ.get("LESSON_NUM", "1")
LANG = os.environ.get("VIDEO_LANG", "ar").lower().strip()

# 2. توليد المؤثرات الصوتية برمجياً بتردد 24000Hz ليتطابق مع صوت التعليق
def generate_sfx():
    print("🔊 جاري توليد المؤثرات الصوتية الحركية (SFX)...")
    # رنة فكرة ذكية Ding
    with wave.open("ding.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        data = []
        for i in range(12000):  # نصف ثانية
            t = i / 24000
            val = int(32767 * 0.4 * math.sin(2 * math.pi * 987.77 * t) * math.exp(-6 * t))
            data.append(struct.pack('<h', val))
        f.writeframes(b''.join(data))

    # ضربة صدمة وتنبيه Boom
    with wave.open("boom.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        data = []
        for i in range(19200):  # 0.8 ثانية
            t = i / 24000
            freq = max(45, 140 - 110 * t)
            val = int(32767 * 0.6 * math.sin(2 * math.pi * freq * t) * math.exp(-3 * t))
            data.append(struct.pack('<h', val))
        f.writeframes(b''.join(data))

# 3. بناء الجرافيك: السبورة الخشبية، المعلم الكرتوني، واستيكرات الميمز
def generate_graphics():
    print("🎨 جاري رسم السبورة، المعلم الكرتوني، واستيكرات المونتاج...")
    
    # 3.1 السبورة الخضراء الكلاسيكية مع الإطار الخشبي ورف الطباشير
    board = Image.new("RGBA", (1080, 1920), "#452613")  # خشب داكن
    d = ImageDraw.Draw(board)
    # إطار داخلي بارز
    d.rectangle([25, 45, 1055, 1875], fill="#693b1d")
    # مساحة الطباشير الخضراء
    d.rectangle([55, 75, 1025, 1845], fill="#13382b", outline="#e5e7eb", width=3)
    # رف الطباشير السفلي
    d.rectangle([90, 1810, 990, 1835], fill="#854820")
    # قطع طباشير ملونة فوق الرف
    d.rectangle([150, 1805, 185, 1815], fill="#ffffff")
    d.rectangle([200, 1805, 235, 1815], fill="#fde047")
    d.rectangle([250, 1805, 285, 1815], fill="#67e8f9")
    board.save("chalkboard.png")

    # 3.2 رسم المعلم (فم مفتوح ومغلق) للتحريك التفاعلي
    def draw_teacher(mouth_open=False):
        img = Image.new("RGBA", (340, 420), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        # الجسد والبدلة
        dr.rectangle([90, 250, 250, 420], fill="#1d4ed8")
        # ربطة العنق
        dr.polygon([(170, 250), (150, 310), (170, 370), (190, 310)], fill="#b91c1c")
        # الرأس والوجه
        dr.ellipse([100, 80, 240, 235], fill="#fed7aa")
        # الشعر الكلاسيكي
        dr.chord([100, 60, 240, 160], 180, 360, fill="#3b2219")
        # النظارات
        dr.rectangle([115, 125, 160, 155], outline="#0f172a", width=4)
        dr.rectangle([180, 125, 225, 155], outline="#0f172a", width=4)
        dr.line([160, 140, 180, 140], fill="#0f172a", width=4)
        # العيون
        dr.ellipse([132, 135, 142, 145], fill="#0f172a")
        dr.ellipse([197, 135, 207, 145], fill="#0f172a")
        # الفم (متحرك)
        if mouth_open:
            dr.ellipse([155, 185, 185, 210], fill="#881337")
        else:
            dr.line([155, 195, 185, 195], fill="#881337", width=4)
        return img

    draw_teacher(mouth_open=False).save("teacher_closed.png")
    draw_teacher(mouth_open=True).save("teacher_open.png")

    # 3.3 استيكرات الميمز
    # استيكر الصدمة (MIND BLOWN)
    stk1 = Image.new("RGBA", (460, 150), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(stk1)
    d1.rounded_rectangle([10, 10, 450, 140], radius=25, fill="#dc2626", outline="#ffffff", width=4)
    stk1.save("sticker_shock.png")

    # استيكر العبقرية (GENIUS IDEA)
    stk2 = Image.new("RGBA", (460, 150), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(stk2)
    d2.rounded_rectangle([10, 10, 450, 140], radius=25, fill="#059669", outline="#fef08a", width=4)
    stk2.save("sticker_idea.png")

# 4. البرومبت الذكي لصناعة الاسكريبت (Master Prompt)
def generate_lesson_content():
    print(f"⏳ توليد المحتوى الذكي بالفكاهة والمونتاج عبر Gemini ({LANG.upper()})...")
    
    if LANG == "ar":
        prompt = f"""
        أنت صانع محتوى تيك توك وريلز مصري فكاهي وخبير رياضيات.
        المطلوب سيناريو شورتس سريع ومضحك في 35 ثانية عن: {SERIES_NAME} - درس {LESSON_NUM}.
        
        الشروط الإجبارية:
        1. ابدأ بهوك فكاهي صادم في أول 3 ثوانٍ يسخر من الحل التقليدي المعقد.
        2. استخدم أسلوب كلام مصري مشكول بالحركات تماماً لضبط النطق.
        3. حدد نوع التأثير إما "shock" أو "idea".
        
        أخرج الرد بصيغة JSON حصرية بدون ماركداون:
        {{
          "title": "عنوان جذاب ومثير مع إيموجي",
          "description": "وصف يوتيوب كامل بالهاشتاجات #رياضيات #شورتس #ثانوية",
          "tags": "رياضيات, قدرات, جبر, شورتس, حيل",
          "spoken_script": "نص الشرح المنطوق باللغة العربية ومشكل بالكامل لسلامة النطق الصوتي بدون مقدمات مملة",
          "hook_text": "المسألة الصادمة (مثال: س² - ٤٩ = ٠)",
          "joke_text": "إفيه قصير جداً للاستيكر (مثال: مستر الرياضة في صدمة!)",
          "step_1": "الحيلة الذكية الأولى",
          "step_2": "التطبيق السريع",
          "result_text": "الحل في ثانية واحدة 🎉",
          "effect_type": "shock"
        }}
        """
    else:
        prompt = f"""
        You are a viral TikTok math creator known for humor and mental hacks.
        Create an entertaining 35-second math hack Short about: {SERIES_NAME} - Ep {LESSON_NUM}.
        
        Rules:
        1. Hook the viewer in the first 2 seconds with a funny or dramatic statement.
        2. Fast, conversational English script.
        3. Choose effect_type as either "shock" or "idea".
        
        Output ONLY valid JSON:
        {{
          "title": "Catchy Title with Emojis",
          "description": "Shorts description with hashtags #math #lifehacks #shorts",
          "tags": "math hacks, algebra, quick tips, shorts",
          "spoken_script": "High-energy humorous spoken script in English. Fast and punchy.",
          "hook_text": "The Problem (e.g., 98 x 95 in 3 seconds?)",
          "joke_text": "Short funny caption (e.g., School never taught you this!)",
          "step_1": "Trick Step 1",
          "step_2": "Trick Step 2",
          "result_text": "Final Answer 🎉",
          "effect_type": "idea"
        }}
        """

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash"
    ]

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
            print(f"🔄 محاولة الاتصال بالنموذج: {model_name}...")
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

# 5. تحويل النص لصوت واقعي
async def create_voiceover(text, output_file="voice.mp3"):
    print(f"⏳ تحويل النص لصوت باللغة ({LANG.upper()})...")
    voice = "ar-EG-ShakirNeural" if LANG == "ar" else "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    print("✓ تم تسجيل الصوت بنجاح.")

# 6. المونتاج والرندرة الكاملة عبر FFmpeg
def build_video_with_ffmpeg(data):
    print("⏳ جاري رندرة الفيديو والسبورة وحركة المعلم والمؤثرات عبر FFmpeg...")
    
    # تنظيف النصوص لسلامة أوامر FFmpeg
    def clean(t): return str(t).replace("'", "").replace(":", " - ").replace('"', '')
    hook = clean(data.get("hook_text", "Problem"))
    joke = clean(data.get("joke_text", "Wait for it!"))
    s1 = clean(data.get("step_1", "Step 1"))
    s2 = clean(data.get("step_2", "Step 2"))
    res = clean(data.get("result_text", "Solved!"))
    effect = data.get("effect_type", "shock")

    sticker_file = "sticker_shock.png" if effect == "shock" else "sticker_idea.png"
    sfx_file = "boom.wav" if effect == "shock" else "ding.wav"

    # الفلاتر البصرية:
    # - وضع المعلم في زاوية السبورة
    # - تبديل صورة الفم المفتوح كل 0.15 ثانية ليعطي إيحاء الكلام الطبيعي
    # - ظهور الاستيكر بين الثانية 4 و 8
    # - كتابة الخطوات بالطباشير الأبيض والأصفر والسماوي
    vf = (
        "[0:v]scale=1080:1920[bg];"
        "[bg][2:v]overlay=x=690:y=1380[v_base];"
        "[v_base][3:v]overlay=x=690:y=1380:enable='between(mod(t,0.3),0,0.15)'[v_teacher];"
        f"[v_teacher][4:v]overlay=x=100:y=1120:enable='between(t,4,8)'[v2];"
        f"[v2]drawtext=text='{clean(SERIES_NAME)}':fontcolor=#fef08a:fontsize=50:x=(w-text_w)/2:y=150,"
        f"drawtext=text='{hook}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=360:enable='between(t,1,60)',"
        f"drawtext=text='{s1}':fontcolor=#fef08a:fontsize=46:x=(w-text_w)/2:y=600:enable='between(t,3,60)',"
        f"drawtext=text='{s2}':fontcolor=#67e8f9:fontsize=46:x=(w-text_w)/2:y=840:enable='between(t,7,60)',"
        f"drawtext=text='{joke}':fontcolor=white:fontsize=36:x=130:y=1175:enable='between(t,4,8)',"
        f"drawtext=text='{res}':fontcolor=#86efac:fontsize=58:box=1:boxcolor=#064e3b@0.85:boxborderw=15:x=(w-text_w)/2:y=1050:enable='between(t,11,60)',"
        "drawbox=x=80:y=1800:w=(iw-160)*t/40:h=8:color=#facc15:t=fill[outv]"
    )

    # دمج مؤثر الصوت SFX في الثانية 4 مع الصوت الأساسي
    af = f"[1:a]volume=1.0[a_voice]; [5:a]adelay=4000|4000,volume=0.8[a_sfx]; [a_voice][a_sfx]amix=inputs=2:duration=first[outa]"

    cmd = (
        f'ffmpeg -y -loop 1 -i chalkboard.png '
        f'-i voice.mp3 '
        f'-loop 1 -i teacher_closed.png '
        f'-loop 1 -i teacher_open.png '
        f'-loop 1 -i {sticker_file} '
        f'-i {sfx_file} '
        f'-filter_complex "{vf}; {af}" '
        f'-map "[outv]" -map "[outa]" -c:v libx264 -preset fast -crf 20 -c:a aac -shortest final_video.mp4'
    )
    os.system(cmd)
    print("✓ تم تجميع ورندرة الفيديو النهائي بنجاح.")

# 7. مسار التشغيل الكامل
async def main():
    generate_sfx()
    generate_graphics()
    data = generate_lesson_content()
    
    txt_filename = f"بيانات_{LANG}_درس_{LESSON_NUM}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"العنوان المقترح:\n{data.get('title', '')}\n\n")
        f.write(f"الوصف:\n{data.get('description', '')}\n\n")
        f.write(f"الكلمات المفتاحية:\n{data.get('tags', '')}\n")

    await create_voiceover(data["spoken_script"])
    build_video_with_ffmpeg(data)
    print("🎉 اكتمل إنتاج الفيديو والمحتوى وأصبح جاهزاً للتحميل!")

if __name__ == "__main__":
    asyncio.run(main())
