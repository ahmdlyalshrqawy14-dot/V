import os
import sys
import glob
import json
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

def create_bumper(lesson_num, title, duration=2.5, output_file="bumper.mp4"):
    safe_title = title.replace("'", "").replace('"', '').replace(":", " -")
    vf = (
        f"drawbox=y=0:color=#0b1f18:width=iw:height=ih:t=fill,"
        f"drawtext=fontfile=fonts/Cairo-Bold.ttf:text='HACK #{lesson_num:02d}':fontcolor=#facc15:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2-60,"
        f"drawtext=fontfile=fonts/Cairo-Bold.ttf:text='{safe_title}':fontcolor=#ffffff:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2+40"
    )
    cmd = (
        f'ffmpeg -y -f lavfi -i color=c=#0b1f18:s=1080x1920:d={duration} '
        f'-f lavfi -i anullsrc=r=24000:cl=mono '
        f'-vf "{vf}" -c:v libx264 -t {duration} -c:a aac -pix_fmt yuv420p {output_file}'
    )
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_file

def compile_compilation(input_dir="archive", output_file="weekly_compilation.mp4", max_videos=10):
    print("[COMPILER] Searching for produced shorts to compile...")
    video_files = sorted(glob.glob(os.path.join(input_dir, "*.mp4")))
    
    if not video_files:
        print("[COMPILER] No archived videos found in target folder.")
        return

    selected = video_files[:max_videos]
    print(f"[COMPILER] Compiling {len(selected)} lessons into long-form video...")

    concat_list = []
    chapters = []
    current_time = 0.0

    for idx, vid in enumerate(selected, 1):
        lesson_name = os.path.splitext(os.path.basename(vid))[0]
        bumper_file = f"temp_bumper_{idx}.mp4"
        create_bumper(idx, lesson_name, duration=2.2, output_file=bumper_file)

        b_dur = get_duration(bumper_file)
        v_dur = get_duration(vid)

        minutes = int(current_time // 60)
        seconds = int(current_time % 60)
        chapters.append(f"{minutes:02d}:{seconds:02d} - Hack #{idx:02d}: {lesson_name}")

        concat_list.append(bumper_file)
        concat_list.append(vid)
        current_time += b_dur + v_dur

    # Write concat manifest
    manifest = "concat_list.txt"
    with open(manifest, "w", encoding="utf-8") as f:
        for item in concat_list:
            f.write(f"file '{os.path.abspath(item)}'\n")

    # Render compilation with EBU R128 (-14 LUFS) normalization
    cmd = (
        f'ffmpeg -y -f concat -safe 0 -i {manifest} '
        f'-af "loudnorm=I=-14:LRA=11:TP=-1.5" '
        f'-c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k {output_file}'
    )
    subprocess.run(cmd, shell=True, check=True)

    # Save chapter markers for YouTube Description
    with open("compilation_chapters.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(chapters))

    print(f"[COMPILER] Compilation generated: {output_file}")
    print(f"[COMPILER] Chapters exported to compilation_chapters.txt")

    # Cleanup bumpers
    for b in glob.glob("temp_bumper_*.mp4"):
        try: os.remove(b)
        except Exception: pass
    if os.path.exists(manifest):
        os.remove(manifest)

if __name__ == "__main__":
    compile_compilation()
