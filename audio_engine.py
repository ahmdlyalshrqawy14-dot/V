import os
import re
import asyncio
import subprocess
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

async def synthesize_raw_chunk(text, voice_model, raw_output_path):
    # حل المشكلة 2: حذف حرف | الزائد المسبب للمربعات مع علامات التنسيق
    clean = re.sub(r'["\'`*_~<>{}[\]\\/^$|]', ' ', str(text))
    clean = " ".join(clean.split()).strip()
    words = []
    
    for attempt in range(3):
        try:
            # حل المشكلة 14: تبطيء صوت الـ TTS بنسبة -11%
            comm = edge_tts.Communicate(clean, voice_model, rate="-11%")
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
    # القيم الأصلية بالكامل دون أي تعديل
    pitch_semitones = float(dsp_config.get("pitch_shift", 0.0))
    chest_gain = float(dsp_config.get("chest_eq_gain", 3.0))
    presence_gain = float(dsp_config.get("presence_eq_gain", -3.0))

    pitch_ratio = 2.0 ** (pitch_semitones / 12.0)
    resample_rate = int(SAMPLE_RATE * pitch_ratio)

    filters = [
        f"asetrate={resample_rate}",
        f"aresample={SAMPLE_RATE}",
        f"atempo={1.0 / pitch_ratio:.4f}",
        f"equalizer=f=160:t=q:w=1.4:g={chest_gain}",
        f"equalizer=f=8000:t=q:w=2.0:g={presence_gain}",
        "compand=attacks=0.02:decays=0.2:points=-80/-80|-35/-20|-10/-10|0/-5:gain=2"
    ]

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", ",".join(filters),
        "-ar", str(SAMPLE_RATE),
        "-c:a", "libmp3lame",
        "-q:a", "2",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

async def build_complete_voiceover(content_data, persona):
    print(f"[AUDIO] Synthesizing broadcast audio for: {persona['name']}...")
    voice_config = persona.get("voice", {})
    voice_model = voice_config.get("model", "en-GB-RyanNeural")
    dsp_config = voice_config.get("dsp", {})

    sections = [
        ("hook", content_data.get("spoken_hook", "")),
        ("step1", content_data.get("spoken_step1", "")),
        ("step2", content_data.get("spoken_step2", "")),
        ("result", content_data.get("spoken_result", ""))
    ]

    all_words = []
    timestamps = {}
    current_time = 0.35
    processed_files = []

    # توليد ملف صمت حقيقي لمنع ترحيل الترجمة
    silence_file = "silence_pause.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono", "-t", "0.85", "-c:a", "libmp3lame", silence_file],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

    concat_inputs = []

    for i, (key, script_text) in enumerate(sections):
        raw_file = f"raw_{key}.mp3"
        dsp_file = f"dsp_{key}.mp3"

        words, raw_dur, clean_txt = await synthesize_raw_chunk(script_text, voice_model, raw_file)
        apply_vocal_dsp(raw_file, dsp_file, dsp_config)
        dur = get_audio_duration(dsp_file)

        processed_files.append(dsp_file)
        concat_inputs.append(dsp_file)
        timestamps[key] = round(current_time, 2)

        if words:
            for w in words:
                all_words.append({
                    "start": round(w["start"] + current_time, 2),
                    "end": round(w["end"] + current_time, 2),
                    "word": w["word"]
                })
        else:
            w_list = clean_txt.split()
            step_dur = dur / max(1, len(w_list))
            for idx, wrd in enumerate(w_list):
                all_words.append({
                    "start": round(current_time + (idx * step_dur), 2),
                    "end": round(current_time + ((idx + 1) * step_dur), 2),
                    "word": wrd
                })

        # حل المشكلة 15: زيادة الفاصل بين الخطوات من 0.25 ثانية إلى 0.85 ثانية
        current_time += dur
        if i < len(sections) - 1:
            concat_inputs.append(silence_file)
            current_time += 0.85

    input_args = []
    for f in concat_inputs:
        input_args.extend(["-i", f])

    n = len(concat_inputs)
    concat_filter = f"".join([f"[{j}:a]" for j in range(n)]) + f"concat=n={n}:v=0:a=1[v_raw];"
    
    total_dur = current_time
    fade_start = max(0.1, round(total_dur - 0.7, 2))

    # حل المشاكل: (12) دمج Room tone خافت، (11) منع وصول الصوت لـ 0dB، (10) عمل Fade out
    final_audio_filter = (
        f"{concat_filter}"
        f"anoisesrc=d={total_dur + 0.5}:c=pink:r={SAMPLE_RATE}:a=0.0008,lowpass=f=1200[room];"
        f"[v_raw][room]amix=inputs=2:duration=first:dropout_transition=0[mixed];"
        f"[mixed]alimiter=limit=-1.5dB,afade=t=out:st={fade_start}:d=0.7[outa]"
    )

    concat_cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", final_audio_filter,
        "-map", "[outa]",
        "-c:a", "libmp3lame",
        "-q:a", "2",
        "voice.mp3"
    ]
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # تنظيف الملفات المؤقتة
    for f in processed_files:
        raw_f = f.replace("dsp_", "raw_")
        if os.path.exists(f): os.remove(f)
        if os.path.exists(raw_f): os.remove(raw_f)
    if os.path.exists(silence_file): os.remove(silence_file)

    total_dur = get_audio_duration("voice.mp3") + 0.4
    timestamps["total"] = round(total_dur, 2)
    print(f"[AUDIO] Voiceover synthesized successfully ({timestamps['total']:.2f}s).")

    return timestamps, all_words
