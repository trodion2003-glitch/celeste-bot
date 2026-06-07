"""
services/image_generator.py — генерация красивых картинок для share
"""

import logging
import re
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
HEIGHT = 1920
PADDING = 60

# Пути к шрифтам (пробуем по очереди)
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    "/System/Library/Fonts/Helvetica.ttc",  # macOS fallback
    "/System/Library/Fonts/Arial.ttf",
]

_FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _try_load(paths: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    # Pillow 10+ supports size parameter on load_default
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _get_fonts():
    title  = _try_load(_FONT_BOLD_CANDIDATES, 72)
    header = _try_load(_FONT_CANDIDATES, 44)
    body   = _try_load(_FONT_CANDIDATES, 36)
    small  = _try_load(_FONT_CANDIDATES, 28)
    return title, header, body, small


def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*',     r'\1', text, flags=re.DOTALL)
    text = re.sub(r'__(.+?)__',     r'\1', text, flags=re.DOTALL)
    text = re.sub(r'_(.+?)_',       r'\1', text, flags=re.DOTALL)
    text = re.sub(r'^#+\s*',        '',    text, flags=re.MULTILINE)
    return text


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width_px: int) -> list[str]:
    """Перенос строк по пикселям (точный)."""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        words = paragraph.split()
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            try:
                w = font.getlength(test)
            except AttributeError:
                w = len(test) * 20  # грубая оценка для fallback шрифта
            if w > max_width_px and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def _draw_image(title_text: str, subtitle: str, body_text: str, height: int) -> BytesIO:
    img = Image.new("RGB", (WIDTH, height), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    font_title, font_header, font_body, font_small = _get_fonts()

    body_text = strip_markdown(body_text)
    max_text_width = WIDTH - PADDING * 2
    y = PADDING

    # Заголовок (логотип)
    draw.text((PADDING, y), title_text, font=font_title, fill=COLORS["accent"])
    y += 90

    # Подзаголовок
    draw.text((PADDING, y), subtitle, font=font_header, fill=COLORS["text"])
    y += 60

    # Дата
    today = datetime.now().strftime("%d.%m.%Y")
    draw.text((PADDING, y), today, font=font_small, fill=COLORS["gold"])
    y += 50

    # Разделитель
    draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill=COLORS["accent"], width=3)
    y += 40

    # Тело
    lines = wrap_text(body_text, font_body, max_text_width)
    for line in lines:
        if y > height - 160:
            draw.text((PADDING, y), "...", font=font_body, fill=COLORS["text"])
            break
        draw.text((PADDING, y), line, font=font_body, fill=COLORS["text"])
        y += 48

    # Подвал
    footer_y = height - 130
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=COLORS["accent"], width=3)
    draw.text((PADDING, footer_y + 20), "🌙 Celesté — Персональная астрология", font=font_small, fill=COLORS["gold"])
    draw.text((PADDING, footer_y + 58), "t.me/CelesteAstroBot", font=font_small, fill=COLORS["text"])

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_forecast_image(name: str, forecast_text: str) -> BytesIO:
    buf = _draw_image(
        title_text="✦ CELESTÉ",
        subtitle=f"Прогноз для {name}",
        body_text=forecast_text,
        height=HEIGHT,
    )
    logger.info(f"Forecast image generated for {name}")
    return buf


def generate_day_card_image(name: str, day_card_text: str) -> BytesIO:
    buf = _draw_image(
        title_text="☽ КАРТА ДНЯ",
        subtitle=f"Для {name}",
        body_text=day_card_text,
        height=1400,
    )
    logger.info(f"Day card image generated for {name}")
    return buf
