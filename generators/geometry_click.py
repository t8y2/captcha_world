"""Geometry_Click: 点击指定几何图形"""
import random
from PIL import Image, ImageDraw
from .base import BaseGenerator, load_font
from generators import register

SHAPES = ["circle", "triangle", "rectangle", "diamond", "star", "pentagon"]

PALETTE = [
    (220, 60, 60), (60, 140, 220), (50, 180, 80),
    (230, 160, 30), (140, 60, 200), (30, 180, 180),
]


def draw_shape(draw: ImageDraw.ImageDraw, shape: str, cx: int, cy: int,
               size: int, color, outline=(80, 80, 80)):
    r = size // 2
    if shape == "circle":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=outline, width=2)

    elif shape == "rectangle":
        rw = int(r * 1.4)
        rh = int(r * 0.85)
        draw.rectangle([cx - rw, cy - rh, cx + rw, cy + rh], fill=color, outline=outline, width=2)

    elif shape == "triangle":
        pts = [(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)]
        draw.polygon(pts, fill=color, outline=outline)

    elif shape == "diamond":
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        draw.polygon(pts, fill=color, outline=outline)

    elif shape == "pentagon":
        import math
        pts = [(cx + int(r * math.cos(math.radians(90 - 72 * i))),
                cy - int(r * math.sin(math.radians(90 - 72 * i)))) for i in range(5)]
        draw.polygon(pts, fill=color, outline=outline)

    elif shape == "star":
        import math
        pts = []
        outer, inner = r, r * 0.45
        for i in range(5):
            angle_o = math.radians(270 + 72 * i)
            angle_i = math.radians(270 + 72 * i + 36)
            pts.append((cx + outer * math.cos(angle_o), cy + outer * math.sin(angle_o)))
            pts.append((cx + inner * math.cos(angle_i), cy + inner * math.sin(angle_i)))
        draw.polygon(pts, fill=color, outline=outline)


@register("geometry_click")
class GeometryClickGenerator(BaseGenerator):
    name = "geometry_click"

    W, H = 400, 200
    SHAPE_SIZE = 56
    NUM_SHAPES = (4, 7)

    def generate_one(self, idx: int) -> dict:
        w, h = self.W, self.H
        img = Image.new("RGB", (w, h), (240, 242, 248))
        draw = ImageDraw.Draw(img)

        # 轻微网格背景
        for gx in range(0, w, 30):
            draw.line([(gx, 0), (gx, h)], fill=(230, 232, 240), width=1)
        for gy in range(0, h, 30):
            draw.line([(0, gy), (w, gy)], fill=(230, 232, 240), width=1)

        n = random.randint(*self.NUM_SHAPES)
        size = self.SHAPE_SIZE
        padding = size + 10

        shapes_used = random.choices(SHAPES, k=n)
        target_shape = random.choice(shapes_used)

        # 随机不重叠布局
        positions = []
        for _ in range(n):
            for _ in range(50):
                cx = random.randint(size, w - size)
                cy = random.randint(size + 30, h - size)
                if all(abs(cx - px) > padding or abs(cy - py) > padding for px, py in positions):
                    positions.append((cx, cy))
                    break
            else:
                positions.append((random.randint(size, w - size), random.randint(size + 30, h - size)))

        click_positions = []
        for (cx, cy), shape in zip(positions, shapes_used):
            color = random.choice(PALETTE)
            draw_shape(draw, shape, cx, cy, size // 2, color)
            if shape == target_shape:
                click_positions.append({"x": cx, "y": cy})

        draw.text((10, 6), f"请点击所有「{target_shape}」", fill=(60, 60, 80), font=load_font(14))

        img.save(self.img_path(idx))
        return {
            "image": f"{idx:04d}.png",
            "target_shape": target_shape,
            "answer": click_positions,  # 所有目标图形的坐标
        }
