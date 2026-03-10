"""
Core watermarking utilities for PDF and image files.
Supports text and image watermarks with configurable position, opacity,
dimensions, rotation, and tiling.
"""

import io
import math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import fitz  # PyMuPDF


def get_default_font(size: int):
    """Get a font, falling back to default if custom fonts unavailable."""
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except (OSError, IOError):
            try:
                return ImageFont.truetype("arial.ttf", size)
            except (OSError, IOError):
                return ImageFont.load_default()


def create_text_watermark_image(
    text: str,
    font_size: int = 40,
    color: str = "#FFFFFF",
    opacity: float = 0.3,
    rotation: int = 0,
) -> Image.Image:
    """
    Render a text string into an RGBA PIL Image with the given opacity.
    The image is tightly cropped around the text and rotated.
    """
    font = get_default_font(font_size)

    # Measure text
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0] + 20
    text_h = bbox[3] - bbox[1] + 20

    # Draw text
    txt_img = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_img)

    # Parse hex color
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    alpha = int(255 * opacity)

    draw.text((10, 10 - bbox[1]), text, font=font, fill=(r, g, b, alpha))

    # Rotate
    if rotation != 0:
        txt_img = txt_img.rotate(rotation, expand=True, resample=Image.BICUBIC)

    return txt_img


def apply_watermark_to_image(
    base_image: Image.Image,
    watermark_config: dict,
) -> Image.Image:
    """
    Apply a watermark (text or image) onto a PIL Image.

    watermark_config keys:
        type: "text" | "image"
        text, font_size, color  (for text type)
        watermark_image: PIL.Image  (for image type)
        width, height: target watermark size in pixels
        x_position, y_position: 0.0 – 1.0 (relative position on page)
        opacity: 0.0 – 1.0
        rotation: degrees
        tile: bool
    """
    result = base_image.convert("RGBA")
    page_w, page_h = result.size

    wm_type = watermark_config.get("type", "text")
    opacity = watermark_config.get("opacity", 0.3)
    rotation = watermark_config.get("rotation", 0)
    tile = watermark_config.get("tile", False)
    target_w = watermark_config.get("width", 200)
    target_h = watermark_config.get("height", 100)
    x_pos = watermark_config.get("x_position", 0.5)
    y_pos = watermark_config.get("y_position", 0.5)

    # Create watermark image
    if wm_type == "text":
        wm_img = create_text_watermark_image(
            text=watermark_config.get("text", "WATERMARK"),
            font_size=watermark_config.get("font_size", 40),
            color=watermark_config.get("color", "#FFFFFF"),
            opacity=opacity,
            rotation=rotation,
        )
        # Scale to target dimensions
        wm_img = wm_img.resize((target_w, target_h), Image.LANCZOS)
    else:
        wm_img = watermark_config["watermark_image"].copy().convert("RGBA")
        # Rotate first
        if rotation != 0:
            wm_img = wm_img.rotate(rotation, expand=True, resample=Image.BICUBIC)
        # Scale to target dimensions
        wm_img = wm_img.resize((target_w, target_h), Image.LANCZOS)
        # Apply opacity
        if opacity < 1.0:
            alpha = wm_img.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            wm_img.putalpha(alpha)

    if tile:
        result = _tile_watermark(result, wm_img, page_w, page_h)
    else:
        # Position: x_pos/y_pos are 0–1 fractions of the page
        paste_x = int(x_pos * (page_w - wm_img.width))
        paste_y = int(y_pos * (page_h - wm_img.height))
        paste_x = max(0, min(paste_x, page_w - wm_img.width))
        paste_y = max(0, min(paste_y, page_h - wm_img.height))

        overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
        overlay.paste(wm_img, (paste_x, paste_y))
        result = Image.alpha_composite(result, overlay)

    return result


def _tile_watermark(
    base: Image.Image, wm: Image.Image, page_w: int, page_h: int
) -> Image.Image:
    """Tile the watermark across the entire page with gaps."""
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gap_x = max(wm.width // 2, 30)
    gap_y = max(wm.height // 2, 30)
    step_x = wm.width + gap_x
    step_y = wm.height + gap_y

    y = 0
    while y < page_h:
        x = 0
        while x < page_w:
            overlay.paste(wm, (x, y), wm)
            x += step_x
        y += step_y

    return Image.alpha_composite(base, overlay)


# --------------- PDF functions ---------------

def pdf_page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages in a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count


def preview_pdf_pages(
    pdf_bytes: bytes,
    page_indices: list[int],
    dpi: int = 150,
) -> list[Image.Image]:
    """Render specific PDF pages to PIL Images."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for idx in page_indices:
        if 0 <= idx < len(doc):
            page = doc[idx]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
    doc.close()
    return images


def apply_watermark_to_pdf(
    pdf_bytes: bytes,
    watermark_config: dict,
) -> bytes:
    """
    Apply watermark to every page of a PDF.
    Returns the watermarked PDF as bytes.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    wm_type = watermark_config.get("type", "text")
    opacity = watermark_config.get("opacity", 0.3)
    rotation = watermark_config.get("rotation", 0)
    tile = watermark_config.get("tile", False)
    x_pos = watermark_config.get("x_position", 0.5)
    y_pos = watermark_config.get("y_position", 0.5)

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_rect = page.rect
        page_w = page_rect.width
        page_h = page_rect.height

        # Target dimensions in PDF points (1 point = 1/72 inch)
        # The user controls these via sliders (as percentage of page)
        wm_w_pct = watermark_config.get("width_pct", 30)
        wm_h_pct = watermark_config.get("height_pct", 15)
        target_w = page_w * wm_w_pct / 100
        target_h = page_h * wm_h_pct / 100

        if wm_type == "text":
            _apply_text_watermark_to_pdf_page(
                page, watermark_config, target_w, target_h,
                x_pos, y_pos, opacity, rotation, tile, page_w, page_h
            )
        else:
            _apply_image_watermark_to_pdf_page(
                page, watermark_config, target_w, target_h,
                x_pos, y_pos, opacity, rotation, tile, page_w, page_h
            )

    out_bytes = doc.tobytes(deflate=True, garbage=4)
    doc.close()
    return out_bytes


def _apply_text_watermark_to_pdf_page(
    page, config, target_w, target_h,
    x_pos, y_pos, opacity, rotation, tile, page_w, page_h
):
    """Insert text watermark onto a PDF page using PyMuPDF."""
    text = config.get("text", "WATERMARK")
    font_size = config.get("font_size", 40)
    color_hex = config.get("color", "#FFFFFF")

    # Parse color to 0–1 float tuple
    r = int(color_hex[1:3], 16) / 255
    g = int(color_hex[3:5], 16) / 255
    b = int(color_hex[5:7], 16) / 255

    # Create a watermark image and insert it as an image overlay
    # This gives us full control over opacity, rotation, and tiling
    wm_img = create_text_watermark_image(
        text=text,
        font_size=font_size,
        color=color_hex,
        opacity=opacity,
        rotation=rotation,
    )

    # Scale to target dimensions in pixels (use 2x for quality)
    px_w = int(target_w * 2)
    px_h = int(target_h * 2)
    wm_img = wm_img.resize((px_w, px_h), Image.LANCZOS)

    if tile:
        _tile_watermark_on_pdf_page(page, wm_img, target_w, target_h, page_w, page_h)
    else:
        paste_x = x_pos * (page_w - target_w)
        paste_y = y_pos * (page_h - target_h)
        rect = fitz.Rect(paste_x, paste_y, paste_x + target_w, paste_y + target_h)

        img_bytes = _pil_to_png_bytes(wm_img)
        page.insert_image(rect, stream=img_bytes, overlay=True)


def _apply_image_watermark_to_pdf_page(
    page, config, target_w, target_h,
    x_pos, y_pos, opacity, rotation, tile, page_w, page_h
):
    """Insert image watermark onto a PDF page."""
    wm_img = config["watermark_image"].copy().convert("RGBA")

    if rotation != 0:
        wm_img = wm_img.rotate(rotation, expand=True, resample=Image.BICUBIC)

    # Apply opacity
    if opacity < 1.0:
        alpha = wm_img.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        wm_img.putalpha(alpha)

    # Scale to good pixel resolution
    px_w = int(target_w * 2)
    px_h = int(target_h * 2)
    wm_img = wm_img.resize((px_w, px_h), Image.LANCZOS)

    if tile:
        _tile_watermark_on_pdf_page(page, wm_img, target_w, target_h, page_w, page_h)
    else:
        paste_x = x_pos * (page_w - target_w)
        paste_y = y_pos * (page_h - target_h)
        rect = fitz.Rect(paste_x, paste_y, paste_x + target_w, paste_y + target_h)

        img_bytes = _pil_to_png_bytes(wm_img)
        page.insert_image(rect, stream=img_bytes, overlay=True)


def _tile_watermark_on_pdf_page(page, wm_img, wm_w, wm_h, page_w, page_h):
    """Tile watermark across an entire PDF page."""
    img_bytes = _pil_to_png_bytes(wm_img)
    gap_x = max(wm_w * 0.5, 20)
    gap_y = max(wm_h * 0.5, 20)
    step_x = wm_w + gap_x
    step_y = wm_h + gap_y

    y = 0
    while y < page_h:
        x = 0
        while x < page_w:
            rect = fitz.Rect(x, y, x + wm_w, y + wm_h)
            page.insert_image(rect, stream=img_bytes, overlay=True)
            x += step_x
        y += step_y


def _pil_to_png_bytes(img: Image.Image) -> bytes:
    """Convert a PIL Image to PNG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_sample_page_indices(total_pages: int, max_samples: int = 3) -> list[int]:
    """Return indices of sample pages (first, middle, last)."""
    if total_pages <= 0:
        return []
    if total_pages == 1:
        return [0]
    if total_pages == 2:
        return [0, 1]
    if total_pages <= max_samples:
        return list(range(total_pages))

    # First, middle, last
    return [0, total_pages // 2, total_pages - 1]
