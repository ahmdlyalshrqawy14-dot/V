import os

def hex_to_ass_color(hex_str, alpha="00"):
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join([c * 2 for c in hex_clean])
    if len(hex_clean) == 6:
        r, g, b = hex_clean[0:2], hex_clean[2:4], hex_clean[4:6]
        return f"&H{alpha.upper()}{b.upper()}{g.upper()}{r.upper()}"
    return f"&H{alpha.upper()}FFFFFF"

def escape_ass(text):
    if not text:
        return ""
    clean = str(text).replace("\\", "").replace("{", "(").replace("}", ")")
    return clean.replace("\n", " ").replace("\r", "").strip()

def to_ass_time(sec):
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_master_ass(content_data, timestamps, words_data, persona, font_name="Cairo", output_file="master_video.ass"):
    print("[ASS] Building master typographic script with dynamic palette...")
    
    theme = persona.get("theme", {})
    colors = theme.get("chalk_colors", {})
    watermark_text = persona.get("watermark", "Speed Math Series")

    c_hook = hex_to_ass_color(colors.get("hook", "#ffffff"))
    c_step1 = hex_to_ass_color(colors.get("step1", "#fde047"))
    c_step2 = hex_to_ass_color(colors.get("step2", "#67e8f9"))
    c_res = hex_to_ass_color(colors.get("result", "#4ade80"))
    c_accent = hex_to_ass_color(colors.get("accent", "#f87171"))

    total_duration = timestamps.get("total", 30.0)
    dur_str = to_ass_time(total_duration)

    t_hook = timestamps.get("hook", 0.4)
    t_s1 = timestamps.get("step1", total_duration * 0.25)
    t_s2 = timestamps.get("step2", total_duration * 0.50)
    t_res = timestamps.get("result", total_duration * 0.75)

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{font_name},46,&H008AE0FE,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,2,8,40,40,150,1
Style: Watermark,{font_name},24,&H70FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,55,40,70,1
Style: Hook,{font_name},48,{c_hook},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,3,8,40,40,360,1
Style: Step1,{font_name},44,{c_step1},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,3,8,40,40,540,1
Style: Step2,{font_name},44,{c_step2},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,3,8,40,40,720,1
Style: Result,{font_name},52,{c_res},&H000000FF,&H00064E3B,&H00064E3B,-1,0,0,0,100,100,0,0,3,18,0,8,40,40,920,1
Style: Joke,{font_name},32,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,2,5,40,40,0,1
Style: Captions,{font_name},38,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,40,40,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    bounce_fx = r"\t(0,140,\fscx110\fscy110)\t(140,280,\fscx100\fscy100)"

    # Static persistent header & teacher watermark
    events.append(f"Dialogue: 0,{to_ass_time(0.0)},{dur_str},Title,,0,0,0,,{escape_ass(content_data.get('title', 'Quick Math Hack'))}")
    events.append(f"Dialogue: 0,{to_ass_time(0.0)},{dur_str},Watermark,,0,0,0,,{escape_ass(watermark_text)}")

    # Visual Chalkboard Cards (Time-locked to each audio section)
    events.append(f"Dialogue: 1,{to_ass_time(t_hook)},{dur_str},Hook,,0,0,0,,{{\\fad(260,0){bounce_fx}}}{escape_ass(content_data.get('hook_text', ''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_s1)},{dur_str},Step1,,0,0,0,,{{\\fad(260,0){bounce_fx}}}{escape_ass(content_data.get('step_1', ''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_s2)},{dur_str},Step2,,0,0,0,,{{\\fad(260,0){bounce_fx}}}{escape_ass(content_data.get('step_2', ''))}")
    events.append(f"Dialogue: 1,{to_ass_time(t_res)},{dur_str},Result,,0,0,0,,{{\\fad(260,0){bounce_fx}}}{escape_ass(content_data.get('result_text', ''))}")

    # Sticker Punchline Card (Synced with result arrival)
    events.append(f"Dialogue: 2,{to_ass_time(t_res)},{to_ass_time(t_res + 2.6)},Joke,,0,0,0,,{{\\an5\\pos(340,1200)\\fad(180,180)}}{escape_ass(content_data.get('joke_text', 'Math Wizard!'))}")

    # Fast, high-retention subtitles (2-3 words per display event)
    if words_data:
        chunk_size = 3
        for i in range(0, len(words_data), chunk_size):
            chunk = words_data[i:i + chunk_size]
            s_t = to_ass_time(chunk[0]["start"])
            e_t = to_ass_time(chunk[-1]["end"] + 0.12)
            caption_text = escape_ass(" ".join(w["word"] for w in chunk))
            if caption_text:
                events.append(f"Dialogue: 3,{s_t},{e_t},Captions,,0,0,0,,{caption_text}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))
    print(f"[ASS] Master script rendered successfully: {output_file}")
