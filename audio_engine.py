import os
import re
import asyncio
import subprocess
import functools
import edge_tts

SAMPLE_RATE = 44100

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

@functools.lru_cache(maxsize=1)
def _has_rubberband_filter():
    try:
        res = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True, timeout=10)
        return "rubberband" in res.stdout
    except Exception:
        return False

def _get_native_sample_rate(file_path):
    # تصحيح الثغرة: نقرأ معدل العينة الحقيقي للملف بدل افتراض 44100
    # (edge-tts بيخرج الصوت افتراضيًا بمعدل 24kHz، مش 44100)
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return int(res.stdout.strip())
    except Exception:
        return SAMPLE_RATE  # قيمة احتياطية أخيرة لو فشلت القراءة

async def synthesize_raw_chunk(text, voice_model, raw_output_path, rate="-10%"):
    # تنظيف الرموز الخاصة مع الإبقاء على علامات الترقيم الطبيعية للحفاظ على نبرة الإلقاء
    clean = re.sub(r'["\'`*_\~<>{}[\]\\/^$|!]', ' ', str(text))
    clean = " ".join(clean.split()).strip()
    words = []

    for attempt in range(3):
        try:
            comm = edge_tts.Communicate(clean, voice_model, rate=rate)
            with open(raw_output_path, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        words.append({
                            "start": chunk["offset"] / 10_000_000.0,
                            "end": (chunk["offset"] + chunk["duration"]) / 10_000_000.0,
                            "word": chunk["text"]
                        })
            if os.path.exists(raw_output_path) and os.path.getsize(raw_output_path) > 1000:
                break
        except Exception as e:
            print(f"[WARN] Edge-TTS attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(1)

    if not os.path.exists(raw_output_path) or os.path.getsize(raw_output_path) < 1000:
        raise RuntimeError(f"[FATAL] Failed to synthesize audio chunk: {clean[:30]}")

    dur = get_audio_duration(raw_output_path)
    return words, dur, clean

def apply_vocal_dsp(input_path, output_path, dsp_config):
    pitch_semitones = float(dsp_config.get("pitch_shift", 0.0))
    chest_gain = float(dsp_config.get("chest_eq_gain", 3.0))
    presence_gain = float(dsp_config.get("presence_eq_gain", -3.0))

    pitch_ratio = 2.0 ** (pitch_semitones / 12.0)

    # --- تصحيح جوهري: الحفاظ على الفورمانت (بصمة الصوت) عند تغيير النغمة ---
    if abs(pitch_semitones) > 0.001 and _has_rubberband_filter():
        pitch_filter = f"rubberband=pitch={pitch_ratio:.6f}:formant=preserved:pitchq=quality"
    elif abs(pitch_semitones) > 0.001:
        # شبكة أمان: لو rubberband مش متاح في بيئة التشغيل
        # تصحيح الثغرة: نستخدم معدل العينة الحقيقي للملف المدخل، مش رقم ثابت مفترض
        native_rate = _get_native_sample_rate(input_path)
        resample_rate = int(native_rate * pitch_ratio)
        pitch_filter = (
            f"asetrate={resample_rate},aresample={SAMPLE_RATE},"
            f"atempo={1.0 / pitch_ratio:.4f}"
        )
    else:
        pitch_filter = None

    filters = []
    if pitch_filter:
        filters.append(pitch_filter)

    filters += [
        "highpass=f=80",
        # EQ بشكل shelf بدل peaking الحاد: صوت أنعم وأطبع، بدون رنين معدني
        f"bass=g={chest_gain}:f=220:w=0.6",
        f"treble=g={presence_gain}:f=3200:w=0.6",
        # de-esser بسيط لتفادي صفير الحروف الصفيرية لو رفعنا الـ presence
        "deesser=i=0.35:m=0.5:f=0.5:s=o",
        "compand=attacks=0.02:decays=0.15:points=-80/-80|-35/-18|-10/-8|0/-3:gain=1.0",
        # تطبيع صوتي بمعيار الشورتس/تيك توك (-14 LUFS)
        "loudnorm=I=-14:TP=-1.5:LRA=11"
    ]

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", ",".join(filters),
        "-ar", str(SAMPLE_RATE),
        "-c:a", "libmp3lame",
        "-q:a", "3",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

async def build_complete_voiceover(content_data, persona):
    print(f"[AUDIO] Synthesizing broadcast audio for: {persona['name']}...")
    voice_config = persona.get("voice", {})
    voice_model = voice_config.get("model", "en-GB-RyanNeural")
    dsp_config = voice_config.get("dsp", {})

    # سرعات متغيرة حسب طبيعة كل جزء لإيقاع أنسب لفيديوهات الشورتس
    sections = [
        ("hook",   content_data.get("spoken_hook", ""),   "+0%"),
        ("step1",  content_data.get("spoken_step1", ""),  "+0%"),
        ("step2",  content_data.get("spoken_step2", ""),  "+0%"),
        ("result", content_data.get("spoken_result", ""), "+0%")
    ]

    all_words = []
    timestamps = {}
    current_time = 0.35
    processed_files = []

    # فاصل قصير بين الأجزاء يناسب إيقاع الشورتس السريع
    pause_duration = 0.45
    silence_file = "silence_pause.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono", "-t", str(pause_duration), "-c:a", "libmp3lame", silence_file],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

    concat_inputs = []

    for i, (key, script_text, rate_val) in enumerate(sections):
        raw_file = f"raw_{key}.mp3"
        dsp_file = f"dsp_{key}.mp3"

        words, raw_dur, clean_txt = await synthesize_raw_chunk(script_text, voice_model, raw_file, rate=rate_val)
        apply_vocal_dsp(raw_file, dsp_file, dsp_config)
        dsp_dur = get_audio_duration(dsp_file)

        time_scale = (dsp_dur / raw_dur) if raw_dur > 0 else 1.0

        processed_files.append(dsp_file)
        concat_inputs.append(dsp_file)
        timestamps[key] = round(current_time, 2)

        if words:
            for w in words:
                all_words.append({
                    "start": round((w["start"] * time_scale) + current_time, 2),
                    "end": round((w["end"] * time_scale) + current_time, 2),
                    "word": w["word"]
                })
        else:
            w_list = clean_txt.split()
            step_dur = dsp_dur / max(1, len(w_list))
            for idx, wrd in enumerate(w_list):
                all_words.append({
                    "start": round(current_time + (idx * step_dur), 2),
                    "end": round(current_time + ((idx + 1) * step_dur), 2),
                    "word": wrd
                })

        current_time += dsp_dur
        if i < len(sections) - 1:
            concat_inputs.append(silence_file)
            current_time += pause_duration

    input_args = []
    for f in concat_inputs:
        input_args.extend(["-i", f])

    n = len(concat_inputs)
    concat_filter = "".join([f"[{j}:a]" for j in range(n)]) + f"concat=n={n}:v=0:a=1[v_raw];"

    total_dur = current_time
    fade_start = max(0.1, round(total_dur - 0.25, 2))

    final_audio_filter = (
        f"{concat_filter}"
        f"anoisesrc=d={total_dur + 0.2}:c=pink:r={SAMPLE_RATE}:a=0.002,lowpass=f=1200[room];"
        f"[v_raw][room]amix=inputs=2:duration=first:dropout_transition=0[mixed];"
        f"[mixed]afade=t=out:st={fade_start}:d=0.25,alimiter=limit=-1.5dB[outa]"
    )

    concat_cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", final_audio_filter,
        "-map", "[outa]",
        "-c:a", "libmp3lame",
        "-q:a", "3",
        "voice.mp3"
    ]
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    for f in processed_files:
        raw_f = f.replace("dsp_", "raw_")
        if os.path.exists(f): os.remove(f)
        if os.path.exists(raw_f): os.remove(raw_f)
    if os.path.exists(silence_file): os.remove(silence_file)

    total_dur = get_audio_duration("voice.mp3") + 0.05
    timestamps["total"] = round(total_dur, 2)
    print(f"[AUDIO] Voiceover synthesized successfully ({timestamps['total']:.2f}s).")

    return timestamps, all_words

def generate_ambient_bgm(duration):
    """
    بديل احتياطي لو فشل تحميل موسيقى الخلفية من الإنترنت.
    بيولّد سرير صوتي هادئ (ambient pad) بدل الصمت الكامل، بمدة مطابقة للمطلوب.
    """
    print(f"[AUDIO] Generating fallback ambient BGM ({duration:.2f}s)...")
    filter_chain = (
        f"anoisesrc=d={duration:.2f}:c=pink:r={SAMPLE_RATE}:a=0.02,"
        "lowpass=f=800,highpass=f=150,"
        "afade=t=in:st=0:d=1.0,"
        f"afade=t=out:st={max(0.5, duration - 1.0):.2f}:d=1.0"
    )
    cmd = [
        "ffmpeg", "-y",
        "-filter_complex", filter_chain,
        "-ac", "2",
        "-ar", str(SAMPLE_RATE),
        "-c:a", "pcm_s16le",
        "bgm.wav"
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("[AUDIO] Ambient BGM fallback ready: bgm.wav")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[AUDIO WARN] Ambient BGM generation failed: {e}")
        return False
