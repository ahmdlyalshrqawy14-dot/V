import os
import re
import wave
import math
import struct
import subprocess
import asyncio
import edge_tts
from gtts import gTTS

SAMPLE_RATE = 24000

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

def generate_sfx():
    print("[AUDIO] Generating micro-SFX suite...")
    
    # 1. Bell ding (Success / Insight)
    with wave.open("ding.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SAMPLE_RATE)
        data = [
            struct.pack('<h', int(32767 * 0.45 * math.sin(2 * math.pi * 987.77 * (i / SAMPLE_RATE)) * math.exp(-6 * (i / SAMPLE_RATE))))
            for i in range(12000)
        ]
        f.writeframes(b''.join(data))

    # 2. Low impact boom (Climax / Shock)
    with wave.open("boom.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SAMPLE_RATE)
        data = [
            struct.pack('<h', int(32767 * 0.65 * math.sin(2 * math.pi * max(45, 140 - 110 * (i / SAMPLE_RATE)) * (i / SAMPLE_RATE)) * math.exp(-3 * (i / SAMPLE_RATE))))
            for i in range(19200)
        ]
        f.writeframes(b''.join(data))

    # 3. Subtle chalk tap (Micro-event for number appearance)
    with wave.open("chalk_tap.wav", "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SAMPLE_RATE)
        data = [
            struct.pack('<h', int(32767 * 0.3 * math.sin(2 * math.pi * 650 * (i / SAMPLE_RATE)) * math.exp(-35 * (i / SAMPLE_RATE))))
            for i in range(1500)
        ]
        f.writeframes(b''.join(data))

def generate_ambient_bgm(duration, output_file="bgm.wav"):
    if os.path.exists(output_file):
        return output_file
    print(f"[AUDIO] Generating custom ambient BGM track ({duration:.2f}s)...")
    total_samples = int(duration * SAMPLE_RATE)
    chords = [
        [130.81, 164.81, 196.00, 246.94], # Cmaj7
        [110.00, 130.81, 164.81, 196.00], # Am7
        [87.31,  110.00, 130.81, 164.81], # Fmaj7
        [98.00,  123.47, 146.83, 174.61], # G7
    ]
    with wave.open(output_file, "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SAMPLE_RATE)
        data = []
        chord_len = int(SAMPLE_RATE * 3.5)
        for i in range(total_samples):
            t = i / SAMPLE_RATE
            chord_idx = (i // chord_len) % len(chords)
            sample_val = sum(math.sin(2 * math.pi * freq * t) for freq in chords[chord_idx])
            sample_val = (sample_val / len(chords[chord_idx])) * 0.12
            envelope = min(1.0, t / 1.5) * min(1.0, (duration - t) / 1.5)
            val = int(32767 * sample_val * envelope)
            data.append(struct.pack('<h', max(-32767, min(32767, val))))
        f.writeframes(b''.join(data))
    return output_file

async def synthesize_raw_chunk(text, voice_model, raw_output_path):
    clean = re.sub(r'["\'`*_~<>{}[\]\\/+=^$]', ' ', str(text))
    clean = " ".join(clean.split()).strip()
    words = []
    
    try:
        comm = edge_tts.Communicate(clean, voice_model)
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
    except Exception as e:
        print(f"[WARN] Edge-TTS failed for chunk, falling back to gTTS: {e}")
        tts = gTTS(text=clean, lang="en")
        tts.save(raw_output_path)

    dur = get_audio_duration(raw_output_path)
    return words, dur, clean

def apply_vocal_dsp(input_path, output_path, dsp_config):
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

    filter_str = ",".join(filters)
    cmd = (
        f'ffmpeg -y -i "{input_path}" '
        f'-af "{filter_str}" -ar {SAMPLE_RATE} -ac 1 -c:a libmp3lame -q:a 2 "{output_path}"'
    )
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def build_complete_voiceover(content_data, persona):
    print(f"[AUDIO] Synthesizing full broadcast audio with persona: {persona['name']}...")
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

    for key, script_text in sections:
        raw_file = f"raw_{key}.mp3"
        dsp_file = f"dsp_{key}.mp3"

        words, raw_dur, clean_txt = await synthesize_raw_chunk(script_text, voice_model, raw_file)
        apply_vocal_dsp(raw_file, dsp_file, dsp_config)
        dur = get_audio_duration(dsp_file)

        processed_files.append(dsp_file)
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

        current_time += dur + 0.25

    filter_inputs = "".join([f"[{i}:a]" for i in range(len(processed_files))])
    concat_cmd = (
        f'ffmpeg -y '
        f'{" ".join([f"-i {f}" for f in processed_files])} '
        f'-filter_complex "{filter_inputs}concat=n={len(processed_files)}:v=0:a=1[outa]" '
        f'-c:a libmp3lame -q:a 2 voice.mp3'
    )
    subprocess.run(concat_cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    total_dur = get_audio_duration("voice.mp3") + 0.4
    timestamps["total"] = round(total_dur, 2)
    print(f"[AUDIO] Audio production finished. Total duration: {timestamps['total']:.2f}s")

    return timestamps, all_words
