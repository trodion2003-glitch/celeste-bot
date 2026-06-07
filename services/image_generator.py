"""
services/image_generator.py — генерация красивых картинок для share
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
HEIGHT = 1920


def wrap_text(text: str, max_width: int = 50) -> list:
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split()
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line += (" " if current_line else "") + word
        if current_line:
            lines.append(current_line)
    return lines


def generate_forecast_image(name: str, forecast_text: str) -> BytesIO:
    try:
        img = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
        draw = ImageDraw.Draw(img)

        font = ImageFont.load_default()

        y_pos = 60

        draw.text((60, y_pos), "✦ CELESTÉ", fill=COLORS["accent"])
        y_pos += 50

        draw.text((60, y_pos), f"Прогноз для {name}", fill=COLORS["text"])
        y_pos += 50

        today = datetime.now().strftime("%d.%m.%Y")
        draw.text((60, y_pos), f"Дата: {today}", fill=COLORS["gold"])
        y_pos += 60

        draw.line([(60, y_pos), (WIDTH - 60, y_pos)], fill=COLORS["accent"], width=3)
        y_pos += 40

        lines = wrap_text(forecast_text, max_width=60)

        for line in lines:
            if y_pos > HEIGHT - 150:
                draw.text((60, y_pos), "...", fill=COLORS["text"])
                break
            draw.text((60, y_pos), line, fill=COLORS["text"])
            y_pos += 35

        y_pos = HEIGHT - 120
        draw.line([(60, y_pos), (WIDTH - 60, y_pos)], fill=COLORS["accent"], width=3)
        y_pos += 30
        draw.text((60, y_pos), "🌙 Celesté — Персональная астрология", fill=COLORS["gold"])
        y_pos += 35
        draw.text((60, y_pos), "t.me/CelesteAstroBot", fill=COLORS["text"])

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        logger.info(f"Forecast image generated for {name}")
        return buffer

    except Exception as e:
        logger.error(f"Error generating forecast image: {e}")
        raise


def generate_day_card_image(name: str, day_card_text: str) -> BytesIO:
    try:
        img = Image.new("RGB", (WIDTH, 1400), COLORS["bg"])
        draw = ImageDraw.Draw(img)

        font = ImageFont.load_default()

        y_pos = 60

        draw.text((60, y_pos), "☽ КАРТА ДНЯ", fill=COLORS["accent"])
        y_pos += 50

        draw.text((60, y_pos), f"Для {name}", fill=COLORS["text"])
        y_pos += 50

        today = datetime.now().strftime("%d.%m.%Y")
        draw.text((60, y_pos), f"Дата: {today}", fill=COLORS["gold"])
        y_pos += 60

        draw.line([(60, y_pos), (WIDTH - 60, y_pos)], fill=COLORS["accent"], width=3)
        y_pos += 40

        lines = wrap_text(day_card_text, max_width=60)

        for line in lines:
            if y_pos > 1400 - 150:
                draw.text((60, y_pos), "...", fill=COLORS["text"])
                break
            draw.text((60, y_pos), line, fill=COLORS["text"])
            y_pos += 35

        y_pos = 1400 - 120
        draw.line([(60, y_pos), (WIDTH - 60, y_pos)], fill=COLORS["accent"], width=3)
        y_pos += 30
        draw.text((60, y_pos), "🌙 Celesté — Персональная астрология", fill=COLORS["gold"])
        y_pos += 35
        draw.text((60, y_pos), "t.me/CelesteAstroBot", fill=COLORS["text"])

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        logger.info(f"Day card image generated for {name}")
        return buffer

    except Exception as e:
        logger.error(f"Error generating day card image: {e}")
        raise
