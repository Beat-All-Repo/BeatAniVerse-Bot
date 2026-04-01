"""
poster_utils.py — PosterBot helpers adapted for BeatAniVerse (/app/)
Provides load_image, create_gradient_overlay, add_corners, sanitize_description,
colorize_icon, load_icon used by templates/*.py
Also exposes _pb_get_fonts() used as a drop-in for PosterBot's fonts.get_fonts()
"""
from pathlib import Path
import os

_APP_DIR = Path(__file__).parent
_FONTS_DIR = _APP_DIR / "fonts"
_ICONS_DIR = _APP_DIR / "iconspng"

from PIL import ImageFont as _IFont

def _pb_get_fonts(size: int = 20, style: str = "regular") -> _IFont.FreeTypeFont:
    """Drop-in for PosterBot's fonts.get_fonts() — returns a PIL font."""
    _map = {
        "bold":       "Poppins-Bold.ttf",
        "semibold":   "Poppins-SemiBold.ttf",
        "medium":     "Poppins-Medium.ttf",
        "regular":    "Poppins-Regular.ttf",
        "black":      "Poppins-Black.ttf",
        "bebas":      "BebasNeue Bold.otf",
        "bebas-bold": "BebasNeue Bold.otf",
        "dmsans":     "DMSans-Regular.ttf",
        "dmsans-bold":"DMSans-Bold.ttf",
    }
    fname = _map.get(style.lower(), "Poppins-Regular.ttf")
    fpath = _FONTS_DIR / fname
    try:
        return _IFont.truetype(str(fpath), size)
    except Exception:
        return _IFont.load_default()

# Alias used by old PosterBot get_fonts() return value
def get_font(size: int = 20, style: str = "regular"):
    return _pb_get_fonts(size, style)

"""
Shared Poster Utilities
=======================

This module contains shared helper functions for image manipulation, text rendering,
and data processing used across various poster templates.

Features:
- Image downloading and caching
- Gradient generation (linear, radial)
- Text wrapping and rendering
- Icon processing (colorizing, resizing)
- Character description sanitization
"""

import math
import re
import requests
from io import BytesIO
from pathlib import Path
from colorsys import rgb_to_hsv, hsv_to_rgb
from PIL import Image, ImageDraw, ImageFont

# NumPy import (lazy to avoid slow startup if not needed)
_numpy = None

def _get_numpy():
    """Lazy import of NumPy for faster module loading."""
    global _numpy
    if _numpy is None:
        import numpy as np
        _numpy = np
    return _numpy


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_image(url: str, timeout: int = 15) -> Image.Image:
    """
    Download an image from a URL and return as RGBA PIL Image.
    
    Args:
        url: URL of the image to download
        timeout: Request timeout in seconds (default: 15)
        
    Returns:
        PIL Image in RGBA mode, or None if download fails
        
    Example:
        >>> img = load_image("https://example.com/poster.jpg")
        >>> if img:
        ...     print(f"Loaded {img.size[0]}x{img.size[1]}")
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None


def load_icon(name: str, size: tuple = None, icons_dir: Path = None) -> Image.Image:
    """
    Load an icon from the icons directory.
    
    Args:
        name: Icon filename (e.g., "star.png", "heart.png")
        size: Optional (width, height) tuple to resize icon
        icons_dir: Custom icons directory (default: ./iconspng)
        
    Returns:
        PIL Image in RGBA mode, or placeholder if not found
        
    Example:
        >>> star = load_icon("star.png", size=(32, 32))
        >>> canvas.paste(star, (100, 100), star)
    """
    if icons_dir is None:
        icons_dir = _ICONS_DIR
    
    icon_path = icons_dir / name
    
    if not icon_path.exists():
        # Return transparent placeholder
        return Image.new('RGBA', size or (32, 32), (255, 255, 255, 128))
    
    icon = Image.open(icon_path).convert('RGBA')
    if size:
        icon = icon.resize(size, Image.Resampling.LANCZOS)
    return icon


# ═══════════════════════════════════════════════════════════════════════════════
# ICON COLORIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def colorize_icon(icon: Image.Image, color: tuple) -> Image.Image:
    """
    Apply a solid color to an icon while preserving its alpha channel.
    Uses NumPy for fast vectorized operations.
    
    Args:
        icon: PIL Image (should be RGBA)
        color: RGB tuple like (255, 100, 10) or RGBA tuple
        
    Returns:
        New PIL Image with color applied
        
    Example:
        >>> icon = load_icon("star.png", (24, 24))
        >>> orange_icon = colorize_icon(icon, (255, 100, 10))
    """
    np = _get_numpy()
    
    arr = np.array(icon)
    r, g, b = color[:3]
    
    # Create output with same alpha, but new RGB
    result = np.zeros_like(arr)
    result[..., 0] = r
    result[..., 1] = g
    result[..., 2] = b
    result[..., 3] = arr[..., 3]  # Keep original alpha
    
    return Image.fromarray(result.astype(np.uint8), 'RGBA')


def colorize_image(image: Image.Image, color) -> Image.Image:
    """
    Apply a solid color to an image while preserving alpha channel.
    Supports both RGB tuples and hex color strings.
    
    Args:
        image: PIL Image (should be RGBA)
        color: RGB tuple like (255, 100, 10) OR hex string like "#ff640a"
        
    Returns:
        New PIL Image with color applied
        
    Example:
        >>> img = colorize_image(icon, "#ff640a")  # Hex color
        >>> img = colorize_image(icon, (255, 100, 10))  # RGB tuple
    """
    if isinstance(color, str):
        if color.startswith('#'):
            color = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        else:
            color = (255, 255, 255)
    
    colored = Image.new('RGBA', image.size, color + (255,))
    colored.putalpha(image.split()[3])
    return colored


# ═══════════════════════════════════════════════════════════════════════════════
# GRADIENT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def create_gradient_overlay(
    width: int, 
    height: int,
    direction: str = "bottom",
    start_alpha: int = 0,
    end_alpha: int = 255,
    start_position: float = 0.5,
    color: tuple = (0, 0, 0)
) -> Image.Image:
    """
    Create a gradient overlay image. Uses NumPy for fast generation.
    
    Args:
        width: Output image width
        height: Output image height
        direction: Gradient direction - "bottom", "top", "left", "right"
        start_alpha: Alpha value at start (0-255)
        end_alpha: Alpha value at end (0-255)
        start_position: Position where gradient starts (0.0-1.0)
        color: RGB color for the gradient (default: black)
        
    Returns:
        PIL RGBA Image with gradient
        
    Example:
        >>> # Fade to black at bottom 50%
        >>> gradient = create_gradient_overlay(1920, 1080, "bottom", 0, 255, 0.5)
        >>> canvas = Image.alpha_composite(canvas, gradient)
    """
    np = _get_numpy()
    
    # Create coordinate grid
    if direction in ("bottom", "top"):
        coords = np.linspace(0, 1, height).reshape(-1, 1)
        coords = np.tile(coords, (1, width))
        if direction == "top":
            coords = 1 - coords
    else:  # left, right
        coords = np.linspace(0, 1, width).reshape(1, -1)
        coords = np.tile(coords, (height, 1))
        if direction == "left":
            coords = 1 - coords
    
    # Apply start position
    coords = np.clip((coords - start_position) / (1 - start_position), 0, 1)
    
    # Calculate alpha
    alpha = (start_alpha + (end_alpha - start_alpha) * coords).astype(np.uint8)
    
    # Build RGBA image
    result = np.zeros((height, width, 4), dtype=np.uint8)
    result[..., 0] = color[0]
    result[..., 1] = color[1]
    result[..., 2] = color[2]
    result[..., 3] = alpha
    
    return Image.fromarray(result, 'RGBA')


def create_multi_gradient(width: int, height: int, gradients: list) -> Image.Image:
    """
    Create a complex gradient with multiple layers (like CSS multi-gradient).
    
    Args:
        width: Output image width
        height: Output image height
        gradients: List of gradient specs, each a dict with:
            - direction: "bottom", "right", "diagonal" (or angle in degrees)
            - stops: list of (position, alpha) tuples
            
    Returns:
        PIL RGBA Image with combined gradients
        
    Example:
        >>> gradient = create_multi_gradient(1920, 1080, [
        ...     {"direction": "right", "stops": [(0, 217), (0.3, 128), (0.55, 0)]},
        ...     {"direction": "bottom", "stops": [(0.5, 0), (1.0, 255)]}
        ... ])
    """
    np = _get_numpy()
    
    # Start with transparent
    final_alpha = np.zeros((height, width), dtype=np.float32)
    
    for grad in gradients:
        direction = grad.get("direction", "bottom")
        stops = grad.get("stops", [(0, 0), (1, 255)])
        
        # Create coordinate grid based on direction
        if direction == "bottom":
            coords = np.linspace(0, 1, height).reshape(-1, 1)
            coords = np.tile(coords, (1, width))
        elif direction == "right":
            coords = np.linspace(0, 1, width).reshape(1, -1)
            coords = np.tile(coords, (height, 1))
        elif isinstance(direction, (int, float)):
            # Diagonal gradient at angle
            angle_rad = math.radians(direction)
            x = np.arange(width)
            y = np.arange(height)
            xx, yy = np.meshgrid(x, y)
            nx, ny = xx / width, yy / height
            coords = (nx * math.cos(angle_rad) + ny * math.sin(angle_rad) + 1) / 2
        else:
            coords = np.linspace(0, 1, height).reshape(-1, 1)
            coords = np.tile(coords, (1, width))
        
        # Interpolate between stops
        layer_alpha = np.zeros((height, width), dtype=np.float32)
        for i in range(len(stops) - 1):
            pos1, alpha1 = stops[i]
            pos2, alpha2 = stops[i + 1]
            
            mask = (coords >= pos1) & (coords < pos2)
            progress = (coords - pos1) / (pos2 - pos1)
            layer_alpha[mask] = alpha1 + (alpha2 - alpha1) * progress[mask]
        
        # Handle last stop
        layer_alpha[coords >= stops[-1][0]] = stops[-1][1]
        
        # Combine with max
        final_alpha = np.maximum(final_alpha, layer_alpha)
    
    # Build RGBA image
    result = np.zeros((height, width, 4), dtype=np.uint8)
    result[..., 3] = np.clip(final_alpha, 0, 255).astype(np.uint8)
    
    return Image.fromarray(result, 'RGBA')


# ═══════════════════════════════════════════════════════════════════════════════
# FADE EFFECTS
# ═══════════════════════════════════════════════════════════════════════════════

def apply_fade_mask(
    image: Image.Image,
    fade_start: float = 0.7,
    fade_end: float = 1.0,
    direction: str = "bottom"
) -> Image.Image:
    """
    Apply a fade effect to an image's alpha channel.
    Uses NumPy for fast processing.
    
    Args:
        image: PIL RGBA Image to fade
        fade_start: Position where fade begins (0.0-1.0)
        fade_end: Position where fade ends (fully transparent)
        direction: "bottom", "top", "left", "right"
        
    Returns:
        New PIL Image with fade applied
        
    Example:
        >>> # Fade text at bottom 30%
        >>> text_layer = apply_fade_mask(text_layer, 0.7, 1.0, "bottom")
    """
    np = _get_numpy()
    
    arr = np.array(image)
    h, w = arr.shape[:2]
    
    # Create fade values
    if direction in ("bottom", "top"):
        coords = np.linspace(0, 1, h).reshape(-1, 1)
        if direction == "top":
            coords = 1 - coords
    else:
        coords = np.linspace(0, 1, w).reshape(1, -1)
        if direction == "left":
            coords = 1 - coords
    
    # Calculate fade multiplier
    fade_mult = np.ones((h, w), dtype=np.float32)
    fade_zone = (coords >= fade_start) & (coords <= fade_end)
    progress = (coords - fade_start) / (fade_end - fade_start)
    fade_mult = np.where(fade_zone, 1 - progress, fade_mult)
    fade_mult = np.where(coords > fade_end, 0, fade_mult)
    
    # Apply to alpha channel
    arr[..., 3] = (arr[..., 3].astype(np.float32) * fade_mult).astype(np.uint8)
    
    return Image.fromarray(arr, 'RGBA')


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE EFFECTS
# ═══════════════════════════════════════════════════════════════════════════════

def add_corners(im: Image.Image, radius: int) -> Image.Image:
    """
    Add rounded corners to an image.
    
    Args:
        im: PIL Image (will be converted to RGBA)
        radius: Corner radius in pixels
        
    Returns:
        PIL Image with rounded corners
        
    Example:
        >>> cover = add_corners(cover_image, 8)
    """
    circle = Image.new('L', (radius * 2, radius * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)
    
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    
    alpha.paste(circle.crop((0, 0, radius, radius)), (0, 0))
    alpha.paste(circle.crop((0, radius, radius, radius * 2)), (0, h - radius))
    alpha.paste(circle.crop((radius, 0, radius * 2, radius)), (w - radius, 0))
    alpha.paste(circle.crop((radius, radius, radius * 2, radius * 2)), (w - radius, h - radius))
    
    im.putalpha(alpha)
    return im


def extract_colors(image: Image.Image, num_colors: int = 5) -> list:
    """
    Extract dominant colors and generate a harmonious theme palette.
    
    Args:
        image: PIL Image to analyze
        num_colors: Number of palette colors to generate
        
    Returns:
        List of (light_hex, dark_hex) tuples for each color
        
    Example:
        >>> palette = extract_colors(cover_image, 5)
        >>> primary_light, primary_dark = palette[0]
    """
    img = image.copy()
    img.thumbnail((80, 80))
    
    pixels = list(img.getdata())
    
    best_color = None
    best_score = 0
    
    for p in pixels:
        if len(p) >= 3:
            r, g, b = p[0], p[1], p[2]
            brightness = (r + g + b) / 3
            saturation = max(r, g, b) - min(r, g, b)
            
            if 50 < brightness < 200 and saturation > 50:
                score = saturation * (1 - abs(brightness - 120) / 120)
                if score > best_score:
                    best_score = score
                    best_color = (r, g, b)
    
    if not best_color:
        best_color = (200, 60, 60)
    
    r, g, b = best_color
    h, s, v = rgb_to_hsv(r/255, g/255, b/255)
    
    palette = []
    shifts = [0, 0.08, -0.08, 0.15, -0.15][:num_colors]
    
    for shift in shifts:
        h2 = (h + shift) % 1.0
        r2, g2, b2 = hsv_to_rgb(h2, min(1.0, s * 1.1), min(1.0, v * 1.1))
        c = (int(r2*255), int(g2*255), int(b2*255))
        light = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
        dark = f"#{max(0,c[0]-50):02x}{max(0,c[1]-50):02x}{max(0,c[2]-50):02x}"
        palette.append((light, dark))
    
    return palette


# ═══════════════════════════════════════════════════════════════════════════════
# MATERIAL ICONS
# ═══════════════════════════════════════════════════════════════════════════════

def draw_material_icon(draw, icon_name: str, x: int, y: int, size: int = 24, color="white"):
    """
    Draw Material Design inspired icons using PNG files or fallback shapes.
    
    Args:
        draw: PIL ImageDraw object
        icon_name: Icon name ("star", "heart", "home", "search", "grid")
        x: X position
        y: Y position
        size: Icon size in pixels
        color: Color as RGB tuple or hex string
        
    Returns:
        For PNG icons: (PIL Image, (x, y)) tuple to paste
        For shape icons: None (drawn directly)
        
    Example:
        >>> result = draw_material_icon(draw, "star", 100, 100, 24, (255, 200, 0))
        >>> if result:
        ...     icon_img, pos = result
        ...     canvas.paste(icon_img, pos, icon_img)
    """
    half = size // 2
    cx, cy = x + half, y + half
    
    # Icons that use PNG files
    png_icons = ["home", "search", "grid", "star", "heart"]
    
    if icon_name in png_icons:
        icon_path = Path(__file__).parent / 'iconspng' / f'{icon_name}.png'
        try:
            icon_img = Image.open(icon_path).convert("RGBA")
            icon_img = icon_img.resize((size, size), Image.Resampling.LANCZOS)
            icon_img = colorize_image(icon_img, color)
            return icon_img, (x, y)
        except:
            pass  # Fallback to shapes
    
    # Fallback polygon shapes
    if icon_name == "home":
        points = [(cx, cy - half + 4), (cx + half - 4, cy), (cx + half - 8, cy), 
                  (cx + half - 8, cy + half - 4), (cx - half + 8, cy + half - 4), 
                  (cx - half + 8, cy), (cx - half + 4, cy)]
        draw.polygon(points, fill=color)
    elif icon_name == "search":
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], outline=color, width=2)
        draw.line([cx + 6, cy + 6, cx + 12, cy + 12], fill=color, width=2)
    elif icon_name in ("category", "grid"):
        for i in range(2):
            for j in range(2):
                sx = cx - 8 + i * 10
                sy = cy - 8 + j * 10
                draw.rectangle([sx, sy, sx + 6, sy + 6], fill=color)
    elif icon_name == "star":
        points = []
        outer_r = size * 0.42
        inner_r = size * 0.17
        for i in range(5):
            angle = math.radians(-90 + i * 72)
            points.append((cx + outer_r * math.cos(angle), cy + outer_r * math.sin(angle)))
            angle = math.radians(-90 + i * 72 + 36)
            points.append((cx + inner_r * math.cos(angle), cy + inner_r * math.sin(angle)))
        draw.polygon(points, fill=color)
    elif icon_name == "heart":
        scale = size / 16
        heart_points = [
            (cx, cy + 6 * scale),
            (cx - 6 * scale, cy),
            (cx - 6 * scale, cy - 3 * scale),
            (cx, cy - 6 * scale),
            (cx + 6 * scale, cy - 3 * scale),
            (cx + 6 * scale, cy),
        ]
        draw.polygon(heart_points, fill=color)


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def sanitize_description(desc: str) -> str:
    """
    Sanitizes AniList description text.
    Combines robust metadata removal with safe text formatting.
    """
    if not desc:
        return ""


    # 1. Remove Spoilers (~! ... !~)
    # Standard AniList spoiler handling
    desc = re.sub(r'~!.*?!~', '', desc, flags=re.DOTALL)
    
    # 2. Remove Metadata (User's Robust Regex)
    # Handles:
    # - Colon inside bold: __Key:__ Value
    # - Colon outside bold: __Key__: Value
    # - Inline metadata: __Key:__ Val __Key2:__ Val
    # Note: We rely on the lookahead (?=...|\n|$) to stop at newlines, 
    # so we can safely use DOTALL or not, but usually this works best per-line.
    metadata_pattern = r'(__|\*\*)[^\n]+?(:[^\n]*?(__|\*\*)|(__|\*\*)\s*:).*?(?=__|\*\*|\n|$)'
    desc = re.sub(metadata_pattern, '', desc, flags=re.DOTALL)
    
    # 3. Flatten Links ([Text](url) -> Text)
    desc = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', desc)
    
    # 4. Remove leftover formatting (Safety Fix)
    # Only remove the bold markers (__ and **) that might remain.
    # CRITICAL: Do NOT remove '!' or '~' so we don't break sentences like "He is strong!"
    desc = re.sub(r'(__|\*\*)', '', desc)
    
    # 5. Fix Whitespace (Paragraph Preservation)
    # Collapse 3+ newlines into 2 (preserving paragraphs)
    desc = re.sub(r'\n{3,}', '\n\n', desc)
    # Collapse multiple spaces into one
    desc = re.sub(r'[ \t]+', ' ', desc)
    
    return desc.strip()
