"""
AniList Poster Generator

Generates AniList-style anime posters at 1920x1080 resolution.
Exact replica of AniList website detail page layout.

Features:
- Banner image with gradient overlay (top ~55%)
- Cover image with rounded corners and shadow
- Title, format, episodes, duration, status
- Genres, studios, and description
- Action buttons (Add to List, Favorite)
- Footer with rankings

Based on: https://anilist.co/anime/[id]
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Edit these values to customize the template
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Canvas Size ───
CANVAS_WIDTH = 1920                      # Output image width in pixels
CANVAS_HEIGHT = 1080                     # Output image height in pixels

# ─── Layout Dimensions ───
BANNER_HEIGHT = 520                      # Banner section height (top area)
COVER_WIDTH = 290                        # Cover image width
COVER_HEIGHT = 420                       # Cover image height
COVER_MARGIN_LEFT = 100                  # Left margin for cover image
COVER_TOP = 350                          # Top position of cover image
COVER_BORDER_RADIUS = 8                  # Cover image corner radius

# ─── Colors (RGB tuples) ───
BG_DARK = (11, 22, 34)                   # Main background (#0b1622)
BG_PANEL = (21, 31, 46)                  # Content panel background (#151f2e)
ACCENT_BLUE = (61, 180, 242)             # AniList accent blue (#3DB4F2)
TEXT_LIGHT = (114, 138, 161)             # Muted text color (#728AA1)
TEXT_WHITE = (159, 173, 189)             # Primary text color (#9FADBD)
TEXT_BRIGHT = (237, 241, 245)            # Bright text (#EDF1F5)
BUTTON_PINK = (232, 93, 117)             # Favorite button (#E85D75)

# ─── Typography ───
FONT_TITLE_SIZE = 48                     # Title font size
FONT_META_SIZE = 22                      # Meta info font size
FONT_BODY_SIZE = 20                      # Description font size
FONT_SMALL_SIZE = 18                     # Small text font size

# ─── Output Configuration ───
OUTPUT_FORMAT = "JPEG"                   # Output format (JPEG or PNG)
OUTPUT_QUALITY = 99                      # JPEG quality (1-100)

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import textwrap
from pathlib import Path

# Project imports
from poster_utils import _pb_get_fonts as get_fonts  # patched
from poster_utils import load_image, add_corners
# stubs for anilist_poster features not in poster_utils
def extract_colors(img, n=5): return [(61,180,242)]*n
def draw_material_icon(*a, **kw): pass
def colorize_image(img, color): return img

# ─── Load Fonts ───
try:
    GOOGLE_FONTS = get_fonts()
except:
    GOOGLE_FONTS = {}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def create_poster(anime_data):
    """
    Create an AniList-style poster.
    
    Args:
        anime_data: Dict with anime info from AniList API
        
    Returns:
        BytesIO object containing the generated JPEG image
    """
    
    # Use constants from configuration
    WIDTH, HEIGHT = CANVAS_WIDTH, CANVAS_HEIGHT
    
    # Create dark background canvas
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(canvas)
    
    # ─── BANNER SECTION (Top ~55% of image) ───
    banner_height = BANNER_HEIGHT
    banner_url = anime_data.get('bannerImage')
    cover_url = anime_data['coverImage'].get('extraLarge') or anime_data['coverImage'].get('large')
    
    if banner_url:
        banner_img = load_image(banner_url)
        if banner_img:
            img_w, img_h = banner_img.size
            
            # CSS background-size: cover - scale to fill, maintain aspect ratio
            img_ratio = img_w / img_h
            canvas_ratio = WIDTH / banner_height
            
            if img_ratio > canvas_ratio:
                # Image is wider - scale by height
                new_h = banner_height
                new_w = int(new_h * img_ratio)
            else:
                # Image is taller - scale by width
                new_w = WIDTH
                new_h = int(new_w / img_ratio)
            
            banner_img = banner_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # CSS background-position: 50% 35%
            left = int((new_w - WIDTH) )
            top = int((new_h - banner_height) * 0.35)
            banner_img = banner_img.crop((left, top, left + WIDTH, top + banner_height))
            
            # Apply gradient dark to banner image bottom (part of banner itself)
            # CSS: linear-gradient(180deg, rgba(0,0,0,0) 40%, rgba(0,0,0,0.6))
            banner_img = banner_img.convert("RGBA")
            gradient_overlay = Image.new('RGBA', (WIDTH, banner_height), (0, 0, 0, 0))
            grad_draw = ImageDraw.Draw(gradient_overlay)
            
            # Gradient starts at 40% height, ends at 100% with 0.6 opacity
            start_y = int(banner_height * 0.40)
            for y in range(start_y, banner_height):
                progress = (y - start_y) / (banner_height - start_y)
                alpha = int(153 * progress)  # 0.6 * 255 = 153
                grad_draw.line((0, y, WIDTH, y), fill=(0, 0, 0, alpha))
            
            banner_img = Image.alpha_composite(banner_img, gradient_overlay)
            
            # CSS margin-top: -58px - paste banner scaled higher
            canvas.paste(banner_img, (0, -90))  # Scaled from -58

    # --- CONTENT PANEL (Below banner) ---
    draw.rectangle([0, banner_height-90, WIDTH, HEIGHT], fill=BG_PANEL)
    
    # --- COVER IMAGE (Positioned to overlap banner) ---
    # Larger scale for 1920x1080 (~1.5x)
    cover_x = 230  # Moved left
    cover_y = 330  # Adjusted
    cover_w = 350  # Larger scale from 215
    cover_h = "auto"   # auto height
    
    if cover_url:
        cover_img = load_image(cover_url)
        if cover_img:
            img_w, img_h = cover_img.size
    
            # Auto height = keep aspect ratio based on width
            if cover_h == "auto":
                scale = cover_w / img_w
                new_w = cover_w
                new_h = int(img_h * scale)
    
                cover_img = cover_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            else:
                # Fixed width & height (your original method)
                scale = max(cover_w / img_w, cover_h / img_h)
                new_w = int(img_w * scale)
                new_h = int(img_h * scale)
    
                cover_img = cover_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
                # Center crop
                left = (new_w - cover_w) // 2
                top = (new_h - cover_h) // 2
                cover_img = cover_img.crop((left, top, left + cover_w, top + cover_h))
    
            # Ensure RGBA for alpha operations
            cover_img = cover_img.convert("RGBA")
    
            # CSS: border-radius: 2px
            cover_img = add_corners(cover_img, 3)
    
            # Use actual sizes from the processed image (important when cover_h == "auto")
            cover_w_actual, cover_h_actual = cover_img.size
    
            # CSS: box-shadow - smooth faded shadow using multiple blur passes
            shadow_pad = 25  # Shadow padding
            shadow_w = cover_w_actual + shadow_pad * 2
            shadow_h = cover_h_actual + shadow_pad * 2
    
            shadow = Image.new("RGBA", (shadow_w, shadow_h), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            
            # Draw shadow shape
            shadow_draw.rounded_rectangle(
                [shadow_pad, shadow_pad, shadow_pad + cover_w_actual, shadow_pad + cover_h_actual],
                radius=3, fill=(10, 15, 25, 70)
            )
            
            # Apply multiple BoxBlur passes for smoother fade (better than single GaussianBlur)
            for _ in range(4):
                shadow = shadow.filter(ImageFilter.BoxBlur(radius=8))
    
            # Paste shadow centered behind cover
            canvas.paste(shadow, (cover_x - shadow_pad, cover_y - shadow_pad), shadow)
    
            # (optional) background/border code can use cover_w_actual/cover_h_actual if enabled
            # border_size = 1
            # border = Image.new('RGBA', (cover_w_actual + border_size*2, cover_h_actual + border_size*2),
            #                    (212, 230, 245, int(255*0.5)))
            # border = add_corners(border, 2)
            # canvas.paste(border, (cover_x - border_size, cover_y - border_size), border)
    
            # Paste cover image
            canvas.paste(cover_img, (cover_x, cover_y), cover_img)

    
    # Refresh draw after pastes
    draw = ImageDraw.Draw(canvas)
    
    # --- LOAD FONTS ---
    # Using multiple fonts scaled for 1920x1080:
    # - Overpass: AniList's primary font for titles
    # - Roboto: Clean body text for descriptions
    # - Poppins: UI elements like buttons, badges, rankings
    try:
        google_fonts = get_fonts()
        
        # Title fonts - Overpass (AniList style) or Poppins Bold fallback
        title_font = ImageFont.truetype(
            google_fonts.get("Overpass-Bold", google_fonts.get("Poppins-SemiBold", "arialbd.ttf")), 50  # Larger scale
        )
        
        # Description font - Roboto for clean reading
        desc_font = ImageFont.truetype(
            google_fonts.get("Roboto-Regular", google_fonts.get("Poppins-Regular", "arial.ttf")), 28  # Larger scale
        )
        
        # Genre pills font - Poppins Medium (compact, clean)
        genre_font = ImageFont.truetype(
            google_fonts.get("Poppins-Medium", "arial.ttf"), 18  # Larger scale
        )
        
        # Info/metadata font - Roboto Regular
        info_font = ImageFont.truetype(
            google_fonts.get("Roboto-Regular", google_fonts.get("Poppins-Regular", "arial.ttf")), 25  # Larger scale
        )
        
        # Source text font - lighter weight
        source_font = ImageFont.truetype(
            google_fonts.get("Poppins-Regular", "arial.ttf"), 17  # Larger scale
        )
        
        # Button font - Poppins Medium (bold, readable)
        button_font = ImageFont.truetype(
            google_fonts.get("Poppins-SemiBold", google_fonts.get("Poppins-Medium", "arialbd.ttf")), 25  # Larger scale
        )
        
        # Ranking font - Poppins Medium for footer
        ranking_font_loaded = ImageFont.truetype(
            google_fonts.get("Poppins-Medium", "arial.ttf"), 24  # Larger scale
        )
        
        # Tab/navigation font
        tab_font = ImageFont.truetype(
            google_fonts.get("Poppins-Regular", "arial.ttf"), 17  # Scaled from 13
        )
    except:
        title_font = ImageFont.load_default()
        desc_font = ImageFont.load_default()
        genre_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        source_font = ImageFont.load_default()
        button_font = ImageFont.load_default()
        ranking_font_loaded = ImageFont.load_default()
        tab_font = ImageFont.load_default()
    
    # --- TITLE (Right of cover, below banner line) ---
    # Use actual cover dimensions if available
    cover_w_used = cover_w_actual if 'cover_w_actual' in dir() else cover_w
    cover_h_used = cover_h_actual if 'cover_h_actual' in dir() else (cover_h if cover_h != "auto" else 485)  # Larger
    
    text_x = cover_x + cover_w_used + 35  # Larger gap
    text_y = banner_height - 90 + 25  # Adjusted positioning
    
    title_text = anime_data['title']['english'] or anime_data['title']['romaji']
    draw.text((text_x, text_y), title_text, font=title_font, fill=TEXT_WHITE)
    text_y += 62  # Larger gap after title
    
    # --- ANIME INFO SECTION (Genres, Rating, Status, Season, Studio) - RIGHT BELOW TITLE ---
    
    # Genres as pills
    genres = anime_data.get('genres', [])[:5]
    if genres:
        genre_x = text_x
        for genre in genres:
            genre_text = genre.upper()
            bbox = draw.textbbox((0, 0), genre_text, font=genre_font)
            pill_w = bbox[2] - bbox[0] + 28  # Larger padding
            pill_h = 35  # Larger height
            
            # Genre pill with accent color
            draw.rounded_rectangle(
                [genre_x, text_y, genre_x + pill_w, text_y + pill_h],
                radius=5, fill=ACCENT_BLUE  # Larger radius
            )
            draw.text((genre_x + 14, text_y + 7), genre_text, font=genre_font, fill="#FFFFFF")
            genre_x += pill_w + 14  # Larger gap
        
        text_y += 50  # Larger gap after genres
    
    # Info items in a row - draw with icons instead of emojis
    info_x = text_x
    
    # Format & Count (Episodes/Chapters)
    fmt = anime_data.get('format', '').replace('_', ' ')
    count = anime_data.get('episodes') or anime_data.get('chapters')
    label = "Eps" if anime_data.get('type') == 'ANIME' else "Chs"
    
    if fmt or count:
        meta_text = f"{fmt} • {count} {label}" if (fmt and count) else (fmt or f"{count} {label}")
        draw.text((info_x+4, text_y), meta_text, font=info_font, fill=TEXT_LIGHT)
        bbox = draw.textbbox((info_x+4, text_y), meta_text, font=info_font)
        info_x = bbox[2] + 25
        draw.text((info_x+4, text_y), "•", font=info_font, fill=TEXT_LIGHT)
        info_x += 25

    # Rating with star icon
    rating = anime_data.get('averageScore')
    if rating:
        result = draw_material_icon(draw, "star", info_x+4, text_y-1, 26, ACCENT_BLUE)  # Larger icon
        if result:  # PNG returned as (image, position)
            star_img, pos = result
            canvas.paste(star_img, pos, star_img)
        info_x += 32  # Larger spacing
        draw.text((info_x+10, text_y), f"{rating}%", font=info_font, fill=TEXT_LIGHT)
        info_x += 80  # Larger gap
        draw.text((info_x+4, text_y), "•", font=info_font, fill=TEXT_LIGHT)
        info_x += 25  # Larger spacing
    
    # Status
    status = anime_data.get('status', '')
    if status:
        draw.text((info_x + 4, text_y), status.replace("_", " ").title(), font=info_font, fill=TEXT_LIGHT)
        bbox = draw.textbbox((info_x+4, text_y), status.replace("_", " ").title(), font=info_font)
        info_x = bbox[2] + 25  # Larger spacing
        draw.text((info_x+4, text_y), "•", font=info_font, fill=TEXT_LIGHT)
        info_x += 25  # Larger spacing
    
    # Season & Year
    season = anime_data.get('season', '')
    year = anime_data.get('seasonYear', '')
    if season and year:
        season_text = f"{season.title()} {year}"
        draw.text((info_x, text_y), season_text, font=info_font, fill=TEXT_LIGHT)
        bbox = draw.textbbox((info_x, text_y), season_text, font=info_font)
        info_x = bbox[2] + 25  # Larger spacing
        draw.text((info_x, text_y), "•", font=info_font, fill=TEXT_LIGHT)
        info_x += 25  # Larger spacing
    elif year:
        draw.text((info_x, text_y), str(year), font=info_font, fill=TEXT_LIGHT)
        bbox = draw.textbbox((info_x, text_y), str(year), font=info_font)
        info_x = bbox[2] + 25  # Larger spacing
        draw.text((info_x, text_y), "•", font=info_font, fill=TEXT_LIGHT)
        info_x += 25  # Larger spacing
    
    if anime_data.get('studios') and anime_data['studios'].get('nodes'):
        studio = anime_data['studios']['nodes'][0].get('name', '')
        if studio:
            draw.text((info_x, text_y), studio, font=info_font, fill=TEXT_LIGHT)
    
    text_y += 20  # Larger gap
    
    # --- DESCRIPTION ---
    # Larger scale for 1920x1080
    desc_max_width = 600  # Adjusted for larger text
    desc_height = 270  # Larger area
    desc_padding = 25  # Larger padding
    
    desc_text = anime_data.get('description', '')
    if desc_text:
        
        text_y += desc_padding  # top padding

        # Approx chars per line for wider canvas
        chars_per_line = int(desc_max_width / 7)
        wrapper = textwrap.TextWrapper(width=chars_per_line)

        # Max lines allowed
        max_lines = (desc_height - desc_padding * 2) // 24  # Scaled line height

        # --- CLEANUP TAGS ---
        desc_text = desc_text.replace("<i>", "").replace("</i>", "")

        # Convert double breaks to ONE explicit blank-line marker
        desc_text = desc_text.replace("<br>\n<br>", "[[BLANK]]")
        desc_text = desc_text.replace("<br> <br>", "[[BLANK]]")
        desc_text = desc_text.replace("<br>\r<br>", "[[BLANK]]")
        desc_text = desc_text.replace("<br>\t<br>", "[[BLANK]]")
        desc_text = desc_text.replace("<br><br>", "[[BLANK]]")

        # Single br → line break
        desc_text = desc_text.replace("<br>", "\n")

        paragraphs = desc_text.split("\n")
        lines = []

        for p in paragraphs:
            if p == "[[BLANK]]":
                lines.append("")  # ONE blank line
            elif p.strip() == "":
                lines.append("")  # normal blank line
            else:
                lines.extend(wrapper.wrap(p))

        # Limit to max lines
        limited = lines[:max_lines]

        # Add ellipsis if truncated
        if len(lines) > max_lines and limited:
            limited[-1] = limited[-1][:100] + "..."

        # Draw lines
        for line in limited:
            draw.text((text_x, text_y), line, font=desc_font, fill=TEXT_LIGHT)
            text_y += 35  # Scaled from 18

        text_y += desc_padding
  #     bottom padding
    
    # --- SOURCE ---
    source = anime_data.get('source', '')
    if source:
        source_formatted = source.replace("_", " ").title()
        draw.text((text_x, text_y), f"(Source: {source_formatted})", font=source_font, fill=(100, 115, 130))
    
    # --- ADD TO LIST BUTTON GROUP ---
    btn_x = cover_x
    btn_y = cover_y + cover_h_used + 25  # Larger gap
    btn_w = 215  # Larger button
    btn_h = 58  # Larger height
    
    # Main "Add to List" button - bright blue
    draw.rounded_rectangle(
        [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
        radius=4,  # Scaled from 3
        fill=(61, 180, 242)  # #3DB4F2
    )
    
    # Button text - centered
    btn_text = "Add to List"
    bbox = draw.textbbox((0, 0), btn_text, font=button_font)
    btn_text_w = bbox[2] - bbox[0]
    btn_text_h = bbox[3] - bbox[1]
    draw.text(
        (btn_x + (btn_w - btn_text_w) // 2, btn_y + (btn_h - btn_text_h) // 2 - bbox[1]),
        btn_text, font=button_font, fill="#FFFFFF"
    )
    
    # Dropdown button - slightly darker blue, attached
    drop_x = btn_x + btn_w - 5  # Adjusted
    drop_w = 55  # Larger
    draw.rounded_rectangle(
        [drop_x, btn_y, drop_x + drop_w, btn_y + btn_h],
        radius=5,  # Larger radius
        fill=(45, 157, 212)  # darker blue
    )
    # Dropdown icon - load PNG for smooth rendering
    dropdown_icon_path = os.path.join(os.path.dirname(__file__), '..', 'iconspng', 'dropdown.png')
    try:
        dropdown_icon = Image.open(dropdown_icon_path).convert("RGBA")
        icon_size = 24  # Larger icon
        dropdown_icon = dropdown_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        # Apply white color
        dropdown_icon = colorize_image(dropdown_icon, (255, 255, 255))
        # Center the icon in the button
        dx = drop_x + (drop_w - icon_size) // 2
        dy = btn_y + (btn_h - icon_size) // 2
        canvas.paste(dropdown_icon, (dx, dy), dropdown_icon)
    except:
        # Fallback to polygon chevron
        cx = drop_x + drop_w // 2
        cy = btn_y + btn_h // 2
        draw.polygon([
            (cx - 6, cy - 3),
            (cx + 6, cy - 3),
            (cx, cy + 5)
        ], fill="#FFFFFF")
    
    # Heart/Favorite button - coral/salmon pink
    heart_x = drop_x + drop_w + 25  # Larger gap
    heart_w = 60  # Larger
    draw.rounded_rectangle(
        [heart_x, btn_y, heart_x + heart_w, btn_y + btn_h],
        radius=5,  # Larger radius
        fill=(236, 41, 75)
    )
    # Load and paste heart icon PNG (centered in button) - WHITE color
    heart_icon_path = os.path.join(os.path.dirname(__file__), '..', 'iconspng', 'heart.png')
    try:
        heart_icon = Image.open(heart_icon_path).convert("RGBA")
        icon_size = 30  # Larger icon
        heart_icon = heart_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        # Apply white color
        heart_icon = colorize_image(heart_icon, (255, 255, 255))
        # Center the icon in the button
        hx = heart_x + (heart_w - icon_size) // 2
        hy = btn_y + (btn_h - icon_size) // 2
        canvas.paste(heart_icon, (hx, hy), heart_icon)
    except:
        # Fallback to simple polygon if image fails
        hx = heart_x + heart_w // 2
        hy = btn_y + btn_h // 2
        heart_points = [
            (hx, hy - 7), (hx - 4, hy - 9), (hx - 8, hy - 7),
            (hx - 9, hy - 3), (hx - 8, hy + 1), (hx, hy + 9),
            (hx + 8, hy + 1), (hx + 9, hy - 3), (hx + 8, hy - 7),
            (hx + 4, hy - 9),
        ]
        draw.polygon(heart_points, fill="#FFFFFF")
    
  
    
    # --- FOOTER SECTION ---
    footer_height = 78  # Larger footer
    footer_y = HEIGHT - footer_height
    
    # Footer background - slightly darker than panel
    draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=(16, 26, 38))
    
    # Optional: subtle top border for the footer
    draw.line([(0, footer_y), (WIDTH, footer_y)], fill=(31, 41, 56), width=1)
    
    # Load and place AniList logo in left corner
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'iconspng/anilist_logo.png')
    try:
        logo_img = Image.open(logo_path).convert("RGBA")
        
        # Resize logo to fit footer (maintain aspect ratio)
        logo_target_height = 55  # Larger logo
        logo_ratio = logo_img.width / logo_img.height
        logo_new_width = int(logo_target_height * logo_ratio)
        logo_img = logo_img.resize((logo_new_width, logo_target_height), Image.Resampling.LANCZOS)
        
        # Position in left corner with padding
        logo_x = 50  # Larger padding
        logo_y = footer_y + (footer_height - logo_target_height) // 2
        
        canvas.paste(logo_img, (logo_x, logo_y), logo_img)
    except Exception as e:
        # Fallback: draw text if logo fails to load
        try:
            logo_text = "AniList"
            logo_font = ImageFont.truetype(google_fonts.get("Poppins-Medium", "arial.ttf"), 18)  # Scaled from 14
            bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
            text_w = bbox[2] - bbox[0]
            draw.text((40, footer_y + 16), logo_text, font=logo_font, fill=ACCENT_BLUE)
        except:
            pass
    
    # --- RANKINGS in right corner of footer ---
    rankings = anime_data.get('rankings', [])
    if rankings:
        ranking_font = ranking_font_loaded  # Use preloaded font
        ranking_x = WIDTH - 50  # Larger padding
        ranking_y = footer_y + (footer_height - 30) // 2  # For larger icon
        
        # Find highest rated and most popular (all time)
        highest_rated = None
        most_popular = None
        
        for r in rankings:
            if r.get('allTime'):
                if r.get('type') == 'RATED' and highest_rated is None:
                    highest_rated = r
                elif r.get('type') == 'POPULAR' and most_popular is None:
                    most_popular = r
        
        # Draw rankings from right to left
        STAR_COLOR = (247, 191, 99)    # Golden yellow for star
        HEART_COLOR = (232, 93, 117)   # Pink/coral for heart
        
        # Most Popular (draw first since we're going right to left)
        if most_popular:
            pop_text = f"#{most_popular['rank']} Most Popular All Time"
            bbox = draw.textbbox((0, 0), pop_text, font=ranking_font)
            text_w = bbox[2] - bbox[0]
            ranking_x -= text_w
            draw.text((ranking_x, ranking_y), pop_text, font=ranking_font, fill=TEXT_LIGHT)
            
            # Heart icon - paste PNG image
            ranking_x -= 35  # Larger gap
            result = draw_material_icon(draw, "heart", ranking_x, ranking_y, 28, HEART_COLOR)  # Larger icon
            if result:  # PNG returned as (image, position)
                heart_img, pos = result
                canvas.paste(heart_img, pos, heart_img)
            
            ranking_x -= 40  # Larger gap between rankings
        
        # Highest Rated
        if highest_rated:
            rated_text = f"#{highest_rated['rank']} Highest Rated All Time"
            bbox = draw.textbbox((0, 0), rated_text, font=ranking_font)
            text_w = bbox[2] - bbox[0]
            ranking_x -= text_w
            draw.text((ranking_x, ranking_y), rated_text, font=ranking_font, fill=TEXT_LIGHT)
            
            # Star icon
            ranking_x -= 35  # Larger gap
            result = draw_material_icon(draw, "star", ranking_x, ranking_y, 28, STAR_COLOR)  # Larger icon
            if result:  # PNG returned as (image, position)
                star_img, pos = result
                canvas.paste(star_img, pos, star_img)
    
    # Output
    bio = BytesIO()
    canvas.convert('RGB').save(bio, 'JPEG', quality=99)
    bio.seek(0)
    return bio
