import os
from PIL import Image, ImageDraw

def hex_to_rgb(hex_str):
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join([c * 2 for c in hex_clean])
    return tuple(int(hex_clean[i:i + 2], 16) for i in (0, 2, 4))

# ============================================================
# 1. Sleek Modern Chalkboard Canvas (YouTube Shorts Safe Layout)
# ============================================================
def render_board(theme, filename="chalkboard.png", mirror_ledge=True):
    print("[GRAPHICS] Rendering clean chalkboard canvas without visual clutter (1180x2040)...")
    
    # 2x supersampling for ultra-clean anti-aliased edges
    sw, sh = 1180 * 2, 2040 * 2
    canvas = Image.new("RGBA", (sw, sh), "#0d0b0a")
    draw = ImageDraw.Draw(canvas)

    top_color = hex_to_rgb(theme.get("board_top", "#10231d"))
    bottom_color = hex_to_rgb(theme.get("board_bottom", "#081310"))

    # حل المشكلة 18: دمج إطار الخشب والحدود بدون خطوط صفراء وبنية متلاصقة تسبب زحاماً بصرياً
    # إطار خارجي فخم من خشب الجوز الموحد
    draw.rounded_rectangle([36, 56, sw - 36, sh - 56], radius=32, fill="#1c130d", outline="#2b1c13", width=8)
    
    # سطح اللوح الحجري (Matte Slate Surface)
    gx0, gy0, gx1, gy1 = 64, 84, sw - 64, sh - 84
    slate_h = gy1 - gy0
    for y in range(0, slate_h, 2):
        ratio = y / max(1, slate_h)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(gx0, gy0 + y), (gx1, gy0 + y)], fill=(r, g, b), width=2)

    # حافة داخلية خافتة ورفيعة جداً (Inlay) تفصل السطح عن الخشب بدون تضارب
    draw.rounded_rectangle([gx0, gy0, gx1, gy1], radius=20, outline="#162e26", width=3)

    # رف الطباشير مع مراعاة منطقة الأمان (Safe Boundary Y ≈ 1440px)
    ledge_y = int(1440 * 2)
    ledge_left, ledge_right = 160, sw - 160
    
    # ظل الرف
    draw.rounded_rectangle([ledge_left + 8, ledge_y + 12, ledge_right - 8, ledge_y + 44], radius=10, fill="#05070a")
    # جسم الرف بدون خط ذهبي متزاحم تحته
    draw.rounded_rectangle([ledge_left, ledge_y, ledge_right, ledge_y + 32], radius=8, fill="#2b1a13", outline="#3d2419", width=3)

    # قطع الطباشير
    chalk_w = 64
    offsets = [120, 210, 300]
    chalks = [
        (offsets[0], "#f8fafc"),  # Pure White
        (offsets[1], "#fef08a"),  # Pastel Gold
        (offsets[2], "#67e8f9")   # Pastel Cyan
    ]

    for offset, color in chalks:
        x_pos = (ledge_right - chalk_w - offset) if mirror_ledge else (ledge_left + offset)
        draw.rounded_rectangle([x_pos, ledge_y - 14, x_pos + chalk_w, ledge_y + 4], radius=6, fill=color, outline="#1e293b", width=2)

    final_board = canvas.resize((1180, 2040), Image.Resampling.LANCZOS)
    final_board.save(filename)

# ============================================================
# 2. Modern 2D Vector Character Sprites (Safe & Direction-Aware)
# ============================================================
def render_teacher_poses(persona):
    print(f"[GRAPHICS] Rendering vector character set with calibrated pointer for: {persona['name']}...")
    avatar = persona.get("avatar", {})
    suit_color = avatar.get("suit_color", "#1e3a8a")
    tie_color = avatar.get("tie_color", "#b91c1c")
    hair_color = avatar.get("hair_color", "#26150f")
    glasses_style = avatar.get("glasses", "round")
    skin_tone = "#fcd34d"
    skin_shadow = "#f59e0b"

    def draw_character(mouth_open=False, is_pointing=False, eyes_closed=False, thinking=False):
        cw, ch = 960, 1040
        img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)

        # حل المشكلة 5: تصحيح زاوية المؤشر والذراع ليشير مباشرة نحو وسط اللوح والمعادلة
        if is_pointing:
            # زاوية الذراع الطبيعية نحو وسط الشاشة
            dr.line([(600, 690), (790, 520)], fill=suit_color, width=54)
            dr.ellipse([(760, 490), (820, 550)], fill=skin_tone)
            # المؤشر التلسكوبي ممتد بزاوية ~35 درجة نحو وسط اللوح (وليس لأعلى نحو السقف)
            dr.line([(790, 520), (945, 340)], fill="#e2e8f0", width=10)
            dr.line([(915, 375), (945, 340)], fill="#ffd700", width=12)
            dr.ellipse([(933, 328), (957, 352)], fill="#ffd700")

        # ذراع التفكير
        if thinking and not is_pointing:
            dr.line([(570, 720), (610, 480)], fill=suit_color, width=54)
            dr.ellipse([(580, 440), (640, 500)], fill=skin_tone)
            dr.rounded_rectangle([595, 425, 620, 465], radius=6, fill=skin_tone)

        # الجذع والبدلة
        dr.rounded_rectangle([350, 600, 730, 1040], radius=50, fill=suit_color)
        
        # القميص الأبيض ورابطة العنق
        dr.polygon([(500, 600), (580, 600), (540, 740)], fill="#f8fafc")
        dr.polygon([(532, 630), (548, 630), (554, 820), (540, 850), (526, 820)], fill=tie_color)
        
        # ياقات البدلة
        dr.polygon([(390, 600), (490, 750), (470, 820), (380, 660)], fill="#111827")
        dr.polygon([(690, 600), (590, 750), (610, 820), (700, 660)], fill="#111827")

        # الرقبة
        dr.rectangle([500, 480, 580, 610], fill=skin_shadow)
        dr.rectangle([508, 480, 572, 600], fill=skin_tone)

        # الرأس والفك
        dr.rounded_rectangle([400, 240, 680, 550], radius=85, fill=skin_tone)
        # الأذنان
        dr.ellipse([(380, 360), (416, 420)], fill=skin_tone)
        dr.ellipse([(664, 360), (700, 420)], fill=skin_tone)

        # الشعر
        dr.rounded_rectangle([390, 200, 690, 340], radius=50, fill=hair_color)
        dr.polygon([(390, 310), (430, 360), (420, 300)], fill=hair_color)

        # الحواجب
        brow_y = 330 if not thinking else 315
        dr.line([(450, brow_y), (505, brow_y + (6 if thinking else 0))], fill=hair_color, width=7)
        dr.line([(575, brow_y - (8 if thinking else 0)), (630, brow_y)], fill=hair_color, width=7)

        # النظارات
        if glasses_style == "cateye":
            dr.polygon([(435, 345), (525, 360), (510, 420), (445, 410)], outline="#0f172a", width=8)
            dr.polygon([(645, 345), (555, 360), (570, 420), (635, 410)], outline="#0f172a", width=8)
            dr.line([(520, 375), (560, 375)], fill="#0f172a", width=8)
        elif glasses_style == "square":
            dr.rounded_rectangle([440, 350, 520, 415], radius=8, outline="#0f172a", width=8)
            dr.rounded_rectangle([560, 350, 640, 415], radius=8, outline="#0f172a", width=8)
            dr.line([(520, 380), (560, 380)], fill="#0f172a", width=8)
        else:  # Round
            dr.rounded_rectangle([440, 345, 520, 420], radius=24, outline="#0f172a", width=8)
            dr.rounded_rectangle([560, 345, 640, 420], radius=24, outline="#0f172a", width=8)
            dr.line([(520, 380), (560, 380)], fill="#0f172a", width=8)

        # العيون وبريق النظر نحو اللوح
        if eyes_closed:
            dr.line([(460, 382), (500, 382)], fill="#0f172a", width=6)
            dr.line([(580, 382), (620, 382)], fill="#0f172a", width=6)
        else:
            py_off = -6 if thinking else 0
            dr.ellipse([(465, 368 + py_off), (495, 398 + py_off)], fill="#0f172a")
            dr.ellipse([(585, 368 + py_off), (615, 398 + py_off)], fill="#0f172a")
            dr.ellipse([(472, 372 + py_off), (480, 380 + py_off)], fill="#ffffff")
            dr.ellipse([(592, 372 + py_off), (600, 380 + py_off)], fill="#ffffff")

        # الفم وحركة الكلام (تمهيد المشكلة 4 للـ Lip-sync)
        if mouth_open:
            dr.rounded_rectangle([514, 458, 566, 502], radius=16, fill="#6b1111")
            dr.rounded_rectangle([522, 460, 558, 474], radius=6, fill="#ffffff")  # أسنان علوية واضحة
        else:
            dr.line([(516, 476), (564, 476)], fill="#881313", width=7)

        return img.resize((480, 520), Image.Resampling.LANCZOS)

    # حفظ الوضعيات للاستخدام في Lip-sync ومحرك التجميع
    draw_character(mouth_open=False, is_pointing=False).save("t_idle_closed.png")
    draw_character(mouth_open=True, is_pointing=False).save("t_idle_open.png")
    draw_character(mouth_open=False, is_pointing=True).save("t_point_closed.png")
    draw_character(mouth_open=True, is_pointing=True).save("t_point_open.png")
    draw_character(mouth_open=False, is_pointing=False, thinking=True).save("t_thinking.png")
    draw_character(mouth_open=False, is_pointing=False, eyes_closed=True).save("t_blink.png")

# ============================================================
# 3. Master Visual Engine Entry Point
# ============================================================
def build_all_graphics(persona, content_data, lesson_num=1):
    theme = persona.get("theme", {})
    render_board(theme, mirror_ledge=True)
    render_teacher_poses(persona)
    print("[GRAPHICS] 2026 YouTube Shorts graphics suite compiled successfully.")
