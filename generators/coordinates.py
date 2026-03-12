"""Coordinates: 将图标拖动到指定坐标"""
import random
from PIL import Image, ImageDraw
from .base import BaseGenerator, load_font
from generators import register


@register("coordinates")
class CoordinatesGenerator(BaseGenerator):
    name = "coordinates"

    W, H = 400, 260
    GRID_PADDING = 40
    CELL = 40  # 网格格子大小
    ICON_SIZE = 20

    def generate_one(self, idx: int) -> dict:
        w, h = self.W, self.H
        img = Image.new("RGB", (w, h), (240, 242, 250))
        draw = ImageDraw.Draw(img)

        pad = self.GRID_PADDING
        cell = self.CELL
        cols = (w - 2 * pad) // cell
        rows = (h - 2 * pad - 30) // cell

        origin_x = pad
        origin_y = h - pad

        # 画网格
        for gx in range(cols + 1):
            x = origin_x + gx * cell
            draw.line([(x, origin_y - rows * cell), (x, origin_y)], fill=(200, 205, 215), width=1)
            draw.text((x - 6, origin_y + 4), str(gx), fill=(80, 80, 100))

        for gy in range(rows + 1):
            y = origin_y - gy * cell
            draw.line([(origin_x, y), (origin_x + cols * cell, y)], fill=(200, 205, 215), width=1)
            draw.text((origin_x - 20, y - 8), str(gy), fill=(80, 80, 100))

        # 坐标轴标签
        draw.text((origin_x + cols * cell // 2, origin_y + 16), "X", fill=(60, 80, 120))
        draw.text((origin_x - 32, origin_y - rows * cell // 2), "Y", fill=(60, 80, 120))

        # 随机目标坐标
        target_x_grid = random.randint(1, cols)
        target_y_grid = random.randint(1, rows)
        target_px = origin_x + target_x_grid * cell
        target_py = origin_y - target_y_grid * cell

        # 画目标位置（空心十字+圆）
        draw.ellipse([target_px - 8, target_py - 8, target_px + 8, target_py + 8],
                     outline=(220, 60, 60), width=3)
        draw.line([(target_px - 12, target_py), (target_px + 12, target_py)], fill=(220, 60, 60), width=2)
        draw.line([(target_px, target_py - 12), (target_px, target_py + 12)], fill=(220, 60, 60), width=2)

        # 画当前图标位置（随机，不与目标重合）
        cur_x_grid = random.choice([x for x in range(0, cols) if x != target_x_grid])
        cur_y_grid = random.choice([y for y in range(0, rows) if y != target_y_grid])
        cur_px = origin_x + cur_x_grid * cell
        cur_py = origin_y - cur_y_grid * cell

        ir = self.ICON_SIZE // 2
        draw.ellipse([cur_px - ir, cur_py - ir, cur_px + ir, cur_py + ir],
                     fill=(60, 120, 220), outline=(30, 80, 180), width=2)

        draw.text((10, 6),
                  f"请将蓝色图标拖动到坐标 ({target_x_grid}, {target_y_grid})",
                  fill=(60, 60, 80), font=load_font(14))

        img.save(self.img_path(idx))
        return {
            "image": f"{idx:04d}.png",
            "icon_pos": {"x": cur_x_grid, "y": cur_y_grid},
            "answer": {"x": target_x_grid, "y": target_y_grid},
        }
