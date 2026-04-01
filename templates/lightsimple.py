"""
Manga Cruise Poster Generator (Fixed)

Updates:
- READ NOW button text split (Red/White)
- Correct overlap of FAB over Middle Carousel Image
- Tighter vertical spacing for Bottom Nav
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Canvas Size ───
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080

# ─── Layout Dimensions ───
LEFT_PANEL_WIDTH = 960                   # Left panel width (50%)
CONTENT_PADDING = 64

# ─── Colors (RGB tuples) ───
BG_WHITE = (255, 255, 255)
BG_DARK = (20, 20, 25)                   # Pitch black/dark for nav
TEXT_BLACK = (22, 22, 25)
TEXT_GRAY = (120, 120, 130)
ACCENT_RED = (230, 40, 50)               # Vibrant Red
DIVIDER_GRAY = (180, 180, 185)           # Darker for visibility

# ─── Typography ───
FONT_TITLE_SIZE = 72
FONT_DESC_SIZE = 24
FONT_BUTTON_SIZE = 20

# ─── Output ───
OUTPUT_FORMAT = "JPEG"
OUTPUT_QUALITY = 95

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import textwrap
from pathlib import Path


# Project imports
# Project imports
from poster_utils import _pb_get_fonts as get_fonts  # patched
from poster_utils import load_image, load_icon, colorize_icon, add_corners  # patched

# ─── Paths ───
# (No local paths needed for template execution)

try:
    GOOGLE_FONTS = get_fonts()
except:
    GOOGLE_FONTS = {}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    try:
        if weight == "bold":
            font_path = GOOGLE_FONTS.get("Poppins-Bold", "arialbd.ttf")
        elif weight == "extra-bold":
            font_path = GOOGLE_FONTS.get("BebasNeue-Bold", "arialbd.ttf")
        elif weight == "medium":
            font_path = GOOGLE_FONTS.get("Poppins-Medium", "arial.ttf")
        else:
            font_path = GOOGLE_FONTS.get("Poppins-Regular", "arial.ttf")
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

def create_left_gradient(width: int, height: int) -> Image.Image:
    """Create a smooth teal-to-transparent gradient."""
    import numpy as np
    result = np.zeros((height, width, 4), dtype=np.uint8)
    teal = (5, 80, 90) # Dark Teal
    
    for y in range(height):
        progress = y / float(height)
        if progress > 0.4:
            alpha = int(255 * ((progress - 0.4) / 0.6) ** 1.5)
            alpha = min(220, alpha)
        else:
            alpha = 0
            
        result[y, :, 0] = teal[0]
        result[y, :, 1] = teal[1]
        result[y, :, 2] = teal[2]
        result[y, :, 3] = alpha

    return Image.fromarray(result, 'RGBA')

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def create_poster(manga_data):
    WIDTH, HEIGHT = CANVAS_WIDTH, CANVAS_HEIGHT
    
    # 1. Base Canvas
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG_WHITE)
    draw = ImageDraw.Draw(canvas)

    # ═══════════════════════════════════════════════════════════════════════════
    # LEFT PANEL (Image & Gradient)
    # ═══════════════════════════════════════════════════════════════════════════
    
    cover_url = None
    if isinstance(manga_data.get('coverImage'), dict):
        cover_url = manga_data['coverImage'].get('extraLarge') or manga_data['coverImage'].get('large')
    else:
        cover_url = manga_data.get('coverImage')

    if cover_url:
        cover = load_image(cover_url)
        if cover:
            img_w, img_h = cover.size
            ratio = max(LEFT_PANEL_WIDTH / img_w, HEIGHT / img_h)
            new_w, new_h = int(img_w * ratio), int(img_h * ratio)
            cover = cover.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            left = (new_w - LEFT_PANEL_WIDTH) // 2
            cover = cover.crop((left, 0, left + LEFT_PANEL_WIDTH, HEIGHT))
            canvas.paste(cover, (0, 0))

            gradient = create_left_gradient(LEFT_PANEL_WIDTH, HEIGHT)
            canvas.paste(gradient, (0, 0), gradient)

    # Left Panel Text
    draw = ImageDraw.Draw(canvas)
    desc = manga_data.get('description', '') or ''
    desc = ""
    # Try to get main character description for left panel
    main_edges = manga_data.get('characters', {}).get('edges', [])
    if main_edges:
        char_node = main_edges[0].get('node', {})
        desc = char_node.get('description', '')
    desc = ""
    # Try to get main character description for left panel
    main_edges = manga_data.get('characters', {}).get('edges', [])
    if main_edges:
        char_node = main_edges[0].get('node', {})
        desc = char_node.get('description', '')
    
    # Local imports for sanitization

    
    # Clean up description
    if desc:
        desc = sanitize_description(desc)
    
    # Fallback to series description if no char desc or too short
    if not desc or len(desc) < 20:
        desc = manga_data.get('description', '') or ''
        if desc:
            desc = sanitize_description(desc)
        
    if desc:
        # Add ellipsis at the end if it's long (likely continuation)
        if len(desc) > 100 and not desc.endswith("..."):
             desc += "..."
             
        desc_font = get_font(18, "regular")  # Larger font
        wrapper = textwrap.TextWrapper(width=45)
        desc_lines = wrapper.wrap(desc)[:4]  # More lines
        
        text_y = HEIGHT - 160
        for line in desc_lines:
            draw.text((45, text_y), line, font=desc_font, fill=(255, 255, 255, 230))
            text_y += 26

    logo_font = get_font(22, "bold")  # Larger logo
    logo_text = "ANIME" if manga_data.get('type') == 'ANIME' else "MANGA"
    draw.text((LEFT_PANEL_WIDTH - 190, HEIGHT - 75), logo_text, font=logo_font, fill=(255, 255, 255))
    draw.text((LEFT_PANEL_WIDTH - 190, HEIGHT - 52), "CRUISE", font=get_font(14), fill=(255, 255, 255))
    
    # Larger dots - moved slightly down
    for i in range(3):
        color = (255,255,255) if i == 0 else (150,150,150)
        draw.ellipse([45 + i*24, HEIGHT - 50, 57 + i*24, HEIGHT - 38], fill=color)

    # ═══════════════════════════════════════════════════════════════════════════
    # RIGHT PANEL (Content)
    # ═══════════════════════════════════════════════════════════════════════════
    
    right_start_x = LEFT_PANEL_WIDTH + CONTENT_PADDING
    right_width = WIDTH - LEFT_PANEL_WIDTH - (CONTENT_PADDING * 2)
    center_right_x = LEFT_PANEL_WIDTH + (WIDTH - LEFT_PANEL_WIDTH) // 2

    # -- Header (larger, no center line) --
    logo_text = "ANIME" if manga_data.get('type') == 'ANIME' else "MANGA"
    draw.text((right_start_x, 30), logo_text, font=get_font(32, "bold"), fill=TEXT_BLACK)
    # Match height but use regular weight for contrast
    draw.text((right_start_x + 130, 30), "CRUISE", font=get_font(32, "regular"), fill=TEXT_BLACK)
    
    tagline = "YOUR HUB FOR THE LATEST ANIME!" if manga_data.get('type') == 'ANIME' else "YOUR HUB FOR THE LATEST MANGA, MANHWA!"
    tagline_x = right_start_x + 340
    draw.text((tagline_x, 38), tagline, font=get_font(18, "medium"), fill=TEXT_GRAY)
    
    # Underline for tagline
    tagline_bbox = draw.textbbox((0,0), tagline, font=get_font(18, "medium"))
    tagline_width = tagline_bbox[2] - tagline_bbox[0]
    draw.line((tagline_x, 62, tagline_x + tagline_width, 62), fill=(150, 150, 155), width=5)
    
    menu_x = WIDTH - 90
    for i in range(3):
        draw.line((menu_x, 38 + i*12, menu_x + 36, 38 + i*12), fill=TEXT_BLACK, width=4)

    # -- Title (using medium weight for different look) --
    title_data = manga_data.get('title', {})
    title_text = (title_data.get('english') or title_data.get('romaji') or 'UNKNOWN').upper()
    title_y = 240
    title_font = get_font(110, "extra-bold")  # Increased from 96
    
    words = title_text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=title_font)
        # Fix: If line is empty, accept valid word even if too long (prevents empty first line)
        if (bbox[2] - bbox[0] < right_width + 40) or not current_line:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    
    # SHIFT UP Logic:
    # If title has multiple lines, move starting Y up so the BOTTOM line stays in place
    # This prevents pushing down elements below.
    # Metric: 100px per line roughly for this font
    if len(lines) > 1:
        shift_amount = (len(lines[:2]) - 1) * 100
        title_y -= shift_amount
    
    for line in lines[:2]:
        draw.text((right_start_x, title_y), line, font=title_font, fill=TEXT_BLACK)
        title_y += 100  # Metric for BebasNeue 110px (tight leading)
        
    # Long DARK underline under title (full width)
    underline_y = title_y + 10
    draw.line((right_start_x, underline_y, WIDTH - CONTENT_PADDING, underline_y), fill=(150, 150, 155), width=5)

    # -- Description (Manga Summary) --
    desc = manga_data.get('description', '') or ''
    # Clean up description (AniList markup)
    if desc:
        desc = desc.replace('<br>', ' ').replace('<i>', '').replace('</i>', '').replace('\n', ' ')
        desc = desc.replace('__', '').replace('**', '').replace('~', '')

    desc_y = underline_y + 40
    if desc:
        wrapper = textwrap.TextWrapper(width=60)
        d_lines = wrapper.wrap(desc)[:6]
        if len(wrapper.wrap(desc)) > 6: d_lines[-1] += "..."
        for line in d_lines:
            draw.text((right_start_x, desc_y - 15), line, font=get_font(26, "medium"), fill=TEXT_BLACK)  # Increased from 24
            desc_y += 40

    # -- Buttons (Larger) --
    btn_y = desc_y + 15
    
    # 1. READ NOW Button (larger: 220x68)
    BTN_WIDTH = 220
    BTN_HEIGHT = 68
    draw.rounded_rectangle([right_start_x, btn_y, right_start_x + BTN_WIDTH, btn_y + BTN_HEIGHT], radius=34, fill=TEXT_BLACK)
    
    # Split text: READ (Red) NOW (White)
    btn_font = get_font(22, "bold")  # Larger font
    txt_read = "WATCH" if manga_data.get('type') == 'ANIME' else "READ"
    txt_now = "NOW"
    
    # Calculate widths to center the combo
    bbox_read = draw.textbbox((0,0), txt_read, font=btn_font)
    bbox_now = draw.textbbox((0,0), txt_now, font=btn_font)
    w_read = bbox_read[2] - bbox_read[0]
    w_now = bbox_now[2] - bbox_now[0]
    spacing = 7
    total_w = w_read + spacing + w_now
    
    start_txt_x = right_start_x + (BTN_WIDTH - total_w) // 2
    txt_y = btn_y + 18
    
    draw.text((start_txt_x, txt_y), txt_read, font=btn_font, fill=ACCENT_RED)
    draw.text((start_txt_x + w_read + spacing, txt_y), txt_now, font=btn_font, fill=(255,255,255))
    
    # 2. Bookmark Button (larger: 68px)
    BM_SIZE = 68
    bm_x = right_start_x + BTN_WIDTH + 24
    draw.ellipse([bm_x, btn_y, bm_x + BM_SIZE, btn_y + BM_SIZE], fill=TEXT_BLACK)
    cx, cy = bm_x + BM_SIZE//2, btn_y + BM_SIZE//2
    draw.polygon([(cx-10, cy-14), (cx+10, cy-14), (cx+10, cy+12), (cx, cy+4), (cx-10, cy+12), (cx-10, cy-14)], fill=(255,255,255))

    draw.text((WIDTH - 100, btn_y + 14), ">>>", font=get_font(32, "bold"), fill=TEXT_BLACK)
    
    # DARK underline after buttons (full width)
    underline_after_btn_y = btn_y + 10+ 80
    draw.line((right_start_x, underline_after_btn_y, WIDTH - CONTENT_PADDING, underline_after_btn_y), fill=(150, 150, 155), width=5)

    # ═══════════════════════════════════════════════════════════════════════════
    # BOTTOM FLOATING LAYOUT (Fixed Overlap)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Dimensions
    NAV_HEIGHT = 80
    NAV_BOTTOM_MARGIN = 40
    THUMB_SIZE = 150  # Larger thumbnails
    THUMB_GAP = 20
    
    # Y-Coordinates
    nav_y0 = HEIGHT - NAV_BOTTOM_MARGIN - NAV_HEIGHT # Top of Nav Pill
    nav_y1 = HEIGHT - NAV_BOTTOM_MARGIN              # Bottom of Nav Pill
    
    # Carousel Position: Move up more
    thumb_y = nav_y0 - THUMB_SIZE - 35
    
    # 1. Get character images (main first, then supporting as fallback)
    char_images = []
    main_edges = manga_data.get('characters', {}).get('edges', [])
    supporting_edges = manga_data.get('supportingCharacters', {}).get('edges', [])
    
    for edge in main_edges:
        if len(char_images) >= 3: break
        url = edge.get('node', {}).get('image', {}).get('large') or edge.get('node', {}).get('image', {}).get('medium')
        if url: char_images.append(url)
    
    # Add supporting chars if needed
    if len(char_images) < 3:
        for edge in supporting_edges:
            if len(char_images) >= 3: break
            url = edge.get('node', {}).get('image', {}).get('large') or edge.get('node', {}).get('image', {}).get('medium')
            if url and url not in char_images: char_images.append(url)
    
    # Reorder images: put main char (#1) in CENTER position
    # Order: [2nd char, 1st char (center), 3rd char]
    if len(char_images) >= 2:
        char_images = [char_images[1] if len(char_images) > 1 else None, 
                       char_images[0],  # Main char in center!
                       char_images[2] if len(char_images) > 2 else None]

    # Size config - center image larger for popup effect
    # Size config - center image larger for popup effect
    THUMB_SIZE_SIDE = 150
    THUMB_SIZE_CENTER = 180  # Larger for emphasis
    thumb_sizes = [THUMB_SIZE_SIDE, THUMB_SIZE_CENTER, THUMB_SIZE_SIDE]
    
    total_carousel_w = THUMB_SIZE_SIDE * 2 + THUMB_SIZE_CENTER + THUMB_GAP * 2
    carousel_start_x = center_right_x - (total_carousel_w // 2)
    
    thumb_x_positions = [
        carousel_start_x,
        carousel_start_x + THUMB_SIZE_SIDE + THUMB_GAP,
        carousel_start_x + THUMB_SIZE_SIDE + THUMB_GAP + THUMB_SIZE_CENTER + THUMB_GAP
    ]

    for i, img_url in enumerate(char_images):
        current_size = thumb_sizes[i]
        pos_x = thumb_x_positions[i]
        
        # Adjust Y so center image pops up a bit
        if i == 1:  # Center image
            pos_y = int(thumb_y) - 15  # Pop up effect
        else:
            pos_y = int(thumb_y) + 15  # Side images slightly lower
        
        # Shadow
        shadow = Image.new("RGBA", (current_size, current_size), (0,0,0,0))
        d_sh = ImageDraw.Draw(shadow)
        d_sh.rounded_rectangle([4, 4, current_size-4, current_size-4], radius=20, fill=(0,0,0,70 if i==1 else 50))
        shadow = shadow.filter(ImageFilter.GaussianBlur(10 if i==1 else 6))
        canvas.paste(shadow, (pos_x, pos_y+12), shadow)

        if img_url:
            c_img = load_image(img_url)
            if c_img:
                # Maintain aspect ratio with cover-crop
                img_w, img_h = c_img.size
                ratio = max(current_size / img_w, current_size / img_h)
                new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                c_img = c_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # Center crop to square
                left = (new_w - current_size) // 2
                top = (new_h - current_size) // 2
                c_img = c_img.crop((left, top, left + current_size, top + current_size))
                c_img = add_corners(c_img.convert("RGBA"), 22 if i==1 else 18)
                canvas.paste(c_img, (pos_x, pos_y), c_img)
        else:
            draw.rounded_rectangle([pos_x, pos_y, pos_x+current_size, pos_y+current_size], radius=20, fill=(230,230,230))

    # Larger dots above carousel
    dot_y = thumb_y - 40
    for i in range(3):
        dx = center_right_x - 25 + (i*25)
        fill = TEXT_BLACK if i==1 else (200,200,200)
        draw.ellipse([dx, dot_y, dx+14, dot_y+14], fill=fill)

    # Arrows
    arrow_f = get_font(30, "bold")
    draw.text((carousel_start_x - 45, thumb_y + 50), "<", font=arrow_f, fill=TEXT_BLACK)
    draw.text((carousel_start_x + total_carousel_w + 20, thumb_y + 50), ">", font=arrow_f, fill=TEXT_BLACK)

    # 2. Draw Nav Pill
    NAV_WIDTH = 620
    nav_x0 = center_right_x - (NAV_WIDTH // 2)
    nav_x1 = center_right_x + (NAV_WIDTH // 2)
    
    draw.rounded_rectangle([nav_x0, nav_y0, nav_x1, nav_y1], radius=NAV_HEIGHT//2, fill=BG_DARK)

    # Icons
    icons = ["home.png", "search.png", "heart.png", "share.png"]
    icon_y = nav_y0 + (NAV_HEIGHT - 28) // 2
    offsets = [-200, -80, 80, 200]
    
    for icon_name, offset in zip(icons, offsets):
        try:
            icon = load_icon(icon_name, size=(28, 28))
            icon = colorize_icon(icon, (255, 255, 255))
            canvas.paste(icon, (center_right_x + offset - 14, int(icon_y)), icon)
        except:
             pass

    # 3. FAB (Red Button) - Draws ON TOP of everything
    FAB_SIZE = 90
    fab_x = center_right_x - (FAB_SIZE // 2)
    fab_y = nav_y0 - (FAB_SIZE // 2) # Centered on top edge of nav pill
    
    # White "Cutout" Stroke (Thicker to separate from image)
    STROKE = 10
    draw.ellipse(
        [fab_x - STROKE, fab_y - STROKE, fab_x + FAB_SIZE + STROKE, fab_y + FAB_SIZE + STROKE],
        fill=BG_WHITE # Matches background, acts as mask/border
    )
    
    # Red Circle
    draw.ellipse([fab_x, fab_y, fab_x + FAB_SIZE, fab_y + FAB_SIZE], fill=ACCENT_RED)
    
    # Plus Icon
    px, py = center_right_x, fab_y + FAB_SIZE // 2
    draw.line((px - 16, py, px + 16, py), fill="white", width=4)
    draw.line((px, py - 16, px, py + 16), fill="white", width=4)

    # ─── Final Save ───
    bio = BytesIO()
    canvas.convert('RGB').save(bio, OUTPUT_FORMAT, quality=OUTPUT_QUALITY)
    bio.seek(0)
    return bio

