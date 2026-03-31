"""
Crunchyroll Poster Generator

Generates Crunchyroll-style anime posters at 1920x1080 resolution.
Based on the Crunchyroll website/TV app design.

Features:
- Header bar with logo and icons
- Full-width backdrop image with gradient overlay
- Title, genres, rating, and description
- Action buttons (Play, Watchlist, Add, Share)
- Content advisory footer

Scale Factor: 1920/1024 = 1.875x
All CSS rem/px values are scaled by 1.875 for HD output.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Edit these values to customize the template
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Canvas Size ───
CANVAS_WIDTH = 1920                      # Output image width in pixels
CANVAS_HEIGHT = 1080                     # Output image height in pixels

# ─── Scale Factor ───
# Original CSS is for 1024x576 viewport, scale up for 1920x1080
SCALE = 1.875                            # 1920 / 1024 = 1.875

# ─── Layout Dimensions (scaled from CSS) ───
HEADER_HEIGHT = int(60 * SCALE)          # Header bar height (112px)
CONTAINER_PADDING = int(64 * SCALE)      # Left/right padding (120px)
TITLE_FONT_SIZE = int(34 * SCALE)        # Title text size (64px)
META_FONT_SIZE = int(14 * SCALE)         # Genres/meta text size (26px)
TEXT_FONT_SIZE = int(16 * SCALE)         # Description text size (30px)
BUTTON_HEIGHT = int(40 * SCALE)          # Button height (75px)
STAR_SIZE = int(28 * SCALE)              # Star icon size (52px)
ICON_SIZE = int(24 * SCALE)              # Header icons size (45px)

# ─── Colors (RGB tuples) ───
COLOR_ORANGE_RGB = (255, 100, 10)        # Primary brand color (Crunchyroll orange)
COLOR_WHITE_RGB = (255, 255, 255)        # White text
COLOR_BLACK_RGB = (0, 0, 0)              # Background
COLOR_GRAY_BBB_RGB = (187, 187, 187)     # Muted text (#bbb)
COLOR_GRAY_TEXT_RGB = (160, 160, 160)    # Footer text
COLOR_BADGE_BG = (74, 78, 88)            # Age rating badge background

# ─── Colors (hex strings) ───
COLOR_ORANGE = "#ff640a"                 # Primary brand color

# ─── Font Configuration ───
FONT_TITLE = "DMSans-ExtraBold"          # Title font weight
FONT_BODY = "DMSans-Medium"              # Body text font weight
FONT_FALLBACK_BOLD = "Poppins-Bold"      # Fallback bold font
FONT_FALLBACK_REGULAR = "Poppins-Regular" # Fallback regular font

# ─── Output Configuration ───
OUTPUT_FORMAT = "JPEG"                   # Output format (JPEG or PNG)
OUTPUT_QUALITY = 99                      # JPEG quality (1-100)

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import sys
import math
import requests  # patched: use standard requests
from pathlib import Path

# Project imports
# crunchyroll module not available — crunchyroll_poster falls back to anilist data
def fetch_series_data(*a, **kw): return None

from poster_utils import _pb_get_fonts as get_fonts  # patched
from poster_utils import load_icon, colorize_icon, load_image, sanitize_description

# ─── Paths ───
SCRIPT_DIR = Path(__file__).parent.parent  # /app  # Project root (up from templates/)
ICONS_DIR = SCRIPT_DIR / "iconspng"        # Icons directory
OUTPUT_DIR = SCRIPT_DIR / "output"          # Output directory

# ─── Load Fonts ───
try:
    GOOGLE_FONTS = get_fonts()
except:
    GOOGLE_FONTS = {}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Get font with fallback chain.
    
    Args:
        size: Font size in pixels
        bold: If True, use bold weight; otherwise use medium weight
        
    Returns:
        PIL ImageFont object
    """
    try:
        if bold:
            font_path = GOOGLE_FONTS.get(FONT_TITLE, GOOGLE_FONTS.get(FONT_FALLBACK_BOLD, "arialbd.ttf"))
        else:
            font_path = GOOGLE_FONTS.get(FONT_BODY, GOOGLE_FONTS.get(FONT_FALLBACK_REGULAR, "arial.ttf"))
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()


def load_icon(name: str, size: tuple = None) -> Image.Image:
    """Load icon from icons directory."""
    icon_path = ICONS_DIR / name
    if not icon_path.exists():
        return Image.new('RGBA', size or (32, 32), (255, 255, 255, 128))
    
    icon = Image.open(icon_path).convert('RGBA')
    if size:
        icon = icon.resize(size, Image.Resampling.LANCZOS)
    return icon


def colorize_icon(icon: Image.Image, color: tuple) -> Image.Image:
    """Colorize icon to specific color using fast NumPy operations."""
    import numpy as np
    
    arr = np.array(icon)
    r, g, b = color[:3]
    
    # Create output with same alpha, but new RGB
    result = np.zeros_like(arr)
    result[..., 0] = r  # R
    result[..., 1] = g  # G
    result[..., 2] = b  # B
    result[..., 3] = arr[..., 3]  # Keep original alpha
    
    return Image.fromarray(result.astype(np.uint8), 'RGBA')


def download_image(url: str) -> Image.Image:
    """Download image from URL."""
    try:
        # Avoid AVIF by setting explicit Accept header
        headers = {
            "Accept": "image/jpeg,image/png,image/webp,*/*;q=0.8"
        }
        response = requests.get(url, headers=headers, timeout=15, impersonate="chrome")
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGBA')
    except Exception as e:
        print(f"Download Error ({url}): {e}")
        return None


def create_gradient_overlay(width: int, height: int) -> Image.Image:
    """
    CSS gradients (FAST NumPy version):
    linear-gradient(252deg, #0000008c 5%, #0000 25%)
    linear-gradient(to right, #000000d9 0%, #00000080 30%, #0000 55%)
    linear-gradient(to bottom, #0000 50.04%, #000 100%)
    """
    import numpy as np
    
    # Create coordinate grids
    x = np.arange(width)
    y = np.arange(height)
    xx, yy = np.meshgrid(x, y)
    
    # Normalize to 0-1
    nx = xx / width
    ny = yy / height
    
    # Gradient 1: 252deg diagonal
    angle_rad = math.radians(252)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    diag_progress = (nx * cos_a + ny * sin_a + 1) / 2
    
    alpha1 = np.zeros((height, width), dtype=np.float32)
    mask1 = diag_progress < 0.05
    mask2 = (diag_progress >= 0.05) & (diag_progress < 0.25)
    alpha1[mask1] = 0x8c
    alpha1[mask2] = 0x8c * (1 - (diag_progress[mask2] - 0.05) / 0.20)
    
    # Gradient 2: to right
    horiz_ratio = nx
    alpha2 = np.zeros((height, width), dtype=np.float32)
    mask1 = horiz_ratio < 0.30
    mask2 = (horiz_ratio >= 0.30) & (horiz_ratio < 0.55)
    alpha2[mask1] = 0xd9 - (0xd9 - 0x80) * (horiz_ratio[mask1] / 0.30)
    alpha2[mask2] = 0x80 * (1 - (horiz_ratio[mask2] - 0.30) / 0.25)
    
    # Gradient 3: to bottom
    vert_ratio = ny
    alpha3 = np.zeros((height, width), dtype=np.float32)
    mask = vert_ratio >= 0.5004
    alpha3[mask] = 255 * (vert_ratio[mask] - 0.5004) / 0.4996
    
    # Combine: max of all gradients, clamped to 255
    final_alpha = np.clip(np.maximum(np.maximum(alpha1, alpha2), alpha3), 0, 255).astype(np.uint8)
    
    # Build RGBA image (black with computed alpha)
    result = np.zeros((height, width, 4), dtype=np.uint8)
    result[..., 3] = final_alpha
    
    return Image.fromarray(result, 'RGBA')


def draw_header(canvas: Image.Image, draw: ImageDraw.Draw):
    """Draw header - scaled to 112px height."""
    header_bg = Image.new('RGBA', (CANVAS_WIDTH, HEADER_HEIGHT), (30, 32, 38, 235))
    canvas.paste(header_bg, (0, 0), header_bg)
    
    # Logo - scaled
    logo_height = int(28 * SCALE)  # 52px
    logo_width = int(32 * SCALE)  # 300px
    logo = load_icon("crunchyroll_logo.png", size=(logo_width, logo_height))
    orange_logo = colorize_icon(logo, COLOR_ORANGE_RGB)
    logo_x = int(18 * SCALE)
    logo_y = (HEADER_HEIGHT - logo_height) // 2
    canvas.paste(orange_logo, (logo_x, logo_y), orange_logo)
    
    # Vertical separator
    sep_x = logo_x + logo_width + int(15 * SCALE)
    draw.line([(sep_x, int(20 * SCALE)), (sep_x, HEADER_HEIGHT - int(20 * SCALE))], fill=(100, 100, 100), width=2)
    
    # Right side icons - scaled
    icon_size = (ICON_SIZE, ICON_SIZE)
    icon_y = (HEADER_HEIGHT - ICON_SIZE) // 2
    icon_spacing = int(60 * SCALE)
    
    icons = ["search.png", "watchlist.png", "usersettings.png"]
    for i, icon_name in enumerate(icons):
        shift_right = int(80 * SCALE)
        icon_x = CANVAS_WIDTH - CONTAINER_PADDING + shift_right - (3 - i) * icon_spacing
        icon = colorize_icon(load_icon(icon_name, icon_size), COLOR_GRAY_BBB_RGB)
        canvas.paste(icon, (icon_x, icon_y), icon)


def draw_more_button(canvas: Image.Image, draw: ImageDraw.Draw):
    """Draw MORE button using more.png icon."""
    x = CANVAS_WIDTH - int(120 * SCALE)
    y = HEADER_HEIGHT + int(30 * SCALE)
    
    # Load and display more.png icon
    icon_size = (int(18 * SCALE), int(18 * SCALE))
    more_icon = colorize_icon(load_icon("more.png", icon_size), COLOR_WHITE_RGB)
    canvas.paste(more_icon, (x, y + int(5 * SCALE)), more_icon)
    
    # MORE text next to icon
    font = get_font(int(14 * SCALE), bold=True)
    draw.text((x + int(25 * SCALE), y + int(5 * SCALE)), "MORE", font=font, fill=COLOR_WHITE_RGB)


def generate_poster(anime_data: dict, output_path: str = None) -> Image.Image:
    """Generate poster with all elements scaled 1.875x."""
    
    canvas = Image.new('RGBA', (CANVAS_WIDTH, CANVAS_HEIGHT), COLOR_BLACK_RGB)
    
    # Download backdrop (starts AFTER header, object-position: left top)
    # Background area = full canvas height minus header
    bg_start_y = HEADER_HEIGHT  # Background starts after header
    bg_height = CANVAS_HEIGHT - HEADER_HEIGHT  # Available height for background
    
    backdrop_url = anime_data.get("images", {}).get("banner_backdrop") or anime_data.get("bannerImage")
    if not backdrop_url and isinstance(anime_data.get("coverImage"), dict):
         backdrop_url = anime_data.get("coverImage", {}).get("extraLarge")
    
    if backdrop_url:
        backdrop = download_image(backdrop_url)
        if backdrop:
            # Scale to cover the available area (object-fit: cover)
            available_aspect = CANVAS_WIDTH / bg_height
            backdrop_aspect = backdrop.width / backdrop.height
            
            if backdrop_aspect > available_aspect:
                # Backdrop is wider - fit by height
                new_height = bg_height
                new_width = int(new_height * backdrop_aspect)
            else:
                # Backdrop is taller - fit by width
                new_width = CANVAS_WIDTH
                new_height = int(new_width / backdrop_aspect)
            
            backdrop = backdrop.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop from left-top (object-position: left top)
            backdrop = backdrop.crop((0, 0, CANVAS_WIDTH, bg_height))
            
            # Paste backdrop AFTER header
            canvas.paste(backdrop, (0, bg_start_y))
    
    # Apply gradient (to entire canvas, but mainly affects backdrop area)
    gradient = create_gradient_overlay(CANVAS_WIDTH, CANVAS_HEIGHT)
    canvas = Image.alpha_composite(canvas, gradient)
    
    draw = ImageDraw.Draw(canvas)
    
    # Header
    draw_header(canvas, draw)
    
    # MORE button
    draw_more_button(canvas, draw)
    
    # === CONTENT - All positions scaled ===
    x = CONTAINER_PADDING
    y = HEADER_HEIGHT + int(40 * SCALE)  # padding-block-start: 2.5rem
    
    # Title - 2.125rem → 64px
    # Title - Support AniList dict or string
    title_data = anime_data.get("title")
    if isinstance(title_data, dict):
        title = title_data.get('english') or title_data.get('romaji') or "Unknown"
    else:
        title = str(title_data) if title_data else "Unknown"
    title_font = get_font(TITLE_FONT_SIZE, bold=True)
    draw.text((x, y), title, font=title_font, fill=COLOR_WHITE_RGB)
    
    # === RATING BADGE + GENRES ===
    meta_y = y + int(70 * SCALE)
    
    maturity = anime_data.get("metadata", {}).get("maturity", {})
    age_ratings = maturity.get("age_rating", [])
    
    if age_ratings:
        age_rating = age_ratings[0]
    elif anime_data.get("isAdult"):
        age_rating = "A 18+"
    else:
        age_rating = "U/A 16+"
    
    # Badge - rect width:46 height:20 scaled
    badge_font = get_font(int(12 * SCALE), bold=False)
    bbox = draw.textbbox((0, 0), age_rating, font=badge_font)
    badge_w = int(46 * SCALE) + 20
    badge_h = int(20 * SCALE) + 8
    
    badge_alpha = int(255 * 0.7)
    offset_y = 10

    # Calculate text dimensions for centering
    text_bbox = draw.textbbox((0, 0), age_rating, font=badge_font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Adjust badge height to fit text with padding
    badge_hx = text_height + int(8 * SCALE) # 4px padding top/bottom scaled

    # Center text horizontally and vertically within the badge
    text_x = x + (badge_w - text_width) // 2
    text_y = meta_y + offset_y + (badge_hx - text_height) // 2

    draw.rounded_rectangle(
        [x, meta_y + offset_y, x + badge_w, meta_y + offset_y - 5 + badge_h],
        radius=int(3 * SCALE),
        fill=(74, 78, 88, badge_alpha)
    )

    draw.text(
        (text_x, text_y),
        age_rating,
        font=badge_font,
        fill=COLOR_WHITE_RGB
    )
    
    # Bullet + Genres (0.875rem → 26px, color #bbb, underline)
    meta_font = get_font(META_FONT_SIZE)
    bullet_x = x + badge_w + int(10 * SCALE)
    draw.text((bullet_x, meta_y + int(6 * SCALE)), "•", font=meta_font, fill=COLOR_WHITE_RGB)
    
    genres = anime_data.get("genres") or anime_data.get("metadata", {}).get("genres", ["Action", "Series"])
    if not genres and isinstance(genres, list):
         genres = ["Action", "Series"]
    elif not isinstance(genres, list):
         genres = ["Action", "Series"]
         
    genre_x = bullet_x + int(15 * SCALE)
    
    for i, genre in enumerate(genres[:4]):
        if i > 0:
            draw.text((genre_x, meta_y + int(6 * SCALE)), ",", font=meta_font, fill=COLOR_GRAY_BBB_RGB)
            genre_x += int(10 * SCALE)
        
        draw.text((genre_x, meta_y + int(6 * SCALE)), genre, font=meta_font, fill=COLOR_GRAY_BBB_RGB)
        bbox = draw.textbbox((genre_x, meta_y), genre, font=meta_font)
        text_width = bbox[2] - bbox[0]
        
        # Underline (0.0625rem thickness → ~2px scaled)
        draw.line([(genre_x, meta_y + badge_h - int(4 * SCALE)), 
                   (genre_x + text_width, meta_y + badge_h - int(4 * SCALE))], 
                  fill=COLOR_GRAY_BBB_RGB, width=2)
        genre_x = bbox[2]
    
    # === STAR RATING ===
    star_y = meta_y + int(50 * SCALE)
    star_size = (STAR_SIZE, STAR_SIZE)
    star_icon = colorize_icon(load_icon("starsharp.png", star_size), COLOR_GRAY_BBB_RGB)
    star_padding = int(4 * SCALE)  # .25rem padding-inline
    
    for i in range(5):
        canvas.paste(star_icon, (x + i * (STAR_SIZE + star_padding), star_y), star_icon)

    sep_x = x + 5 * (STAR_SIZE + star_padding) 
    draw.line([(sep_x, star_y + int(5 * SCALE)), (sep_x, star_y + STAR_SIZE - int(5 * SCALE))], fill=COLOR_GRAY_BBB_RGB, width=2)
    
    rating_data = anime_data.get("metadata", {}).get("rating", {})
    
    score = anime_data.get("averageScore")
    if score:
        stars = round(score / 20, 1)
        count = anime_data.get("popularity", 385600) # Default if pop missing
    else:
        stars = rating_data.get("stars", 4.9)
        count = rating_data.get("count", 385600)
    
    count_str = f"{count/1000:.1f}K" if isinstance(count, int) and count >= 1000 else str(count)
    count_str = f"{count/1000:.1f}K" if isinstance(count, int) and count >= 1000 else str(count)
    
    rating_font = get_font(META_FONT_SIZE, bold=True)
    rating_x = x + 5 * (STAR_SIZE + star_padding) + int(10 * SCALE)
    draw.text((rating_x, star_y + int(5 * SCALE)), f"{stars} ({count_str})", font=rating_font, fill=COLOR_WHITE_RGB)
    
    # Dropdown icon (1.5rem → 45px)
    dropdown_size = (int(24 * SCALE), int(24 * SCALE))
    dropdown = colorize_icon(load_icon("dropdownfill.png", dropdown_size), COLOR_WHITE_RGB)
    dropdown_x = rating_x + int(80 * SCALE)
    canvas.paste(dropdown, (dropdown_x, star_y + int(3 * SCALE)), dropdown)
    
    # === BUTTONS (height 2.5rem → 75px) ===
    btn_y = star_y + int(60 * SCALE)
    btn_height = BUTTON_HEIGHT
    btn_width = int(200 * SCALE)  # min-width 7.5rem → scaled
    btn_padding = int(16 * SCALE)  # padding 0 1rem
    
    # Primary button - orange bg
    draw.rounded_rectangle([x, btn_y, x + btn_width, btn_y + btn_height],
                           radius=0, fill=COLOR_ORANGE)

    # Play icon (1.5rem → 45px) and "START WATCHING" text
    play_size = (int(24 * SCALE), int(24 * SCALE))
    play = colorize_icon(load_icon("play.png", play_size), COLOR_BLACK_RGB)

    btn_font = get_font(int(14 * SCALE), bold=True)
    text_content = "START WATCHING"
    text_bbox = draw.textbbox((0, 0), text_content, font=btn_font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calculate total width of icon + gap + text
    gap_between_icon_text = int(8 * SCALE)
    total_content_width = play_size[0] + gap_between_icon_text + text_width

    # Calculate starting x-position for content to be centered
    content_start_x = x + (btn_width - total_content_width) // 2

    # Position play icon
    play_icon_x = content_start_x
    play_icon_y = btn_y + (btn_height - play_size[1]) // 2
    canvas.paste(play, (play_icon_x, play_icon_y), play)

    # Position text
    text_x = content_start_x + play_size[0] + gap_between_icon_text
    text_y = btn_y + (btn_height - text_height) // 2 - 5
    draw.text((text_x, text_y), text_content, font=btn_font, fill=COLOR_BLACK_RGB)
    # Watchlist button - outline (.3125rem margin → 6px scaled)
    wl_x = x + btn_width + int(10 * SCALE)
    wl_size = btn_height
    draw.rounded_rectangle([wl_x, btn_y, wl_x + wl_size, btn_y + wl_size], 
                           radius=0, outline=COLOR_ORANGE, width=int(3 * SCALE))
    
    wl_icon_size = (int(24 * SCALE), int(24 * SCALE))
    wl_icon = colorize_icon(load_icon("watchlist.png", wl_icon_size), COLOR_ORANGE_RGB)
    canvas.paste(wl_icon, (wl_x + (wl_size - wl_icon_size[0]) // 2, 
                           btn_y + (wl_size - wl_icon_size[1]) // 2), wl_icon)
    
    # === ADD + SHARE (.625rem gap → 12px scaled) ===
    action_y = btn_y + btn_height + int(25 * SCALE)
    action_size = (int(28 * SCALE), int(28 * SCALE))
    action_gap = int(10 * SCALE)
    
    add_icon = colorize_icon(load_icon("add.png", action_size), COLOR_ORANGE_RGB)
    share_icon = colorize_icon(load_icon("share.png", action_size), COLOR_ORANGE_RGB)
    canvas.paste(add_icon, (x, action_y), add_icon)
    canvas.paste(share_icon, (x + action_size[0] + action_gap, action_y), share_icon)
    
    # === DESCRIPTION with fade effect ===
    # CSS: max-height: 5.5rem (88px → 165px scaled)
    # CSS: fade-size: 2.5rem (40px → 75px scaled)
    # CSS: mask-image: linear-gradient(to bottom, #000 calc(100% - 2.5rem), #0000)
    desc_y = action_y + int(60 * SCALE)
    description = anime_data.get("description", "")
    if description:
        description = sanitize_description(description)
        # CSS: font-size: 1rem (16px → 30px), weight: 400, line-height: 1.375rem (22px → 41px)
        desc_font = get_font(int(16 * SCALE), bold=False)  # 1rem = 30px, weight 400
        line_height = int(22 * SCALE)  # calc(1rem + .375rem) = 22px → 41px
        max_width = int(480 * SCALE)
        max_height = int(88 * SCALE)  # 5.5rem = 165px
        fade_size = int(40 * SCALE)   # 2.5rem = 75px fade
        
        # Word wrap
        words = description.split()
        lines, line = [], []
        for word in words:
            test = ' '.join(line + [word])
            if draw.textbbox((0, 0), test, font=desc_font)[2] <= max_width:
                line.append(word)
            else:
                if line: lines.append(' '.join(line))
                line = [word]
        if line: lines.append(' '.join(line))
        
        # Create a separate layer for description text
        desc_layer = Image.new('RGBA', (max_width + 50, max_height + 20), (0, 0, 0, 0))
        desc_draw = ImageDraw.Draw(desc_layer)
        
        # Draw all visible lines onto the description layer
        visible_lines = (max_height // line_height) + 1
        for i, ln in enumerate(lines[:visible_lines]):
            line_y_local = i * line_height
            if line_y_local < max_height:
                desc_draw.text((0, line_y_local), ln, font=desc_font, fill=(255, 255, 255, 255))
        
        # Create fade mask using NumPy (FAST)
        import numpy as np
        fade_start_y = max_height - fade_size
        
        # Build fade values for each row
        h, w = desc_layer.height, desc_layer.width
        y_coords = np.arange(h)
        
        fade_alpha = np.ones(h, dtype=np.float32) * 255
        fade_zone = (y_coords >= fade_start_y) & (y_coords < max_height)
        beyond_zone = y_coords >= max_height
        
        progress = (y_coords[fade_zone] - fade_start_y) / fade_size
        fade_alpha[fade_zone] = 255 * (1 - progress)
        fade_alpha[beyond_zone] = 0
        
        # Create 2D mask by broadcasting row values
        mask_arr = np.tile(fade_alpha.astype(np.uint8).reshape(-1, 1), (1, w))
        
        # Get alpha channel and multiply
        arr = np.array(desc_layer)
        arr[..., 3] = (arr[..., 3].astype(np.float32) * mask_arr / 255).astype(np.uint8)
        desc_layer = Image.fromarray(arr, 'RGBA')
        
        # Composite onto main canvas
        canvas.paste(desc_layer, (x, desc_y), desc_layer)
    
    # === MORE DETAILS (margin-block-start: 1.25rem → 23px) ===
    more_y = desc_y + int(88 * SCALE) + int(20 * SCALE)  # After max-height + margin
    more_font = get_font(int(14 * SCALE), bold=True)
    draw.text((x, more_y), "MORE DETAILS", font=more_font, fill=COLOR_ORANGE)
    
    # === FOOTER ===
    footer_x = CANVAS_WIDTH // 2 + int(60 * SCALE)
    footer_y = CANVAS_HEIGHT - int(130 * SCALE)
    
    footer_font = get_font(int(14 * SCALE), bold=False)
    draw.text((footer_x, footer_y), "Content Advisory:", font=footer_font, fill=COLOR_WHITE_RGB)
    
    badge_x = footer_x + int(125 * SCALE)
    badge_w = int(50 * SCALE)
    badge_h = int(22 * SCALE)
    draw.rounded_rectangle([badge_x, footer_y - int(2 * SCALE)+5, badge_x + badge_w, footer_y + badge_h-10], 
                           radius=int(3 * SCALE), fill=(74, 78, 88, 178))
    age_font = get_font(int(11 * SCALE))
    age_rating_width = draw.textlength(age_rating, font=age_font)
    age_rating_x = badge_x + (badge_w - age_rating_width) / 2
    draw.text((age_rating_x, footer_y + int(2 * SCALE)), age_rating,
              font=age_font, fill=COLOR_WHITE_RGB)
    
    advisories = maturity.get("advisory", ["Profanity", "Smoking", "Violence"])
    draw.text((badge_x + badge_w + int(5 * SCALE), footer_y), 
              ", ".join(advisories[:3]), font=footer_font, fill=COLOR_GRAY_TEXT_RGB)
    
    copyright_text = anime_data.get("metadata", {}).get("copyright", "")
    if copyright_text:
        draw.text((footer_x, footer_y + int(25 * SCALE)), f"{copyright_text}", 
                  font=get_font(int(12 * SCALE)), fill=COLOR_GRAY_TEXT_RGB)
    
    # Save
    if output_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        output_file = OUTPUT_DIR / output_path
        canvas.convert('RGB').save(output_file, 'JPEG', quality=99)
        print(f"Poster saved to: {output_file}")
    
    return canvas


def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Enter Anime Name: ").strip()
    
    if not query:
        print("No anime name provided.")
        return
    
    print(f"Fetching data for: {query}")
    
    try:
        # Worker handles session/auth internally
        anime_data = fetch_series_data(query)
    except Exception as e:
        print(f"Error: {e}")
        return
    
    if "error" in anime_data:
        print(f"Error: {anime_data['error']}")
        return
    
    print(f"Generating poster for: {anime_data.get('title')}")
    slug = anime_data.get("slug", query.lower().replace(" ", "_"))
    generate_poster(anime_data, f"crunchyroll_{slug}_poster.png")
    print("Done!")


if __name__ == "__main__":
    main()
