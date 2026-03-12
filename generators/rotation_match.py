"""Rotation_Match: 旋转图形至参考方向"""
import random
import math
from PIL import Image, ImageDraw
from .base import BaseGenerator, load_font
from generators import register

SHAPES = ["arrow", "airplane", "key", "wrench"]


def draw_arrow(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color):
    r = size // 2
    body_w = int(r * 0.3)
    pts_body = [
        (cx - r, cy - body_w),
        (cx + int(r * 0.3), cy - body_w),
        (cx + int(r * 0.3), cy - r + body_w),
        (cx + r, cy),
        (cx + int(r * 0.3), cy + r - body_w),
        (cx + int(r * 0.3), cy + body_w),
        (cx - r, cy + body_w),
    ]
    draw.polygon(pts_body, fill=color, outline=(30, 30, 30))


def draw_key(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color):
    r = size // 2
    kr = int(r * 0.4)
    draw.ellipse([cx - r, cy - kr, cx - r + kr * 2, cy + kr], fill=color, outline=(30, 30, 30), width=2)
    draw.rectangle([cx, cy - int(kr * 0.3), cx + r, cy + int(kr * 0.3)], fill=color)
    draw.rectangle([cx + int(r * 0.5), cy - int(kr * 0.5), cx + int(r * 0.65), cy + int(kr * 0.1)], fill=color)
    draw.rectangle([cx + int(r * 0.75), cy - int(kr * 0.5), cx + int(r * 0.9), cy + int(kr * 0.1)], fill=color)


def render_shape(shape: str, size: int, color, angle: int) -> Image.Image:
    """在透明画布上绘制图形，旋转 angle 度后返回"""
    canvas_size = int(size * 1.6)
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = canvas_size // 2
    half = size // 2

    if shape == "arrow":
        draw_arrow(draw, cx, cy, half, color)
    elif shape == "key":
        draw_key(draw, cx, cy, half, color)
    elif shape == "airplane":
        pts = [
            (cx + half, cy),
            (cx - int(half * 0.3), cy - int(half * 0.8)),
            (cx - int(half * 0.1), cy),
            (cx - int(half * 0.3), cy + int(half * 0.8)),
        ]
        draw.polygon(pts, fill=color, outline=(30, 30, 30))
        wing_l = [(cx - int(half * 0.6), cy - int(half * 0.1)), (cx, cy - int(half * 0.1)),
                  (cx, cy + int(half * 0.1)), (cx - int(half * 0.6), cy + int(half * 0.1))]
        draw.polygon(wing_l, fill=color)
    elif shape == "wrench":
        for ang in [0, 90]:
            rad = math.radians(ang)
            draw.rectangle([
                cx - int(half * 0.2), cy - int(half * 0.9),
                cx + int(half * 0.2), cy + int(half * 0.9)
            ], fill=color)
        draw.ellipse([cx - int(half * 0.5), cy - int(half * 0.8),
                      cx + int(half * 0.5), cy - int(half * 0.3)], fill=color, outline=(30, 30, 30))
        draw.ellipse([cx - int(half * 0.5), cy + int(half * 0.3),
                      cx + int(half * 0.5), cy + int(half * 0.8)], fill=color, outline=(30, 30, 30))

    return img.rotate(-angle, resample=Image.BICUBIC, expand=False)


@register("rotation_match")
class RotationMatchGenerator(BaseGenerator):
    name = "rotation_match"

    W, H = 400, 200
    OBJ_SIZE = 80
    ANGLE_STEP = 15  # 可选角度步长（度）

    def generate_one(self, idx: int) -> dict:
        w, h = self.W, self.H
        img = Image.new("RGB", (w, h), (238, 240, 248))
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, w, h], fill=(238, 240, 248))
        draw.text((10, 6), "旋转左侧图形使其与右侧参考方向一致", fill=(60, 60, 80), font=load_font(14))

        shape = random.choice(SHAPES)
        color = (random.randint(100, 220), random.randint(60, 180), random.randint(60, 200))

        reference_angle = random.choice(range(0, 360, self.ANGLE_STEP))
        current_angle = random.choice(range(0, 360, self.ANGLE_STEP))
        needed_rotation = (reference_angle - current_angle) % 360
        if needed_rotation > 180:
            needed_rotation -= 360

        obj_size = self.OBJ_SIZE
        # 左：当前角度（需要旋转）
        left_img = render_shape(shape, obj_size, color, current_angle)
        lx = w // 4 - left_img.width // 2
        ly = h // 2 - left_img.height // 2 + 15
        img.paste(left_img, (lx, ly), left_img)
        draw.text((w // 4 - 20, ly + left_img.height + 2), "← 旋转我", fill=(120, 120, 140), font=load_font(12))

        # 右：参考角度
        ref_img = render_shape(shape, obj_size, color, reference_angle)
        rx = 3 * w // 4 - ref_img.width // 2
        ry = h // 2 - ref_img.height // 2 + 15
        img.paste(ref_img, (rx, ry), ref_img)
        draw.text((3 * w // 4 - 20, ry + ref_img.height + 2), "← 参考", fill=(120, 120, 140), font=load_font(12))

        # 分隔线
        draw.line([(w // 2, 40), (w // 2, h - 20)], fill=(180, 185, 200), width=2)

        img.save(self.img_path(idx))
        return {
            "image": f"{idx:04d}.png",
            "shape": shape,
            "current_angle": current_angle,
            "reference_angle": reference_angle,
            "answer": needed_rotation,  # 需要顺时针旋转的度数
        }
