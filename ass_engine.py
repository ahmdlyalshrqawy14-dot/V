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
    # حل المشاكل 2 و4: حذف | وحذف ! لمنع خطأ المضروب الرياضي
    clean = str(text).replace("|", "").replace("!", "").replace("\\", "").replace("{", "(").replace("}", ")")
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

# ============================================================
# Kinetic Typography Helpers (YouTube Shorts Optimized)
# ============================================================
GOLD_ASS = "&H0000D7FF"

def build_typewriter_clip(marginv, fontsize, playresx=1080, marginl=80, marginr=240, reveal_ms=500):
    x1 = marginl
    x2_full = playresx - marginr
    y1 = marginv
    line_h = int(fontsize * 1.6)
    y2 = marginv + line_h
    return f"\\clip({x1},{y1},{x1},{y2})\\t(0,{reveal_ms},\\clip({x1},{y1},{x2_full},{y2}))"

def build_rhythmic_pulse(start_ms=280, cycles=5, period_ms=280, amp=5, base=100):
    up = base + amp
    parts = []
    t = start_ms
    for _ in range(cycles):
        t_mid = t + period_ms // 2
        t_end = t + period_ms
        parts.append(f"\\t({t},{t_mid},\\fscx{up}\\fscy{up})\\t({t_mid},{t_end},\\fscx{base}\\fscy{base})")
        t = t_end
    return "".join(parts)

def build_reveal_glow(start_ms=0, peak_ms=250, end_ms=750, base_blur=1, peak_blur=6):
    return (
        f"\\blur{base_blur}"
        f"\\t({start_ms},{peak_ms},\\blur{peak_blur})"
        f"\\t({peak_ms},{end_ms},\\blur{base_blur})"
    )

# ============================================================
# Master ASS Subtitle & Canvas Typography Generator
# ============================================================
def generate_master_ass(content_data, timestamps, words_data, persona, font_name="Cairo", output_file="master_video.ass"):
    print("[ASS] Building YouTube Shorts-safe typographic script...")

    theme = persona.get("theme", {})
    colors = theme.get("chalk_colors", {})

    c_hook = hex_to_ass_color(colors.get("hook", "#ffffff"))
    c_step1 = hex_to_ass_color(colors.get("step1", "#fde047"))
    c_step2 = hex_to_ass_color(colors.get("step2", "#67e8f9"))
    c_res = hex_to_ass_color(colors.get("result", "#4ade80"))

    total_duration = timestamps.get("total", 30.0)
    dur_str = to_ass_time(total_duration)

    t_hook = timestamps.get("hook", 0.4)
    t_s1 = timestamps.get("step1", total_duration * 0.25)
    t_s2 = timestamps.get("step2", total_duration * 0.50)
    t_res = timestamps.get("result", total_duration * 0.75)

    # Styles:
    # حل المشاكل: (2) تكبير الخطوط، (22) تناسق التباعد، (35) استبدال الصندوق المصمت بإطار أنيق، (41) إضافة Spacing: 2 لمنع التصاق الحروف، (1 و33) رفع الترجمة لـ MarginV: 700
    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{font_name},50,&H008AE0FE,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,2,8,80,240,160,1
Style: Hook,{font_name},56,{c_hook},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,3,8,80,240,320,1
Style: Step1,{font_name},54,{c_step1},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,3,8,80,240,480,1
Style: Step2,{font_name},54,{c_step2},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,0,3,8,80,240,640,1
Style: Result,{font_name},60,{c_res},{GOLD_ASS},&H00064E3B,&H00000000,-1,0,0,0,100,100,1,0,1,3,2,8,80,240,800,1
Style: Captions,{font_name},52,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,2,0,1,3,2,2,80,240,700,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    # حل المشكلة 14 و32: إلغاء طبقة اسم المعلم (Watermark) لتنظيف الجزء العلوي من الشاشة ومنع التكدس
    events.append(f"Dialogue: 0,{to_ass_time(0.0)},{dur_str},Title,,0,0,0,,{escape_ass(content_data.get('title', 'Quick Math Hack'))}")

    # حل المشكلة 22: بطاقات متسلسلة بتوزيع رأسي موحد تماماً (فارق 160 بكسل)
    card_specs = [
        (t_hook, "Hook", 320, 56, content_data.get('hook_text', '')),
        (t_s1, "Step1", 480, 54, content_data.get('step_1', '')),
        (t_s2, "Step2", 640, 54, content_data.get('step_2', '')),
    ]
    for t_start, style_name, marginv, fontsize, text in card_specs:
        clean_text = escape_ass(text)
        if clean_text:
            typewriter = build_typewriter_clip(marginv, fontsize, reveal_ms=500)
            pulse = build_rhythmic_pulse(start_ms=550, cycles=4, period_ms=280, amp=5)
            fx = f"{{\\fad(180,0){typewriter}{pulse}}}"
            events.append(f"Dialogue: 1,{to_ass_time(t_start)},{dur_str},{style_name},,0,0,0,,{fx}{clean_text}")

    # Final result reveal card
    clean_res = escape_ass(content_data.get('result_text', ''))
    if clean_res:
        res_typewriter = build_typewriter_clip(800, 60, reveal_ms=400)
        res_glow = build_reveal_glow(start_ms=0, peak_ms=240, end_ms=850, base_blur=1, peak_blur=6)
        res_bounce = (
            r"\t(0,140,\fscx120\fscy120)"
            r"\t(140,280,\fscx96\fscy96)"
            r"\t(280,400,\fscx106\fscy106)"
            r"\t(400,520,\fscx100\fscy100)"
        )
        res_pulse = build_rhythmic_pulse(start_ms=700, cycles=3, period_ms=300, amp=4)
        result_fx = f"{{\\fad(160,0){res_typewriter}{res_glow}{res_bounce}{res_pulse}}}"
        events.append(f"Dialogue: 1,{to_ass_time(t_res)},{dur_str},Result,,0,0,0,,{result_fx}{clean_res}")

    # حل المشاكل: (5 و40) إبراز حركي لكل كلمة (Karaoke Highlight)، (37 و38) تقطيع متزن ومنع التكدس
    if words_data:
        chunk_size = 3
        for i in range(0, len(words_data), chunk_size):
            chunk = words_data[i:i + chunk_size]
            chunk_len = len(chunk)
            for j in range(chunk_len):
                w_start = chunk[j]["start"]
                if j < chunk_len - 1:
                    w_end = chunk[j + 1]["start"]
                else:
                    w_end = chunk[j]["end"] + 0.10
                    if i + chunk_size < len(words_data):
                        w_end = min(w_end, words_data[i + chunk_size]["start"])

                if w_end <= w_start:
                    w_end = w_start + 0.15

                # إبراز الكلمة المنطوقة حالياً باللون الذهبي وتكبيرها قليلاً مع بقاء بقية الكلمات بيضاء
                parts = []
                for k, w_obj in enumerate(chunk):
                    w_text = escape_ass(w_obj["word"])
                    if k == j:
                        parts.append(f"{{\\c&H0000D7FF\\fscx108\\fscy108}}{w_text}{{\\c&H00FFFFFF\\fscx100\\fscy100}}")
                    else:
                        parts.append(f"{{\\c&H00FFFFFF\\fscx100\\fscy100}}{w_text}")

                s_t = to_ass_time(w_start)
                e_t = to_ass_time(w_end)
                line_text = " ".join(parts)
                if line_text:
                    events.append(f"Dialogue: 2,{s_t},{e_t},Captions,,0,0,0,,{line_text}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))
    print(f"[ASS] Typography compiled successfully: {output_file}")
