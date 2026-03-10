"""
Watermark Studio — A Streamlit application to add watermarks to PDFs and images.
Supports text and image watermarks with configurable dimensions, position,
opacity, rotation, and tiling. Provides live preview before generating output.
"""

import io
import streamlit as st
from PIL import Image
from watermark_utils import (
    apply_watermark_to_image,
    apply_watermark_to_pdf,
    preview_pdf_pages,
    pdf_page_count,
    get_sample_page_indices,
)


# ──────────────────────── Page Config ────────────────────────

st.set_page_config(
    page_title="Watermark Studio",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────── Custom CSS ─────────────────────────

st.markdown("""
<style>
    /* Header gradient */
    .main-header {
        background: linear-gradient(135deg, #6C63FF 0%, #3B82F6 50%, #06B6D4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0;
        padding: 0;
        letter-spacing: -0.5px;
    }
    .sub-header {
        text-align: center;
        color: #94A3B8;
        font-size: 1.05rem;
        margin-top: -8px;
        margin-bottom: 30px;
        font-weight: 400;
    }

    /* Card containers */
    .preview-card {
        background: linear-gradient(145deg, #1A1D29 0%, #12141D 100%);
        border: 1px solid #2A2D3A;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0E1117 0%, #141824 100%);
    }
    section[data-testid="stSidebar"] .stRadio > label {
        font-weight: 600;
    }

    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #6C63FF, #3B82F6) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 32px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(108,99,255,0.4) !important;
    }

    /* Upload area */
    [data-testid="stFileUploader"] {
        border-radius: 12px;
    }

    /* Section labels */
    .section-label {
        color: #6C63FF;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 8px;
        margin-top: 16px;
    }

    /* Badge */
    .badge {
        display: inline-block;
        background: rgba(108,99,255,0.15);
        color: #6C63FF;
        padding: 3px 10px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 8px;
    }

    /* Preview page label */
    .page-label {
        text-align: center;
        color: #64748B;
        font-size: 0.85rem;
        margin-top: 4px;
        margin-bottom: 12px;
    }

    /* Divider */
    .custom-divider {
        border: none;
        border-top: 1px solid #2A2D3A;
        margin: 16px 0;
    }

    /* Hide default header */
    header[data-testid="stHeader"] {
        background: transparent;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────── Header ─────────────────────────────

st.markdown('<h1 class="main-header">💧 Watermark Studio</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Add professional watermarks to your PDFs and images with full control</p>', unsafe_allow_html=True)


# ──────────────────────── Sidebar ────────────────────────────

with st.sidebar:
    st.markdown('<div class="section-label">📁 Upload</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload PDF or Image",
        type=["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"],
        help="Supported: PDF, PNG, JPG, JPEG, WebP, BMP, TIFF",
    )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">🎨 Watermark Type</div>', unsafe_allow_html=True)
    wm_type = st.radio(
        "Choose watermark type",
        ["Text", "Image"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # --- Text watermark options ---
    if wm_type == "Text":
        st.markdown('<div class="section-label">✏️ Text Settings</div>', unsafe_allow_html=True)
        wm_text = st.text_input("Watermark Text", value="CONFIDENTIAL", max_chars=100)
        col_font, col_color = st.columns(2)
        with col_font:
            wm_font_size = st.slider("Font Size", 10, 200, 60, step=2)
        with col_color:
            wm_color = st.color_picker("Color", "#FFFFFF")

    # --- Image watermark options ---
    else:
        st.markdown('<div class="section-label">🖼️ Watermark Image</div>', unsafe_allow_html=True)
        wm_image_file = st.file_uploader(
            "Upload watermark image",
            type=["png", "jpg", "jpeg", "webp", "svg"],
            key="wm_upload",
            help="Use a PNG with transparency for best results",
        )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">📐 Dimensions & Position</div>', unsafe_allow_html=True)

    col_w, col_h = st.columns(2)
    with col_w:
        wm_width_pct = st.slider("Width %", 5, 100, 30, step=1, help="Watermark width as % of page")
    with col_h:
        wm_height_pct = st.slider("Height %", 5, 100, 15, step=1, help="Watermark height as % of page")

    col_x, col_y = st.columns(2)
    with col_x:
        x_position = st.slider("X Position", 0.0, 1.0, 0.5, step=0.01, help="0 = left edge, 1 = right edge")
    with col_y:
        y_position = st.slider("Y Position", 0.0, 1.0, 0.5, step=0.01, help="0 = top edge, 1 = bottom edge")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">⚙️ Effects</div>', unsafe_allow_html=True)

    opacity = st.slider("Opacity", 0.05, 1.0, 0.3, step=0.05)
    rotation = st.slider("Rotation°", 0, 360, 0, step=5)
    tile_mode = st.checkbox("🔲 Tile across page", value=False, help="Repeat watermark in a grid pattern")


# ──────────────────────── Helper Functions ───────────────────

def build_watermark_config(page_w: int, page_h: int) -> dict:
    """Build watermark config dict from sidebar values."""
    config = {
        "type": wm_type.lower(),
        "opacity": opacity,
        "rotation": rotation,
        "tile": tile_mode,
        "x_position": x_position,
        "y_position": y_position,
        "width": int(page_w * wm_width_pct / 100),
        "height": int(page_h * wm_height_pct / 100),
        # For PDF path
        "width_pct": wm_width_pct,
        "height_pct": wm_height_pct,
    }

    if wm_type == "Text":
        config["text"] = wm_text
        config["font_size"] = wm_font_size
        config["color"] = wm_color
    else:
        if wm_image_file is not None:
            config["watermark_image"] = Image.open(wm_image_file)
        else:
            config["watermark_image"] = None

    return config


def get_file_type(uploaded) -> str:
    """Determine if the uploaded file is a PDF or image."""
    name = uploaded.name.lower()
    if name.endswith(".pdf"):
        return "pdf"
    return "image"


# ──────────────────────── Main Content ───────────────────────

if uploaded_file is None:
    # Empty state
    st.markdown("""
    <div class="preview-card" style="text-align:center; padding:60px 20px;">
        <div style="font-size:4rem; margin-bottom:16px;">📄</div>
        <h3 style="color:#E2E8F0; margin-bottom:8px;">Upload a file to get started</h3>
        <p style="color:#64748B;">
            Drag and drop a PDF or image into the sidebar uploader.<br/>
            Adjust watermark settings and see a live preview here.
        </p>
    </div>
    """, unsafe_allow_html=True)

else:
    file_bytes = uploaded_file.getvalue()
    file_type = get_file_type(uploaded_file)

    # Validate image watermark is provided
    if wm_type == "Image":
        if "wm_image_file" not in dir() or wm_image_file is None:
            st.warning("⚠️ Please upload a watermark image in the sidebar.")
            st.stop()

    # ─────────── PDF Path ───────────
    if file_type == "pdf":
        total = pdf_page_count(file_bytes)
        st.markdown(f'<span class="badge">PDF • {total} page{"s" if total != 1 else ""}</span>', unsafe_allow_html=True)

        sample_indices = get_sample_page_indices(total)
        sample_images = preview_pdf_pages(file_bytes, sample_indices, dpi=150)

        if not sample_images:
            st.error("Could not render PDF pages.")
            st.stop()

        # Build config for preview (use first page dimensions)
        page_w, page_h = sample_images[0].size
        config = build_watermark_config(page_w, page_h)

        if config.get("type") == "image" and config.get("watermark_image") is None:
            st.warning("⚠️ Please upload a watermark image in the sidebar.")
            st.stop()

        # Preview section
        st.markdown("### 🔍 Live Preview")
        st.caption("Showing sample pages with watermark applied:")

        # Apply watermark to sample images
        preview_cols = st.columns(len(sample_images))
        for i, (col, img, idx) in enumerate(zip(preview_cols, sample_images, sample_indices)):
            with col:
                img_config = config.copy()
                img_config["width"] = int(img.width * wm_width_pct / 100)
                img_config["height"] = int(img.height * wm_height_pct / 100)
                watermarked = apply_watermark_to_image(img, img_config)
                st.image(watermarked.convert("RGB"), use_container_width=True)
                st.markdown(f'<p class="page-label">Page {idx + 1}</p>', unsafe_allow_html=True)

        # Generate & Download
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

        col_info, col_download = st.columns([2, 1])
        with col_info:
            st.markdown("### 📥 Generate Watermarked PDF")
            st.caption("Apply watermark to all pages and download the result.")

        with col_download:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Generate", use_container_width=True, type="primary"):
                with st.spinner("Applying watermark to all pages..."):
                    pdf_config = config.copy()
                    result_bytes = apply_watermark_to_pdf(file_bytes, pdf_config)

                st.session_state["result_pdf"] = result_bytes
                st.session_state["result_name"] = f"watermarked_{uploaded_file.name}"

        if "result_pdf" in st.session_state:
            st.download_button(
                label="⬇️ Download Watermarked PDF",
                data=st.session_state["result_pdf"],
                file_name=st.session_state["result_name"],
                mime="application/pdf",
                use_container_width=True,
            )

    # ─────────── Image Path ───────────
    else:
        source_img = Image.open(io.BytesIO(file_bytes))
        img_w, img_h = source_img.size
        st.markdown(
            f'<span class="badge">Image • {img_w}×{img_h}px</span>',
            unsafe_allow_html=True,
        )

        config = build_watermark_config(img_w, img_h)

        if config.get("type") == "image" and config.get("watermark_image") is None:
            st.warning("⚠️ Please upload a watermark image in the sidebar.")
            st.stop()

        # Preview
        st.markdown("### 🔍 Live Preview")

        watermarked = apply_watermark_to_image(source_img, config)

        col_orig, col_wm = st.columns(2)
        with col_orig:
            st.caption("Original")
            st.image(source_img, use_container_width=True)
        with col_wm:
            st.caption("With Watermark")
            st.image(watermarked.convert("RGB"), use_container_width=True)

        # Download
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown("### 📥 Download Watermarked Image")

        fmt = st.selectbox("Output Format", ["PNG", "JPEG", "WebP"], index=0)
        fmt_lower = fmt.lower()
        mime_map = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}

        buf = io.BytesIO()
        output_img = watermarked.convert("RGB") if fmt_lower == "jpeg" else watermarked
        output_img.save(buf, format=fmt)
        buf.seek(0)

        base_name = uploaded_file.name.rsplit(".", 1)[0]
        st.download_button(
            label=f"⬇️ Download as {fmt}",
            data=buf.getvalue(),
            file_name=f"watermarked_{base_name}.{fmt_lower}",
            mime=mime_map[fmt_lower],
            use_container_width=True,
        )


# ──────────────────────── Footer ─────────────────────────────

st.markdown("""
<div style="text-align:center; margin-top:60px; padding:20px; color:#475569; font-size:0.8rem;">
    Made with ❤️ using Streamlit • 
    <a href="https://github.com" target="_blank" style="color:#6C63FF; text-decoration:none;">View Source</a>
</div>
""", unsafe_allow_html=True)
