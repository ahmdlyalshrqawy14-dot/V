import os
import random
from PIL import Image, ImageDraw

def hex_to_rgb(hex_str):
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join([c * 2 for c in hex_clean])
    return tuple(int(hex_clean[i:i + 2], 16) for i in (0, 2, 4))

def render_board(theme, filename="chalkboard.png"):
    print("[GRAPHICS] Rendering theme-tailored chalkboard canvas (1180x2040)...")
    board = Image.new("RGBA", (1180, 2040), "#2a1810")
    draw = ImageDraw.Draw(board)

    border_outer = theme.get("border_outer", "#3c2211")
    border_inner = theme.get("border_inner", "#1f120a")
    top_color = hex_to_rgb(theme.get("board_top", "#16382c"))
    bottom_color = hex_to_rgb(theme.get("board_bottom", "#0b1f18"))

    # Outer wooden framing
    draw.rectangle([20, 35, 1160, 2005], fill=border_outer)
    draw.rectangle([45, 60, 1135, 1980], fill=border_inner)

    # Vertical gradient chalkboard slate
    gx0, gy0, gx1, gy1 = 55, 70, 1125, 1960
    slate_height = gy1 - gy0
    for y in range(slate_height):
        ratio = y / max(1, slate_height)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(gx0, gy0 + y), (gx1, gy0 + y)], fill=(r, g, b))

    # Inner chalk slate outline
    draw.rectangle([gx0, gy0, gx1, gy1], outline="#d1d5db", width=2)

    # Bottom wooden chalk ledge
    draw.rectangle([90, 1920, 1090, 1946], fill="#5c2e14", outline="#2b1407", width=2)

    # Resting chalk pieces (White, Yellow, Cyan)
    chalks = [
        (160, "#ffffff"),
        (210, "#fde047"),
        (260, "#67e8f9")
    ]
    for x_pos, chalk_col in chalks:
        draw.rounded_rectangle([x_pos, 1913, x_pos + 38, 1924], radius=3, fill=chalk_col)

    board.save(filename)

def render_teacher_poses(persona):
    print(f"[GRAPHICS] Generating teacher sprite set for: {persona['name']}...")
    avatar = persona.get("avatar", {})
    suit_color = avatar.get("suit_color", "#1e3a8a")
    tie_color = avatar.get("tie_color", "#b91c1c")
    hair_color = avatar.get("hair_color", "#3b2219")
    glasses_style = avatar.get("glasses", "round")

    def draw_character(mouth_open=False, is_pointing=False):
        img = Image.new("RGBA", (480, 520), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)

        # Pointing arm with wooden pointer stick
        if is_pointing:
            # Arm
            dr.line([(200, 340), (70, 200)], fill=suit_color, width=28)
            # Hand
            dr.ellipse([(55, 185), (85, 215)], fill="#fed7aa")
            # Wooden pointer stick extending upward onto board
            dr.line([(70, 200), (20, 60)], fill="#d97706", width=7)
            # Metallic/glowing pointer tip
            dr.ellipse([(14, 52), (26, 68)], fill="#fbbf24")

        # Body torso / Suit jacket
        dr.rectangle([180, 310, 350, 510], fill=suit_color)

        # Shirt collar / Tie
        dr.polygon([(265, 310), (245, 370), (265, 430), (285, 370)], fill=tie_color)

        # Head / Skin
        dr.ellipse([190, 130, 340, 290], fill="#fed7aa")

        # Hair
        dr.chord([188, 110, 342, 215], 180, 360, fill=hair_color)

        # Eyewear Rendering
        if glasses_style == "round":
            dr.ellipse([210, 175, 255, 215], outline="#0f172a", width=4)
            dr.ellipse([275, 175, 320, 215], outline="#0f172a", width=4)
            dr.line([255, 195, 275, 195], fill="#0f172a", width=4)
        elif glasses_style == "cateye":
            dr.polygon([(205, 175), (255, 185), (245, 215), (210, 210)], outline="#0f172a", width=4)
            dr.polygon([(325, 175), (275, 185), (285, 215), (320, 210)], outline="#0f172a", width=4)
            dr.line([255, 190, 275, 190], fill="#0f172a", width=4)
        else:  # Square / Minimal
            dr.rectangle([210, 180, 255, 210], outline="#0f172a", width=4)
            dr.rectangle([275, 180, 320, 210], outline="#0f172a", width=4)
            dr.line([255, 195, 275, 195], fill="#0f172a", width=4)

        # Eyes pupils
        dr.ellipse([228, 188, 238, 198], fill="#0f172a")
        dr.ellipse([292, 188, 302, 198], fill="#0f172a")

        # Mouth (Dynamic speaking state)
        if mouth_open:
            dr.ellipse([250, 240, 280, 268], fill="#881337")
        else:
            dr.line([250, 252, 280, 252], fill="#881337", width=4)

        return img

    draw_character(mouth_open=False, is_pointing=False).save("t_idle_closed.png")
    draw_character(mouth_open=True, is_pointing=False).save("t_idle_open.png")
    draw_character(mouth_open=False, is_pointing=True).save("t_point_closed.png")
    draw_character(mouth_open=True, is_pointing=True).save("t_point_open.png")

def render_reaction_sticker(effect_type="shock", filename="sticker_active.png"):
    stk = Image.new("RGBA", (520, 160), (0, 0, 0, 0))
    d_stk = ImageDraw.Draw(stk)
    bg_color = "#dc2626" if effect_type == "shock" else "#059669"

    # Soft ambient drop shadow
    d_stk.rounded_rectangle([18, 18, 508, 148], radius=22, fill=(15, 23, 42, 160))
    # Raised surface card
    d_stk.rounded_rectangle([10, 10, 500, 140], radius=22, fill=bg_color, outline="#ffffff", width=4)
    stk.save(filename)

def render_dust_layer(lesson_seed=1, filename="dust.png"):
    tile_w, h = 1080, 1920
    tile = Image.new("RGBA", (tile_w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(tile)
    random.seed(int(lesson_seed) if str(lesson_seed).isdigit() else 1)

    for _ in range(55):
        x = random.randint(0, tile_w)
        y = random.randint(0, h)
        radius = random.randint(1, 3)
        alpha = random.randint(20, 65)
        dr.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(255, 255, 255, alpha))

    # Join 2 identical tiles side-by-side for seamless horizontal scrolling
    dust = Image.new("RGBA", (tile_w * 2, h), (0, 0, 0, 0))
    dust.paste(tile, (0, 0))
    dust.paste(tile, (tile_w, 0))
    dust.save(filename)

def build_all_graphics(persona, content_data, lesson_num=1):
    theme = persona.get("theme", {})
    effect_type = content_data.get("effect_type", "shock")

    render_board(theme)
    render_teacher_poses(persona)
    render_reaction_sticker(effect_type)
    render_dust_layer(lesson_seed=lesson_num)
    print("[GRAPHICS] All visual layers compiled successfully.")
