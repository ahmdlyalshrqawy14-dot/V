import os
import glob
import shutil
import subprocess

def get_duration(file_path):
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
        return 0.0

def create_horizontal_bumper(lesson_num, title, duration=1.2, output_file="bumper.mp4"):
    safe_title = title.replace("'", "").replace('"', '').replace(":", " -")
    
    # تصميم أفقي فاخر 1920x1080 بلمسات ذهبية
    vf = (
        "drawbox=y=0:color=#0f172a:width=iw:height=ih:t=fill,"
        "drawbox=x=160:y=120:w=1600:h=840:color=#ffd700@0.4:t=3,"
        f"drawtext=fontfile=fonts/Cairo-Bold.ttf:text='HACK #{lesson_num:02d}':"
        "fontcolor=#ffd700:fontsize=76:x=(w-text_w)/2:y=(h-text_h)/2-55,"
        f"drawtext=fontfile=fonts/Cairo-Bold.ttf:text='{safe_title}':"
        "fontcolor=#f8fafc:fontsize=38:x=(w-text_w)/2:y=(h-text_h)/2+45"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#0f172a:s=1920x1080:d={duration}",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-t", str(duration),
        "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        output_file
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_file

def convert_vertical_to_horizontal(input_vid, output_vid):
    """
    تحويل الشورتس العمودي إلى شاشة أفقية 1920x1080:
    الفيديو العمودي في المنتصف + خلفية ضبابية سينمائية تملأ الجوانب
    """
    filter_complex = (
        "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,boxblur=25:5,eq=brightness=-0.15[bg];"
        "[0:v]scale=-1:1080[fg];"
        "[bg][fg]overlay=(W-w)/2:0[outv]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", input_vid,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        output_vid
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_vid

def compile_compilation(input_dir="archive", output_file="weekly_compilation.mp4", max_videos=14):
    print("[COMPILER] Searching for uncompiled lessons...")
    video_files = sorted([f for f in glob.glob(os.path.join(input_dir, "*.mp4")) if os.path.isfile(f)])
    
    if not video_files:
        print("[COMPILER] No pending videos found in archive.")
        return

    selected = video_files[:max_videos]
    print(f"[COMPILER] Compiling {len(selected)} lessons into YouTube 16:9 Long-form...")

    concat_list = []
    chapters = []
    current_time = 0.0
    temp_files = []

    for idx, vid in enumerate(selected, 1):
        lesson_name = os.path.splitext(os.path.basename(vid))[0].replace("_", " ").title()
        
        # 1. إنشاء الفاصل الأفقي السريع
        bumper_file = f"temp_bumper_{idx}.mp4"
        create_horizontal_bumper(idx, lesson_name, duration=1.2, output_file=bumper_file)
        temp_files.append(bumper_file)

        # 2. تحويل الشورتس الأصلي إلى فيديو أفقي بجوانب سينمائية
        h_vid = f"temp_h_{idx}.mp4"
        convert_vertical_to_horizontal(vid, h_vid)
        temp_files.append(h_vid)

        # 3. توثيق وقت الفصل لوصف اليوتيوب
        minutes = int(current_time // 60)
        seconds = int(current_time % 60)
        chapters.append(f"{minutes:02d}:{seconds:02d} - Hack #{idx:02d}: {lesson_name}")

        concat_list.append(bumper_file)
        concat_list.append(h_vid)
        current_time += get_duration(bumper_file) + get_duration(h_vid)

    manifest = "concat_list.txt"
    with open(manifest, "w", encoding="utf-8") as f:
        for item in concat_list:
            f.write(f"file '{os.path.abspath(item)}'\n")

    print("[COMPILER] Merging all segments and mastering audio loudness...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", manifest,
        "-af", "loudnorm=I=-14:LRA=11:TP=-1.5",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        output_file
    ]
    subprocess.run(cmd, check=True)

    with open("compilation_chapters.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(chapters))

    print(f"[COMPILER] Master compilation ready: {output_file}")
    print("[COMPILER] YouTube chapters exported to compilation_chapters.txt")

    # أرشفة الفيديوهات المدمجة حتى لا تتكرر في التجميعات القادمة
    compiled_folder = os.path.join(input_dir, "compiled")
    os.makedirs(compiled_folder, exist_ok=True)
    for vid in selected:
        shutil.move(vid, os.path.join(compiled_folder, os.path.basename(vid)))

    # تنظيف الملفات المؤقتة
    for temp in temp_files:
        if os.path.exists(temp):
            try: os.remove(temp)
            except Exception: pass
    if os.path.exists(manifest):
        os.remove(manifest)

if __name__ == "__main__":
    compile_compilation()
