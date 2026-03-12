"""Slide_Puzzle: 滑动缺口验证码"""
import random
from PIL import Image, ImageDraw, ImageFilter
from .base import BaseGenerator
from generators import register


def _make_jigsaw_mask(w, h):
    scale = 4
    W, H = w * scale, h * scale
    r = int(min(W, H) * 0.2)
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle([r, r, W - r, H - r], fill=255)
    for side in ["top", "bottom", "left", "right"]:
        direction = random.choice([1, -1])
        cx, cy = W // 2, H // 2
        if side == "top":    cx_b, cy_b = cx, r
        elif side == "bottom": cx_b, cy_b = cx, H - r
        elif side == "left": cx_b, cy_b = r, cy
        else:                cx_b, cy_b = W - r, cy
        bbox = [cx_b - r, cy_b - r, cx_b + r, cy_b + r]
        draw.ellipse(bbox, fill=255 if direction == 1 else 0)
    return mask.resize((w, h), Image.LANCZOS)


def _gen_bg(w, h):
    img = Image.new("RGB", (w, h))
    pixels = img.load()
    c1 = tuple(random.randint(60, 200) for _ in range(3))
    c2 = tuple(random.randint(60, 200) for _ in range(3))
    for y in range(h):
        t = y / h
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        for x in range(w):
            pixels[x, y] = (r, g, b)
    draw = ImageDraw.Draw(img)
    for _ in range(random.randint(4, 12)):
        x0, y0 = random.randint(0, w), random.randint(0, h)
        x1 = x0 + random.randint(20, 80)
        y1 = y0 + random.randint(10, 50)
        color = tuple(random.randint(30, 220) for _ in range(3))
        if random.random() < 0.5:
            draw.rectangle([x0, y0, x1, y1], outline=color, width=2)
        else:
            draw.ellipse([x0, y0, x1, y1], outline=color, width=2)
    return img


@register("slide")
class SlideGenerator(BaseGenerator):
    name = "slide"

    BG_W, BG_H = 360, 160
    PW, PH = 50, 50

    def generate_one(self, idx: int) -> dict:
        w, h = self.BG_W, self.BG_H
        pw, ph = self.PW, self.PH

        bg_path = self.kwargs.get("bg_dir")
        if bg_path:
            import os
            files = [os.path.join(bg_path, f) for f in os.listdir(bg_path)
                     if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            if files:
                bg = Image.open(random.choice(files)).convert("RGB").resize((w, h))
            else:
                bg = _gen_bg(w, h)
        else:
            bg = _gen_bg(w, h)

        gap_x = random.randint(100, w - pw - 20)
        gap_y = random.randint(20, h - ph - 20)
        mask = _make_jigsaw_mask(pw, ph)

        region = bg.crop((gap_x, gap_y, gap_x + pw, gap_y + ph))
        slide = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        slide.paste(region, (0, 0), mask)

        bg_rgba = bg.convert("RGBA")
        # 缺口阴影：先画模糊扩散的暗影
        shadow = Image.new("RGBA", (pw + 8, ph + 8), (0, 0, 0, 0))
        shadow_mask_big = mask.resize((pw + 8, ph + 8), Image.LANCZOS)
        shadow.paste(Image.new("RGBA", (pw + 8, ph + 8), (0, 0, 0, 100)), (0, 0), shadow_mask_big)
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))
        bg_rgba.paste(shadow, (gap_x - 4, gap_y - 4), shadow)
        # 缺口填充（灰色半透明）
        hole = Image.new("RGBA", (pw, ph), (180, 180, 180, 120))
        bg_rgba.paste(hole, (gap_x, gap_y), mask)

        bg_path_out = self.out / "bg"
        slide_path_out = self.out / "slide"
        bg_path_out.mkdir(exist_ok=True)
        slide_path_out.mkdir(exist_ok=True)

        bg_rgba.convert("RGB").save(bg_path_out / f"{idx:04d}.png")
        slide.save(slide_path_out / f"{idx:04d}.png")

        return {
            "bg": f"bg/{idx:04d}.png",
            "slide": f"slide/{idx:04d}.png",
            "answer": gap_x,
            "gap_y": gap_y,
        }
