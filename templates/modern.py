"""
Modern Poster Generator

Generates a modern, visually rich anime poster at 1920x1080 resolution.
Features dynamic color extraction from cover image for cohesive palette.

Features:
- Full background with cover image + gradient overlay
- Sidebar navigation with material icons
- Genre pills with dynamic colors
- Title, season, year, and info section
- Character card with description
- Overview section

Style: Modern gradient-heavy UI with vibrant accents
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Edit these values to customize the template
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Canvas Size ───
CANVAS_WIDTH = 1920                      # Output image width in pixels
CANVAS_HEIGHT = 1080                     # Output image height in pixels

# ─── Layout Dimensions ───
SIDEBAR_WIDTH = 120                      # Left sidebar width
MARGIN_LEFT = 180                        # Main content left margin
COLUMN_RIGHT_X = 1350                    # Right column X position

# ─── Colors (RGB tuples) ───
BG_BASE = (15, 15, 25)                   # Base background color
SIDEBAR_TOP = (12, 12, 17)               # Sidebar gradient top
SIDEBAR_BOTTOM = (20, 20, 25)            # Sidebar gradient bottom
TEXT_WHITE = (255, 255, 255)             # White text
TEXT_MUTED = (204, 204, 204)             # Muted icon color
PILL_RADIUS = 24                         # Genre pill corner radius

# ─── Fallback Accent Colors ───
FALLBACK_COLORS = [
    ("#E74C3C", "#C0392B"),              # Red
    ("#E67E22", "#D35400"),              # Orange
    ("#9B59B6", "#8E44AD"),              # Purple
    ("#E91E63", "#C2185B"),              # Pink
    ("#F39C12", "#E67E22"),              # Yellow
]

# ─── Typography ───
FONT_HEADER_SIZE = 39                    # Site header font size
FONT_TITLE_SIZE = 93                     # Main title font size
FONT_SEASON_SIZE = 51                    # Season/year font size
FONT_SECTION_SIZE = 33                   # Section header font size
FONT_BODY_SIZE = 27                      # Body text font size
FONT_INFO_SIZE = 24                      # Info label font size
FONT_BUTTON_SIZE = 27                    # Button/pill font size

# ─── Output Configuration ───
OUTPUT_FORMAT = "JPEG"                   # Output format (JPEG or PNG)
OUTPUT_QUALITY = 99                      # JPEG quality (1-100)

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

import os
import math
from io import BytesIO
import textwrap
from pathlib import Path

# Project imports
from poster_utils import _pb_get_fonts as get_fonts  # patched
from poster_utils import load_image, extract_colors, add_corners, draw_material_icon, colorize_image  # patched

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
    Create a modern-style anime poster.
    
    Args:
        anime_data: Dict with anime info from AniList API
        
    Returns:
        BytesIO object containing the generated JPEG image
    """
    # Use constants from configuration
    WIDTH, HEIGHT = CANVAS_WIDTH, CANVAS_HEIGHT
    
    # Create base canvas
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG_BASE + (255,))
    
    # ─── Background Image ───
    bg_url = anime_data['coverImage'].get('extraLarge') or anime_data.get('bannerImage')
    if bg_url:
        bg = load_image(bg_url)
        if bg:
            img_w, img_h = bg.size
            src_ratio = img_w / img_h
            dst_ratio = WIDTH / HEIGHT
            
            # CROP TO FILL - Always cover entire canvas, no black borders
            if src_ratio > dst_ratio:
                # Image is wider - scale to height, crop width
                new_h = HEIGHT
                new_w = int(new_h * src_ratio)
            else:
                # Image is taller - scale to width, crop height
                new_w = WIDTH
                new_h = int(new_w / src_ratio)
            
            bg_resized = bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Center crop to canvas size
            left = (new_w - WIDTH) // 2
            top = (new_h - HEIGHT) // 2
            bg_cropped = bg_resized.crop((left, top, left + WIDTH, top + HEIGHT))
            
            final_bg = bg_cropped.convert("RGBA")
            
            # Base dark overlay for entire image
            base_overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 120))
            final_bg = Image.alpha_composite(final_bg, base_overlay)
            
            # Then gradient overlay for text areas
            overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
            draw_overlay = ImageDraw.Draw(overlay)
            
            # Smooth blended gradient - stronger intensity (scaled for 1920x1080)
            import math
            for x in range(WIDTH):
                if x < 900:  # Scaled from 600
                    # Left gradient - stronger
                    progress = x / 900
                    eased = 1 - pow(1 - progress, 3)
                    alpha = int(220 * (1 - eased))  # 220 -> 0
                elif x > 1050:  # Scaled from 700
                    # Right gradient - stronger
                    progress = (x - 1050) / (WIDTH - 1050)
                    eased = pow(progress, 2)
                    alpha = int(50 + eased * 180)  # 50 -> 230
                else:
                    # Middle transition zone
                    mid_progress = (x - 900) / 150
                    alpha = int(30 * (1 - mid_progress) + 50 * mid_progress)  # 30 -> 50
                
                draw_overlay.line((x, 0, x, HEIGHT), fill=(0, 0, 0, alpha))
            
            canvas = Image.alpha_composite(final_bg, overlay)
            
            # Extract dynamic colors from background
            dynamic_colors = extract_colors(bg)
    
    # Fallback colors if no background
    if 'dynamic_colors' not in dir() or not dynamic_colors:
        dynamic_colors = [
            ("#E74C3C", "#C0392B"),
            ("#E67E22", "#D35400"),
            ("#9B59B6", "#8E44AD"),
            ("#E91E63", "#C2185B"),
            ("#F39C12", "#E67E22"),
        ]
    
    # Primary accent color (first extracted color)
    primary_accent = dynamic_colors[0][0]
    secondary_accent = dynamic_colors[1][0] if len(dynamic_colors) > 1 else primary_accent

    draw = ImageDraw.Draw(canvas)

    # --- MODERN SIDEBAR ---
    sidebar_w = 120  # Scaled from 80
    # Gradient sidebar background
    for y in range(HEIGHT):
        progress = y / HEIGHT
        shade = int(12 + progress * 8)
        draw.line((0, y, sidebar_w, y), fill=(shade, shade, shade + 5, 255))
    
    # Modern Material Icons with labels (scaled for 1920x1080)
    icons = [("home", "HOME", 330), ("search", "SEARCH", 450), 
             ("grid", "GENRE", 570), ("star", "RATE", 690)]  # Changed category to grid
    
    # Load mini font for sidebar labels early
    try:
        sidebar_mini_font = ImageFont.truetype(get_fonts().get("Poppins-Regular", "arial.ttf"), 12)  # Scaled
    except:
        sidebar_mini_font = ImageFont.load_default()
    
    for icon_name, label, icon_y in icons:
        result = draw_material_icon(draw, icon_name, sidebar_w // 2 - 18, icon_y, 36, (204, 204, 204))  # Larger icons
        if result:  # PNG returned as (image, position)
            icon_img, pos = result
            canvas.paste(icon_img, pos, icon_img)
        
        # Icon label
        try:
            bbox = draw.textbbox((0, 0), label, font=sidebar_mini_font)
            label_w = bbox[2] - bbox[0]
            draw.text((sidebar_w // 2 - label_w // 2, icon_y + 42), label,  # Scaled offset
                     font=sidebar_mini_font, fill="#666666")
        except:
            pass
        
    # Active indicator - animated gradient bar
    active_y = 330  # Scaled
    for i in range(60):  # Scaled
        progress = i / 60
        draw.line((0, active_y + i, 6, active_y + i),  # Wider bar
                 fill=(255, int(215 - progress * 20), int(progress * 50), 255))
    
    # Load Google Fonts - Multiple font families for variety (scaled for 1920x1080)
    # - Overpass: Headers and titles (bold, impactful)
    # - Roboto: Body text and descriptions (clean, readable)
    # - Poppins: UI elements like buttons, pills (modern)
    try:
        google_fonts = get_fonts()
        
        # Site header - Poppins Bold
        header_font = ImageFont.truetype(
            google_fonts.get("Poppins-Bold", "arialbd.ttf"), 39  # Scaled from 26
        )
        
        # Main title - Overpass Bold or Poppins Bold fallback
        title_font = ImageFont.truetype(
            google_fonts.get("Overpass-Bold", google_fonts.get("Poppins-Bold", "arialbd.ttf")), 93  # Scaled from 62
        )
        
        # Season/Year - Poppins SemiBold
        season_font = ImageFont.truetype(
            google_fonts.get("Poppins-SemiBold", "arialbd.ttf"), 51  # Scaled from 34
        )
        
        # Button/Pills font - Poppins Medium
        button_font = ImageFont.truetype(
            google_fonts.get("Poppins-Medium", "arialbd.ttf"), 27  # Scaled from 18
        )
        
        # Section headers - Poppins Bold
        section_header_font = ImageFont.truetype(
            google_fonts.get("Poppins-Bold", "arialbd.ttf"), 33  # Scaled from 22
        )
        
        # Body/Description text - Roboto Regular
        text_font = ImageFont.truetype(
            google_fonts.get("Roboto-Regular", google_fonts.get("Poppins-Regular", "arial.ttf")), 27  # Scaled from 18
        )
        
        # Character name - Poppins Bold
        char_name_font = ImageFont.truetype(
            google_fonts.get("Poppins-Bold", "arialbd.ttf"), 42  # Scaled from 28
        )
        
        # Info labels - Roboto Regular (smaller)
        info_font = ImageFont.truetype(
            google_fonts.get("Roboto-Regular", google_fonts.get("Poppins-Regular", "arial.ttf")), 24  # Scaled from 16
        )
        
        # Sidebar mini labels - Poppins Regular
        mini_font = ImageFont.truetype(
            google_fonts.get("Poppins-Regular", "arial.ttf"), 12  # Scaled from 9
        )
    except Exception as e:
        print(f"Font loading error: {e}, using fallback")
        header_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        season_font = ImageFont.load_default()
        button_font = ImageFont.load_default()
        section_header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        char_name_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        mini_font = ImageFont.load_default()

    # --- LEFT COLUMN ---
    margin_left = 180  # Scaled from 120
    
    # 1. Site Header with glow effect
    header_text = "BLAZE_UPDATEZ"
    # Shadow/glow
    draw.text((margin_left + 2, 62), header_text, font=header_font, fill=(100, 100, 120, 150))  # Scaled
    draw.text((margin_left, 60), header_text, font=header_font, fill="#FFFFFF")  # Scaled from 40
    
    # 2. Genre Pills - Dynamic colors from background
    genres = anime_data.get('genres', [])[:5]
    pill_x = margin_left
    pill_y = 132  # Scaled from 88
    
    # Use dynamically extracted colors
    
    for idx, genre in enumerate(genres):
        txt = genre.upper()
        bbox = draw.textbbox((0, 0), txt, font=button_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        # Fixed pill dimensions with generous padding (scaled)
        padding_x = 27  # Scaled from 18
        padding_y = 12  # Scaled from 8
        pill_w = text_w + padding_x * 2
        pill_h = 48  # Scaled from 32
        
        # Get color from dynamic palette
        color1, _ = dynamic_colors[idx % len(dynamic_colors)]
        r, g, b = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        
        # Draw solid rounded rectangle
        draw.rounded_rectangle(
            [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
            radius=24,  # Scaled from 16
            fill=(r, g, b, 255)
        )
        
        # Text - vertically centered accounting for font baseline
        text_x = pill_x + padding_x
        # Use bbox[1] (top offset) to correct for baseline
        text_y = pill_y + (pill_h - text_h) // 2 - bbox[1]
        draw.text((text_x, text_y), txt, font=button_font, fill="white")
        
        pill_x += pill_w + 15  # Scaled from 10

    # 3. Anime Title with shadow
    current_y = 222  # Scaled from 148
    title_text = anime_data['title']['english'] or anime_data['title']['romaji']
    title_wrapper = textwrap.TextWrapper(width=16)  # Adjusted for larger font
    for line in title_wrapper.wrap(title_text.upper()):
        # Shadow
        draw.text((margin_left + 3, current_y + 3), line, font=title_font, fill=(0, 0, 0, 120))
        # Main text
        draw.text((margin_left, current_y), line, font=title_font, fill="#FFFFFF")
        current_y += 93  # Scaled from 62
        
    # 4. Season & Year with icon
    season = anime_data.get('season', '')
    year = anime_data.get('seasonYear', '')
    if season and year:
        season_text = f"{season} {year}".upper()
        draw.text((margin_left, current_y), season_text, font=season_font, fill="#FFD700")
        current_y += 72  # Scaled from 48
    
    current_y += 27  # Scaled from 18
    
    # 5. Information Section - no separate background
    current_y += 15  # Scaled from 10
    draw.text((margin_left, current_y), "INFORMATION", font=section_header_font, fill=primary_accent)
    current_y += 42  # Scaled from 28
    
    studio_name = "N/A"
    if anime_data['studios']['nodes']:
        studio_name = anime_data['studios']['nodes'][0]['name']
        
    info_items = [
        ("STUDIO", studio_name),
        ("STATUS", anime_data.get('status', 'N/A')),
        ("RATING", f"{anime_data.get('averageScore', 'N/A')}/100")
    ]
    
    for label, value in info_items:
        # Gold bullet
        draw.text((margin_left, current_y), ">", font=text_font, fill=primary_accent)
        # Text
        text = f"{label} : {value}"
        draw.text((margin_left + 24, current_y), text, font=text_font, fill="#FFFFFF")  # Scaled from 16
        current_y += 36  # Scaled from 24


    # --- RIGHT COLUMN ---
    col_right_x = 1350  # Moved more to the right
    current_right_y = 87  # Scaled from 58
    
    # 6. Character Card - Modern design
    char_node = None
    if anime_data.get('characters') and anime_data['characters']['edges']:
        char_node = anime_data['characters']['edges'][0]['node']
        
    if char_node and char_node.get('image') and char_node['image'].get('large'):
        char_url = char_node['image']['large']
        char_img = load_image(char_url)
        
        if char_img:
            card_w, card_h = 480, 300  # Scaled from 320, 200
            
            img_ratio = char_img.width / char_img.height
            target_ratio = card_w / card_h
            
            if img_ratio > target_ratio:
                new_h = card_h
                new_w = int(new_h * img_ratio)
            else:
                new_w = card_w
                new_h = int(new_w / img_ratio)
                
            char_img = char_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            left = (new_w - card_w) / 2
            top = (new_h - card_h) / 2
            char_img = char_img.crop((left, top, left + card_w, top + card_h))
            
            # Modern rounded corners + border
            char_img = add_corners(char_img, 30)  # Scaled from 20
            
            # Add subtle border/glow
            # border_img = Image.new('RGBA', (card_w + 4, card_h + 4), (100, 100, 150, 80))
            # border_img = add_corners(border_img, 22)
            # canvas.paste(border_img, (col_right_x - 2, current_right_y - 2), border_img)
            
            canvas.paste(char_img, (col_right_x, current_right_y), char_img)
            current_right_y += card_h + 18  # Scaled from 12
            
            # Character Name with underline accent
            name = char_node['name']['full'].upper()
            draw.text((col_right_x, current_right_y), name, font=char_name_font, fill="#FFFFFF")
            
            # Underline accent - moved lower to not cut text
            name_bbox = draw.textbbox((col_right_x, current_right_y), name, font=char_name_font)
            name_w = name_bbox[2] - name_bbox[0]
            name_h = name_bbox[3] - name_bbox[1]
            draw.line((col_right_x, current_right_y + name_h + 23, col_right_x + min(name_w, 150),  # Scaled
                      current_right_y + name_h + 23), fill=primary_accent, width=7)  # Scaled
            
            current_right_y += name_h + 23 + 10   # Scaled from 15
            
            # Character Description
            # Character Description
            char_desc = char_node.get('description', '')
            
            # Use shared sanitization

            if char_desc:
                char_desc = sanitize_description(char_desc)
                
            if char_desc:
                # Add ellipsis if long
                char_desc_wrapper = textwrap.TextWrapper(width=38)  # Adjusted for larger font
                char_lines = char_desc_wrapper.wrap(char_desc)[:4]  # Allow 4 lines for char info
                
                # Add ellipsis if truncated
                if len(char_desc_wrapper.wrap(char_desc)) > 4:
                    if char_lines:
                        char_lines[-1] = char_lines[-1][:36] + "..."
                
                for line in char_lines:
                    draw.text((col_right_x, current_right_y), line, font=info_font, fill="#FFFFFF")
                    current_right_y += 27  # Scaled from 18
                
                current_right_y += 18  # Scaled from 12
            
    # 7. Overview Section
    current_right_y += 12  # Scaled from 8
    draw.text((col_right_x, current_right_y), "OVERVIEW", font=section_header_font, fill=secondary_accent)
    current_right_y += 45  # Scaled from 26
    
    desc_text = anime_data.get('description', '')
    if desc_text:
        desc_text = desc_text.replace("<br>", "").replace("<i>", "").replace("</i>", "")
        remaining_h = HEIGHT - current_right_y - 90  # Scaled from 60
        max_lines = max(1, remaining_h // 27)  # Scaled from 18
        
        wrapper = textwrap.TextWrapper(width=38)  # Adjusted for larger font
        all_lines = wrapper.wrap(desc_text)
        lines = all_lines[:max_lines]
        
        # Add ellipsis if truncated
        if len(all_lines) > max_lines and lines:
            lines[-1] = lines[-1][:36] + "..."
        
        for line in lines:
            draw.text((col_right_x, current_right_y), line, font=text_font, fill="#EEEEEE")
            current_right_y += 30  # Scaled from 20

    # Output
    bio = BytesIO()
    canvas.convert('RGB').save(bio, 'JPEG', quality=99)
    bio.seek(0)
    return bio
