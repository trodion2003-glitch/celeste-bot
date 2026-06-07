"""
services/image_generator.py — генерация картинок для share
"""

import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

logger = logging.getLogger(__name__)

COLORS = {
    "bg":     (25, 25, 35),
    "text":   (255, 255, 255),
    "accent": (107, 70, 193),
    "gold":   (212, 175, 55),
}

WIDTH = 1080
PADDING = 60
LINE_HEIGHT = 52

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
_FONT_PATHS_REG = [p.replace("Bold", "").replace("-Bold", "") for p in _FONT_PATHS]


def _load_fonts(size_title=56, size_body=36, size_small=28):
    for path in _FONT_PATHS:
        try:
            return (
                ImageFont.truetype(path, size_title),
                ImageFont.truetype(path.replace("Bold", "").replace("-Bold", "") or path, size_body),
                ImageFont.truetype(path.replace("Bold", "").replace("-Bold", "") or path, size_small),
            )
        except OSError:
            continue
    default = ImageFont.load_default()
    return default, default, default


def _wrap_text(line: str, max_chars: int = 48) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    words = line.split()
    rows, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars:
            if current:
                rows.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        rows.append(current)
    return rows or [line]


def _draw_card(draw, title: str, subtitle: str, body_text: str,
               title_font, body_font, small_font, height: int) -> None:
    y = PADDING

    draw.text((PADDING, y), title, font=title_font, fill=COLORS["accent"])
    y += LINE_HEIGHT + 10

    draw.text((PADDING, y), subtitle, font=body_font, fill=COLORS["text"])
    y += LINE_HEIGHT

    today = datetime.now().strftime("%d.%m.%Y")
    draw.text((PADDING, y), today, font=small_font, fill=COLORS["gold"])
    y += LINE_HEIGHT + 20

    draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill=COLORS["accent"], width=2)
    y += 30

    for raw_line in body_text.split("\n"):
        for wrapped in _wrap_text(raw_line):
            if y > height - PADDING - 120:
                break
            draw.text((PADDING, y), wrapped, font=body_font, fill=COLORS["text"])
            y += LINE_HEIGHT

    footer_y = height - PADDING - 80
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=COLORS["accent"], width=2)
    draw.text((PADDING, footer_y + 20), "🌙 Celesté — Персональная астрология", font=small_font, fill=COLORS["gold"])
    draw.text((PADDING, footer_y + 52), "t.me/CelesteAstroBot", font=small_font, fill=COLORS["text"])


def generate_forecast_image(name: str, forecast_text: str) -> BytesIO:
    height = 1920
    img = Image.new("RGB", (WIDTH, height), COLORS["bg"])
    draw = ImageDraw.Draw(img)
    title_font, body_font, small_font = _load_fonts()

    _draw_card(draw, "✦ Celesté", f"Прогноз для {name}", forecast_text,
               title_font, body_font, small_font, height)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    logger.info(f"Forecast image generated for {name}")
    return buf


def generate_day_card_image(name: str, day_card_text: str) -> BytesIO:
    height = 1400
    img = Image.new("RGB", (WIDTH, height), COLORS["bg"])
    draw = ImageDraw.Draw(img)
    title_font, body_font, small_font = _load_fonts()

    _draw_card(draw, "☽ Карта дня", f"Для {name}", day_card_text,
               title_font, body_font, small_font, height)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    logger.info(f"Day card image generated for {name}")
    return buf
