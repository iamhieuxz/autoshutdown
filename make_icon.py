"""Generate a multi-resolution .ico file for the Auto Shutdown application."""

import os
import sys

from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]


def render_icon(size: int) -> Image.Image:
    scale = 4
    canvas_size = size * scale
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = canvas_size * 0.06
    box = (margin, margin, canvas_size - margin, canvas_size - margin)

    # Rounded square with vertical gradient
    gradient = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    top = (76, 201, 240)
    bottom = (27, 140, 179)
    for y in range(canvas_size):
        ratio = y / max(1, canvas_size - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        grad_draw.line([(0, y), (canvas_size, y)], fill=color + (255,))

    mask = Image.new("L", (canvas_size, canvas_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        box, radius=canvas_size * 0.26, fill=255
    )
    image.paste(gradient, (0, 0), mask)

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        box, radius=canvas_size * 0.26, outline=(127, 223, 247, 255),
        width=max(1, int(canvas_size * 0.025)),
    )

    # Power symbol
    stroke = max(2, int(canvas_size * 0.075))
    cx = canvas_size / 2
    arc_box = (cx - canvas_size * 0.19, cx - canvas_size * 0.19,
               cx + canvas_size * 0.19, cx + canvas_size * 0.19)
    draw.arc(arc_box, start=55, end=345, fill=(4, 32, 47, 255), width=stroke)
    draw.line(
        [(cx, canvas_size * 0.24), (cx, canvas_size * 0.44)],
        fill=(4, 32, 47, 255),
        width=stroke,
    )

    return image.resize((size, size), Image.LANCZOS)


def main():
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    images = [render_icon(size) for size in SIZES]
    images[-1].save(output, format="ICO", sizes=[(s, s) for s in SIZES])

    print(f"icon.ico created ({os.path.getsize(output)} bytes)")


if __name__ == "__main__":
    main()
