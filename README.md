# 💧 Watermark Studio

A Streamlit application for adding professional watermarks to PDFs and images.

## Features

- **PDF & Image Support** — Upload PDFs, PNG, JPG, JPEG, WebP, BMP, or TIFF files
- **Text Watermarks** — Custom text with configurable font size and color
- **Image Watermarks** — Upload any logo or image as a watermark (PNG with transparency recommended)
- **Live Preview** — See how your watermark looks on sample pages before generating the final file
- **Full Control** — Adjust dimensions, position, opacity, rotation, and tiling
- **Download** — Generate and download the watermarked file in your preferred format

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Deploy to Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set the main file path to `app.py`
5. Click **Deploy**

## Dependencies

- `streamlit` — Web UI framework
- `Pillow` — Image processing
- `PyMuPDF` — PDF reading and writing
- `reportlab` — PDF overlay generation

## License

MIT
