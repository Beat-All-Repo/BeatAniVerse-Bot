"""
Netflix Poster Generator

Generates Netflix-style anime posters at 1920x1080 resolution.
Dark, cinematic design with prominent title and rating.

Features:
- Full-screen backdrop with cinematic vignette
- Large, bold title with Netflix-style typography
- Match percentage and maturity rating
- Genres as subtle tags
- Brief description with fade
- Play and My List buttons

Style: Dark, minimal, cinematic with red accents
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Edit these values to customize the template
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Canvas Size ───
CANVAS_WIDTH = 1920                      # Output image width in pixels
CANVAS_HEIGHT = 1080                     # Output image height in pixels

# ─── Layout Dimensions ───
CONTENT_LEFT = 100                       # Left margin for content
CONTENT_BOTTOM = 220                     # Bottom margin for content (increased to move up)
LOGO_TOP = 45                            # Netflix logo top position
LOGO_LEFT = 65                           # Netflix logo left position

# ─── Colors (RGB tuples) ───
NETFLIX_RED = (229, 9, 20)               # Netflix brand red (#E50914)
NETFLIX_RED_DARK = (180, 7, 15)          # Darker red for gradients
NETFLIX_BLACK = (15, 15, 15)             # True black background
TEXT_WHITE = (255, 255, 255)             # White text
TEXT_LIGHT = (230, 230, 230)             # Slightly off-white
TEXT_GRAY = (170, 170, 170)              # Muted text
TEXT_LIGHT_GRAY = (130, 130, 130)        # Even more muted
MATCH_GREEN = (70, 211, 105)             # Green match percentage
NEW_BADGE_RED = (229, 9, 20)             # "NEW" badge color

# ─── Typography ───
FONT_TITLE_SIZE = 90                     # Main title font size (larger)
FONT_META_SIZE = 26                      # Match/year/rating font size
FONT_DESC_SIZE = 22                      # Description font size
FONT_BUTTON_SIZE = 20                    # Button text font size
FONT_GENRE_SIZE = 18                     # Genre tags font size

# ─── Button Dimensions ───
BUTTON_HEIGHT = 52                       # Button height
BUTTON_RADIUS = 4                        # Button corner radius (more Netflix-like)
PLAY_BUTTON_WIDTH = 150                  # Play button width
LIST_BUTTON_WIDTH = 170                  # My List button width
INFO_BUTTON_SIZE = 52                    # Info circle button

# ─── Output Configuration ───
OUTPUT_FORMAT = "JPEG"                   # Output format (JPEG or PNG)
OUTPUT_QUALITY = 99                      # JPEG quality (1-100)

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import textwrap
from pathlib import Path

# Project imports
from poster_utils import _pb_get_fonts as get_fonts  # patched
from poster_utils import load_image, create_gradient_overlay, colorize_icon, load_icon, sanitize_description

# ─── Paths ───
SCRIPT_DIR = Path(__file__).parent.parent  # /app
ICONS_DIR = SCRIPT_DIR / "iconspng"
OUTPUT_DIR = SCRIPT_DIR / "output"

# ─── Load Fonts ───
try:
    GOOGLE_FONTS = get_fonts()
except:
    GOOGLE_FONTS = {}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    """
    Get font with Netflix-style typography.
    
    Args:
        size: Font size in pixels
        weight: "bold", "medium", or "regular"
    """
    try:
        if weight == "bold":
            font_path = GOOGLE_FONTS.get("Poppins-Bold", "arialbd.ttf")
        elif weight == "medium":
            font_path = GOOGLE_FONTS.get("Poppins-Medium", "arial.ttf")
        else:
            font_path = GOOGLE_FONTS.get("Poppins-Regular", "arial.ttf")
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()


def create_cinematic_vignette(width: int, height: int) -> Image.Image:
    """Create Netflix-style cinematic vignette with strong left coverage for text."""
    import numpy as np
    
    # Create coordinate grids
    x = np.arange(width)
    y = np.arange(height)
    xx, yy = np.meshgrid(x, y)
    
    # Normalize
    nx = xx / width
    ny = yy / height
    
    # Bottom gradient - smooth fade from bottom
    bottom_gradient = np.clip((ny - 0.35) / 0.65, 0, 1) ** 0.7
    bottom_alpha = (bottom_gradient * 235).astype(np.uint8)
    
    # Left gradient - extends to 65% of screen for wider coverage
    left_gradient = np.clip(1 - nx / 0.65, 0, 1) ** 1.0  # Smoother falloff
    left_alpha = (left_gradient * 240).astype(np.uint8)
    
    # Bottom-left corner extra darkening for text area
    bottom_left = np.clip((1 - nx / 0.55) * np.clip((ny - 0.25) / 0.75, 0, 1), 0, 1) ** 0.6
    bottom_left_alpha = (bottom_left * 220).astype(np.uint8)
    
    # Top edge subtle darkening
    top_gradient = np.clip(1 - ny / 0.25, 0, 1) ** 2.5
    top_alpha = (top_gradient * 90).astype(np.uint8)
    
    # Right edge subtle vignette
    right_gradient = np.clip((nx - 0.85) / 0.15, 0, 1) ** 1.5
    right_alpha = (right_gradient * 60).astype(np.uint8)
    
    # Combine all gradients
    final_alpha = np.maximum(np.maximum(bottom_alpha, left_alpha), top_alpha)
    final_alpha = np.maximum(final_alpha, bottom_left_alpha)
    final_alpha = np.maximum(final_alpha, right_alpha)
    
    # Build RGBA image
    result = np.zeros((height, width, 4), dtype=np.uint8)
    result[..., 3] = final_alpha
    
    return Image.fromarray(result, 'RGBA')


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def create_poster(anime_data):
    """
    Create a Netflix-style poster.
    
    Args:
        anime_data: Dict with anime info from AniList API
        
    Returns:
        BytesIO object containing the generated JPEG image
    """
    WIDTH, HEIGHT = CANVAS_WIDTH, CANVAS_HEIGHT
    
    # Create base canvas
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), NETFLIX_BLACK)
    
    # ─── Background Image ───
    # Support both AniList and Crunchyroll data formats
    # Iterate through candidates until one successfully loads
    images = anime_data.get('images', {})
    bg_url_candidates = [
        images.get('banner_backdrop'),            # Crunchyroll backdrop (Preferred)
        images.get('landscape_poster'),           # Crunchyroll wide poster
        anime_data.get('landscape_poster'),       # Crunchyroll flat
        anime_data.get('bannerImage'),            # AniList banner
        anime_data.get('backdrop_url'),           # Crunchyroll backdrop alt
        (anime_data.get('coverImage', {}).get('extraLarge') if isinstance(anime_data.get('coverImage'), dict) else None),
        images.get('portrait_poster')             # Last resort: portrait
    ]
    
    bg = None
    for url in bg_url_candidates:
        if url:
            # print(f"Trying BG: {url}")
            bg = load_image(url)
            if bg:
                # Successfully loaded
                break
    
    if bg:
        # Scale to cover
        img_w, img_h = bg.size
        ratio = max(WIDTH / img_w, HEIGHT / img_h)
        new_w, new_h = int(img_w * ratio), int(img_h * ratio)
        bg = bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Center crop
        left = (new_w - WIDTH) // 2
        top = (new_h - HEIGHT) // 2
        bg = bg.crop((left, top, left + WIDTH, top + HEIGHT))
        
        canvas.paste(bg, (0, 0))
    
    # ─── Cinematic Vignette ───
    vignette = create_cinematic_vignette(WIDTH, HEIGHT)
    canvas = Image.alpha_composite(canvas, vignette)
    
    draw = ImageDraw.Draw(canvas)
    
    # ─── Netflix Logo (top left) ───
    try:
        logo = load_icon("netflix_logo.png", size=(90, 110))
        canvas.paste(logo, (LOGO_LEFT, LOGO_TOP), logo)
    except:
        # Fallback to text "N" if logo not found
        logo_font = get_font(48, "bold")
        draw.text((LOGO_LEFT, LOGO_TOP), "N", font=logo_font, fill=NETFLIX_RED)
    
    # ─── Content Area (bottom left) ───
    content_y = HEIGHT - CONTENT_BOTTOM
    x = CONTENT_LEFT
    
    # Title - support both AniList (dict) and Crunchyroll (string) formats
    title_data = anime_data.get('title')
    if isinstance(title_data, dict):
        title = title_data.get('english') or title_data.get('romaji') or 'Unknown'
    else:
        title = str(title_data) if title_data else 'Unknown'
    title_font = get_font(FONT_TITLE_SIZE, "bold")
    
    # Wrap title if too long
    max_title_width = 900
    title_lines = []
    words = title.split()
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=title_font)
        if bbox[2] - bbox[0] <= max_title_width:
            current_line = test_line
        else:
            if current_line:
                title_lines.append(current_line)
            current_line = word
    if current_line:
        title_lines.append(current_line)
    
    # Draw title (from bottom up)
    title_height = len(title_lines) * (FONT_TITLE_SIZE + 10)
    title_y = content_y - title_height - 180
    
    for line in title_lines:
        # Shadow
        draw.text((x + 3, title_y + 3), line, font=title_font, fill=(0, 0, 0, 180))
        # Main text
        draw.text((x, title_y), line, font=title_font, fill=TEXT_WHITE)
        title_y += FONT_TITLE_SIZE + 10
    
    # ─── Meta Row (Match %, Year, Rating, Duration) ───
    meta_y = title_y + 20
    meta_font = get_font(FONT_META_SIZE, "medium")
    
    # Match percentage (random 90-99%)
    import random
    match_pct = random.randint(90, 99)
    draw.text((x, meta_y), f"{match_pct}% Match", font=meta_font, fill=MATCH_GREEN)
    
    meta_x = x + 160
    
    # Year - support both formats
    year = anime_data.get('seasonYear') or anime_data.get('season_year') or anime_data.get('year', '')
    if year:
        draw.text((meta_x, meta_y), str(year), font=meta_font, fill=TEXT_GRAY)
        meta_x += 80
    
    # Maturity rating badge - properly sized with padding
    badge_font = get_font(16, "medium")
    badge_text = "TV-14"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_text_w = badge_bbox[2] - badge_bbox[0]
    badge_text_h = badge_bbox[3] - badge_bbox[1]
    badge_pad_x = 8
    badge_pad_y = 4
    badge_w = badge_text_w + badge_pad_x * 2
    badge_h = badge_text_h + badge_pad_y * 2
    
    draw.rounded_rectangle(
        [meta_x, meta_y, meta_x + badge_w, meta_y + badge_h], 
        radius=4, fill=None, outline=TEXT_GRAY, width=1
    )
    draw.text((meta_x + badge_pad_x, meta_y + badge_pad_y - badge_bbox[1]), badge_text, font=badge_font, fill=TEXT_GRAY)
    meta_x += badge_w + 20
    
    # Episodes
    # Episodes/Chapters
    episodes = anime_data.get('episodes') or anime_data.get('chapters')
    if episodes:
        label = "Chapters" if anime_data.get('type') == 'MANGA' else "Episodes"
        draw.text((meta_x, meta_y), f"{episodes} {label}", font=meta_font, fill=TEXT_GRAY)
        meta_x += 160
    
    # HD badge - properly sized
    hd_text = "HD"
    hd_bbox = draw.textbbox((0, 0), hd_text, font=badge_font)
    hd_text_w = hd_bbox[2] - hd_bbox[0]
    hd_text_h = hd_bbox[3] - hd_bbox[1]
    hd_w = hd_text_w + badge_pad_x * 2
    hd_h = hd_text_h + badge_pad_y * 2
    
    draw.rounded_rectangle(
        [meta_x, meta_y, meta_x + hd_w, meta_y + hd_h], 
        radius=4, fill=None, outline=TEXT_GRAY, width=1
    )
    draw.text((meta_x + badge_pad_x, meta_y + badge_pad_y - hd_bbox[1]), hd_text, font=badge_font, fill=TEXT_GRAY)
    
    # ─── Genres ───
    genres_y = meta_y + 50
    # Support both AniList (genres) and Crunchyroll (metadata.genres)
    metadata = anime_data.get('metadata', {})
    genres = anime_data.get('genres') or metadata.get('genres', [])
    genres = genres[:4] if genres else []
    genre_font = get_font(FONT_GENRE_SIZE, "regular")
    genre_text = " • ".join(genres) if genres else "Action • Drama"
    draw.text((x, genres_y), genre_text, font=genre_font, fill=TEXT_LIGHT_GRAY)
    
    # ─── Description ───
    desc_y = genres_y + 45
    desc = anime_data.get('description', '')
    
    if desc:
        # robust sanitization
        desc = sanitize_description(desc)
        
        desc_font = get_font(FONT_DESC_SIZE, "regular")
        wrapper = textwrap.TextWrapper(width=70)
        all_desc_lines = wrapper.wrap(desc)
        desc_lines = all_desc_lines[:5]  # Max 5 lines
        
        # Always add ellipsis at the end if there's more text
        if len(all_desc_lines) > 5 and desc_lines:
            last_line = desc_lines[-1]
            if len(last_line) > 60:
                desc_lines[-1] = last_line[:60] + "..."
            else:
                desc_lines[-1] = last_line + "..."
        elif desc_lines:
            # Add ellipsis anyway for cinematic look
            desc_lines[-1] = desc_lines[-1].rstrip('.') + "..."
        
        for i, line in enumerate(desc_lines):
            # Slight fade on last 2 lines
            color = TEXT_GRAY if i < 3 else TEXT_LIGHT_GRAY
            draw.text((x, desc_y + i * 28), line, font=desc_font, fill=color)
    
    # ─── Buttons ───
    button_y = desc_y + 160  # Adjusted for 5 lines
    button_font = get_font(FONT_BUTTON_SIZE, "medium")
    
    # Play button (white)
    draw.rounded_rectangle([x, button_y, x + PLAY_BUTTON_WIDTH, button_y + BUTTON_HEIGHT],
                           radius=BUTTON_RADIUS, fill=TEXT_WHITE)
    
    # Play/Read icon (triangle)
    play_icon_x = x + 20
    play_icon_y = button_y + 18
    draw.polygon([
        (play_icon_x, play_icon_y),
        (play_icon_x, play_icon_y + 20),
        (play_icon_x + 18, play_icon_y + 10)
    ], fill=NETFLIX_BLACK)
    
    play_text = "Read" if anime_data.get('type') == 'MANGA' else "Play"
    draw.text((x + 50, button_y + 14), play_text, font=button_font, fill=NETFLIX_BLACK)
    
    # My List button (semi-transparent dark with border)
    list_x = x + PLAY_BUTTON_WIDTH + 15
    
    # Create semi-transparent button overlay
    button_overlay = Image.new('RGBA', (LIST_BUTTON_WIDTH, BUTTON_HEIGHT), (50, 50, 50, 180))
    canvas.paste(button_overlay, (list_x, button_y), button_overlay)
    
    # Draw border
    draw.rounded_rectangle(
        [list_x, button_y, list_x + LIST_BUTTON_WIDTH, button_y + BUTTON_HEIGHT],
        radius=BUTTON_RADIUS, fill=None, outline=(150, 150, 150), width=1
    )
    
    # Plus icon - properly centered and thicker
    plus_x = list_x + 28
    plus_y = button_y + BUTTON_HEIGHT // 2
    plus_size = 10
    draw.line((plus_x, plus_y - plus_size, plus_x, plus_y + plus_size), fill=TEXT_WHITE, width=3)
    draw.line((plus_x - plus_size, plus_y, plus_x + plus_size, plus_y), fill=TEXT_WHITE, width=3)
    
    # "My List" text - centered vertically
    mylist_bbox = draw.textbbox((0, 0), "My List", font=button_font)
    mylist_y = button_y + (BUTTON_HEIGHT - (mylist_bbox[3] - mylist_bbox[1])) // 2 - mylist_bbox[1]
    draw.text((list_x + 55, mylist_y), "My List", font=button_font, fill=TEXT_WHITE)
    
    # ─── Rating (bottom right area) ───
    # Support both AniList (averageScore) and Crunchyroll (metadata.rating.stars)
    metadata = anime_data.get('metadata', {})
    rating_data = metadata.get('rating', {})
    score = anime_data.get('averageScore') or rating_data.get('stars')
    
    # Handle string scores from Crunchyroll
    if isinstance(score, str):
        try:
            score = float(score) if score != "N/A" else None
        except:
            score = None
    
    # Convert Crunchyroll star rating (1-5) to percentage-like score
    if score and isinstance(score, (int, float)) and score <= 5:
        score = score * 20  # Convert 5-star to 100-scale
    
    if score:
        rating_x = WIDTH - 140
        rating_y = HEIGHT - 100
        
        # Load star icon from PNG
        try:
            star_icon = load_icon("star.png", size=(36, 36))
            star_icon = colorize_icon(star_icon, (255, 200, 0))  # Gold color
            canvas.paste(star_icon, (rating_x, rating_y), star_icon)
        except:
            # Fallback: draw a proper 5-point star
            import math
            cx, cy = rating_x + 18, rating_y + 18
            outer_r, inner_r = 18, 7
            points = []
            for i in range(10):
                angle = math.radians(-90 + i * 36)
                r = outer_r if i % 2 == 0 else inner_r
                points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            draw.polygon(points, fill=(255, 200, 0))
        
        # Score text
        score_font = get_font(30, "bold")
        draw.text((rating_x + 45, rating_y + 3), f"{score/10:.1f}", font=score_font, fill=TEXT_WHITE)
    
    # ─── Output ───
    bio = BytesIO()
    canvas.convert('RGB').save(bio, OUTPUT_FORMAT, quality=OUTPUT_QUALITY)
    bio.seek(0)
    return bio


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from anilist import get_anime_data
    
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "attack on titan"
    print(f"Fetching: {query}")
    
    data = get_anime_data(query)
    if data:
        title = data['title'].get('english') or data['title'].get('romaji')
        print(f"Found: {title}")
        
        poster = create_poster(data)
        
        OUTPUT_DIR.mkdir(exist_ok=True)
        slug = query.lower().replace(" ", "-")
        output_path = OUTPUT_DIR / f"netflix_{slug}.jpg"
        
        with open(output_path, "wb") as f:
            f.write(poster.read())
        print(f"Saved: {output_path}")
    else:
        print("No results found")
