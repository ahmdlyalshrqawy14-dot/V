import os
import json
import asyncio
import urllib.request
import urllib.error
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import edge_tts

# 1. تهيئة المتغيرات
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
GDRIVE_KEY_JSON = os.environ.get("GDRIVE_KEY")
FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID")
SERIES_NAME = os.environ.get("SERIES_NAME", "سلسلة الجبر الأساسي")
LESSON_NUM = os.environ.get("LESSON_NUM", "1")

# 2. استدعاء الموديل مباشرة عبر REST API
def generate_lesson_content():
    print("⏳ جاري توليد محتوى الدرس بواسطة الذكاء الاصطناعي...")
    prompt = f"""
    أنت معلم رياضيات خبير ومبتكر في إنتاج فيديوهات تعليمية مبسطة وجذابة.
    المطلوب إعداد سيناريو كامل لـ: {SERIES_NAME} - الدرس رقم {LESSON_NUM}.
    
    أخرج الرد بصيغة JSON حصرية وصالحة 100% وبدون أي كود markdown خارجي:
    {{
      "title": "عنوان جذاب ومثير لليوتيوب مع رمز تعبيري",
      "description": "وصف يوتيوب مهيأ بالكامل للـ SEO ومحركات البحث ويوضح محاور الفيديو والروابط",
      "tags": "كلمات, مفتاحية, دقيقة, مفصولة, بفواصل",
      "spoken_script": "نص الشرح المنطوق باللغة العربية ومشكل بالتشكيل والحركات لنطقه صوتياً بسلاسة ووضوح",
      "board_summary": "العنوان والمعادلة الرياضية الأساسية للسبورة"
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
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.7
        }
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    last_error = None
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        try:
            print(f"🔄 محاولة الاتصال المباشر بالنموذج: {model_name}...")
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]

                print(f"✓ تم استخراج المحتوى بنجاح عبر: {model_name}")
                return json.loads(raw_text.strip())
        except Exception as e:
            print(f"⚠️ تعذر عبر {model_name}: {e}")
            last_error = e
            continue

    raise RuntimeError(f"فشلت المحاولات مع كافة النماذج المحددة: {last_error}")

# 3. تحويل النص إلى صوت
async def create_voiceover(text, output_file="voice.mp3"):
    print("⏳ جاري تحويل الشرح إلى صوت بشري...")
    communicate = edge_tts.Communicate(text, "ar-EG-ShakirNeural")
    await communicate.save(output_file)
    print("✓ تم إنشاء الملف الصوتي بنجاح.")

# 4. الرندرة عبر FFmpeg
def build_video_with_ffmpeg(board_text):
    print("⏳ جاري رندرة الفيديو والسبورة بواسطة FFmpeg...")
    cmd = (
        f'ffmpeg -y -f lavfi -i color=c="#0c0d12":s=1080x1920:d=60 '
        f'-i voice.mp3 '
        f'-filter_complex "[0:v]drawtext=text=\'{SERIES_NAME}\':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=200,'
        f'drawtext=text=\'الدرس رقم {LESSON_NUM}\':fontcolor=#9d85ff:fontsize=64:x=(w-text_w)/2:y=300[v]" '
        f'-map "[v]" -map 1:a -c:v libx264 -c:a aac -shortest final_video.mp4'
    )
    os.system(cmd)
    print("✓ تم تجميع الفيديو النهائي بنجاح.")

# 5. الرفع إلى Google Drive
def upload_to_drive(file_path, file_name, mime_type):
    print(f"⏳ جاري رفع {file_name} إلى مجلد Google Drive...")
    creds_info = json.loads(GDRIVE_KEY_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["[https://www.googleapis.com/auth/drive](https://www.googleapis.com/auth/drive)"]
    )
    service = build("drive", "v3", credentials=creds)

    metadata = {"name": file_name, "parents": [FOLDER_ID]}
    media = MediaFileUpload(file_path, mimetype=mime_type)
    uploaded = service.files().create(body=metadata, media_body=media, fields="id").execute()
    print(f"✓ تم الرفع بنجاح! معرّف الملف: {uploaded.get('id')}")

# المسار الرئيسي
async def main():
    data = generate_lesson_content()
    
    txt_filename = f"بيانات_اليوتيوب_درس_{LESSON_NUM}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"العنوان المقترح:\n{data['title']}\n\n")
        f.write(f"الوصف:\n{data['description']}\n\n")
        f.write(f"الكلمات المفتاحية:\n{data['tags']}\n")

    await create_voiceover(data["spoken_script"])
    build_video_with_ffmpeg(data.get("board_summary", ""))

    upload_to_drive("final_video.mp4", f"فيديو_درس_{LESSON_NUM}_{SERIES_NAME}.mp4", "video/mp4")
    upload_to_drive(txt_filename, txt_filename, "text/plain")
    print("🎉 اكتمل خط الإنتاج بنجاح وتم تسليم كافة المخرجات إلى درايف!")

if __name__ == "__main__":
    asyncio.run(main())
