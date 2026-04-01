"""
Webtoon Flix Poster Generator - High Contrast Dark Mode
"""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import textwrap
import numpy as np

# Project imports
from poster_utils import _pb_get_fonts as get_fonts  # patched
from poster_utils import load_image, sanitize_description  # patched

# ─── Configuration ───
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080

# Colors
# Start is almost black for maximum vignette effect
COLOR_BG_START = (5, 0, 5)        # Deepest Plum/Black (Corners)
COLOR_BG_END = (160, 0, 80)       # Vibrant Magenta (Center Spotlight)
COLOR_WHITE = (255, 255, 255)
COLOR_OFF_WHITE = (255, 250, 245) 
COLOR_TEXT_BLACK = (15, 15, 15)   
COLOR_TITLE_BG = (255, 255, 255, 45) 

# Dimensions
LEFT_PANEL_WIDTH = 1150 # Increased from 900
PADDING_X = 110  # Slightly increased padding

# Fonts Loading
try:
    GOOGLE_FONTS = get_fonts()
except:
    GOOGLE_FONTS = {}

def get_font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    try:
        if weight == "bold":
            font_path = GOOGLE_FONTS.get("Poppins-Bold", "arialbd.ttf")
        elif weight == "extra-bold":
            font_path = GOOGLE_FONTS.get("Poppins-ExtraBold", "arialbd.ttf") 
        elif weight == "medium":
            font_path = GOOGLE_FONTS.get("Poppins-Medium", "arial.ttf")
        elif weight == "regular":
            font_path = GOOGLE_FONTS.get("Poppins-Regular", "arial.ttf")
        else:
            font_path = GOOGLE_FONTS.get("Poppins-Regular", "arial.ttf")
            
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()

def create_gradient_bg(width, height):
    """
    Creates a High-Contrast Spotlight Gradient.
    Strong vignette with deep dark corners.
    """
    y, x = np.ogrid[:height, :width]
    
    # Base: Pitch Black / Deep Plum
    arr = np.zeros((height, width, 3), dtype=float)
    arr[:] = COLOR_BG_START
    
    # Spotlight Center
    # Focused slightly higher (0.4) to illuminate the Title Box
    cx, cy = width * 0.5, height * 0.4
    
    # Calculate distance
    dist = np.sqrt((x - cx)**2 + (y - cy)**2)
    max_dist = np.sqrt(width**2 + height**2)
    
    # FADE LOGIC:
    # 0.8 radius -> Wider spread of light
    # 1.3 exponent -> Gentle curve (not sharp)
    # REDUCED INTENSITY: slightly softer glow to reduce hash contrast
    glow = np.clip(1 - (dist / (max_dist * 0.95)), 0, 1) ** 1.8
    
    target = np.array(COLOR_BG_END, dtype=float)
    
    for c in range(3):
        arr[:, :, c] = arr[:, :, c] * (1 - glow) + target[c] * glow
        
    return Image.fromarray(np.uint8(arr))

def draw_pill_button(draw, x, y, w, h, text, font, text_color, bg_color):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=h//2, fill=bg_color)
    
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    tx = x + (w - tw) // 2
    ty = y + (h - th) // 2 - bbox[1] 
    
    draw.text((tx, ty), text, font=font, fill=text_color)

def create_poster(anime_data):
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), (0,0,0))
    
    # ─── 1. Background Panel ───
    left_bg = create_gradient_bg(LEFT_PANEL_WIDTH + 50, CANVAS_HEIGHT)
    canvas.paste(left_bg, (0, 0))
    
    # ─── 2. Character Image (Right Side) ───
    images = anime_data.get("images", {})
    img_url = (
        images.get("portrait_poster") or 
        images.get("poster_tall") or 
        images.get("cover_poster") or
        anime_data.get("coverImage", {}).get("extraLarge")
    )
    
    if img_url:
        img = load_image(img_url)
        if img:
            target_w = CANVAS_WIDTH - LEFT_PANEL_WIDTH
            target_h = CANVAS_HEIGHT
            
            img_ratio = img.width / img.height
            target_ratio = target_w / target_h
            
            if img_ratio > target_ratio:
                new_h = target_h
                new_w = int(new_h * img_ratio)
            else:
                new_w = target_w
                new_h = int(new_w / img_ratio)
                
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            crop_x = (new_w - target_w) // 2
            crop_y = 0 
            
            img = img.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))
            canvas.paste(img, (LEFT_PANEL_WIDTH, 0))

    # ─── 3. UI Elements ───
    draw = ImageDraw.Draw(canvas, "RGBA")
    
    # -- HEADER --
    logo_y = 40
    
    # Use "Chorettan" font for the Title Logo
    # fonts.py normalizes names to lower-case keys
    logo_font_path = GOOGLE_FONTS.get("chorettan", "arial.ttf")
    try:
        logo_font = ImageFont.truetype(logo_font_path, 92) # Increased size (80 -> 92)
    except:
        logo_font = get_font(80, weight="regular")

    draw.text((PADDING_X, logo_y), "Webtoon Flix", font=logo_font, fill=COLOR_WHITE)
    
    # Calculate width of the custom font logo to position slogan
    logo_w = draw.textlength("Webtoon Flix", font=logo_font)
    
    tagline_text = "UNFOLD THE BEST OF ANIME!" if anime_data.get('type') == 'ANIME' else "UNFOLD THE BEST OF MANGA & MANHWA!"
    tag_font = get_font(24, weight="bold") # Size 22 for balance
    
    # Position: Right of logo (Beside it)
    tag_x = PADDING_X + logo_w + 180
    tag_y = logo_y + 42 # Base line adjustment
    
    draw.text((tag_x, tag_y), tagline_text, font=tag_font, fill=COLOR_WHITE)
    
    # Underline
    line_y = tag_y + 30
    tag_w = draw.textlength(tagline_text, font=tag_font)
    draw.line([(tag_x, line_y), (tag_x + tag_w, line_y)], fill=COLOR_WHITE, width=4)
    
    # -- TITLE BOX --
    box_y = 150 # Moved up 50px (was 230)
    box_w = 980 # Increased width (930 -> 980)
    box_h = 360 # Increased height (320 -> 360)
    
    draw.rounded_rectangle(
        [PADDING_X, box_y, PADDING_X + box_w, box_y + box_h],
        radius=40,
        fill=COLOR_TITLE_BG
    )
    
    titles = anime_data.get("title", {})
    # Prefer English, fallback to Romaji, then Native
    raw_title = titles.get("english") or titles.get("romaji") or titles.get("native") or "Unknown Title"
    title_text = raw_title.upper()
    
    # Fixed font size as requested (truncation handles length)
    title_font_size = 90

    if len(title_text) < 14:
        title_font_size = 110
        print("Title is too short, increasing font size to 120")
    
    title_font = get_font(title_font_size, weight="extra-bold")
    
    # Truncate to 29 chars as requested
    if len(title_text) > 29:
        title_text = title_text[:29] + "..."

    
    # Wrap text with strict 2-line limit
    # This catches cases where 29 chars might still wrap to 3 lines
    wrapper = textwrap.TextWrapper(width=18, max_lines=2, placeholder="...") 
    lines = wrapper.wrap(title_text)
    
    total_text_h = len(lines) * (title_font_size * 1.15)
    text_start_y = box_y + (box_h * 0.60 - total_text_h) // 2 + 25
    
    for line in lines:
        lw = draw.textlength(line, font=title_font)
        # Left Align with simple padding
        lx = PADDING_X + 20 + 25
        draw.text((lx, text_start_y), line, font=title_font, fill=COLOR_WHITE)
        text_start_y += title_font_size * 1.15
        
    # -- GENRE PILLS --
    genres = anime_data.get("genres", [])
    if not genres: genres = ["ACTION", "FANTASY", "ADVENTURE", "SUPERNATURAL"]
    genres = [g.upper() for g in genres][:4] # Increased limit to 4 if present
    
    pill_h = 65 # Increased Height (50->60)
    pill_w = 215 # Increased Width (180->210)
    spacing = 25
    
    total_pills_w = len(genres) * pill_w + (len(genres) - 1) * spacing
    start_pill_x = PADDING_X + (box_w - total_pills_w) // 2
    
    # MOVED UP: Increased bottom offset
    pill_y = box_y + box_h - pill_h - 55
    
    pill_font = get_font(20, weight="extra-bold") # Font 20
    
    for i, g in enumerate(genres):
        px = start_pill_x + i * (pill_w + spacing)
        draw_pill_button(draw, px, pill_y, pill_w, pill_h, g, pill_font, COLOR_TEXT_BLACK, COLOR_OFF_WHITE)
        
    # -- SYNOPSIS --
    syn_start_y = box_y + box_h + 30
    
    syn_font = get_font(60, weight="extra-bold") # Increased 38 -> 42
    syn_text = "SYNOPSIS"
    syn_w = draw.textlength(syn_text, font=syn_font)
    
    # Re-calculate center axis based on new box_w
    center_axis = PADDING_X + box_w // 2
    syn_x = center_axis - syn_w // 2
    
    draw.text((syn_x, syn_start_y), syn_text, font=syn_font, fill=COLOR_WHITE)
    
    raw_desc = anime_data.get("description", "")
    clean_desc = sanitize_description(raw_desc)
    
    body_font = get_font(30, weight="medium") # Slightly smaller body for better fit with large container? No, sticking to 30.
    
    # Decreased wrapping width (85 -> 75) for tighter block
    body_wrapper = textwrap.TextWrapper(width=70) 
    body_lines = body_wrapper.wrap(clean_desc)[:6]
    
    current_y = syn_start_y + 80
    
    for line in body_lines:
        lw = draw.textlength(line, font=body_font)
        lx = center_axis - lw // 2
        draw.text((lx, current_y), line, font=body_font, fill=(235, 235, 235))
        current_y += 42 
        
    # -- READ NOW BUTTON --
    btn_w = 340 # 280 -> 340
    btn_h = 85 # 70 -> 85
    btn_x = (LEFT_PANEL_WIDTH - btn_w) // 2 # Centered in Left Panel
    btn_y = CANVAS_HEIGHT - 140
    
    btn_text = "WATCH NOW" if anime_data.get('type') == 'ANIME' else "READ NOW"
    draw_pill_button(draw, btn_x, btn_y, btn_w, btn_h, btn_text, get_font(32, weight="extra-bold"), COLOR_TEXT_BLACK, COLOR_OFF_WHITE)

    output = BytesIO()
    canvas.save(output, format="JPEG", quality=95)
    return output