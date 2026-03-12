"""Click_Order: 按顺序点击数字/字母"""
import random
from PIL import Image, ImageDraw
from .base import BaseGenerator, load_font
from generators import register

PALETTES = [
    (220, 60, 60),
    (60, 140, 220),
    (50, 180, 80),
    (220, 160, 30),
    (140, 60, 200),
    (30, 180, 180),
    (220, 100, 50),
]


@register("click_order")
class ClickOrderGenerator(BaseGenerator):
    name = "click_order"

    W, H = 400, 240
    NUM_ITEMS = (4, 8)
    ITEM_RADIUS = 24

    def generate_one(self, idx: int) -> dict:
        w, h = self.W, self.H
        img = Image.new("RGB", (w, h), (238, 240, 248))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h], fill=(238, 240, 248))

        n = random.randint(*self.NUM_ITEMS)
        # 是否按数字还是字母
        use_letters = random.random() < 0.4
        if use_letters:
            labels = random.sample("ABCDEFGHJKLMNPQRSTUVWXYZ", n)
            order_labels = labels[:]  # 点击顺序 = 字母顺序
            order_labels.sort()
        else:
            labels = random.sample(range(1, 20), n)
            labels = [str(v) for v in labels]
            order_labels = sorted(labels, key=lambda x: int(x))

        r = self.ITEM_RADIUS
        padding = r + 10

        positions = []
        for _ in range(n):
            for _ in range(60):
                cx = random.randint(padding, w - padding)
                cy = random.randint(padding + 30, h - padding)
                if all(abs(cx - px) > r * 2 + 8 or abs(cy - py) > r * 2 + 8 for px, py in positions):
                    positions.append((cx, cy))
                    break
            else:
                positions.append((random.randint(padding, w - padding),
                                   random.randint(padding + 30, h - padding)))

        if use_letters:
            draw.text((10, 6), f"请按字母顺序点击：{' → '.join(order_labels)}", fill=(60, 60, 80), font=load_font(14))
        else:
            draw.text((10, 6), f"请按从小到大的顺序点击数字", fill=(60, 60, 80), font=load_font(14))

        items = list(zip(labels, positions))

        for label, (cx, cy) in items:
            color = random.choice(PALETTES)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                          fill=color, outline=(min(255, color[0] + 30), min(255, color[1] + 30), 255), width=2)
            draw.text((cx, cy), str(label), fill=(255, 255, 255), font=load_font(20), anchor="mm")

        img.save(self.img_path(idx))
        click_sequence = [{"label": lbl, "x": cx, "y": cy}
                          for lbl in order_labels
                          for (l, (cx, cy)) in items if l == lbl]
        return {
            "image": f"{idx:04d}.png",
            "mode": "letter" if use_letters else "number",
            "items": [{"label": lbl, "x": cx, "y": cy} for lbl, (cx, cy) in items],
            "answer": click_sequence,
        }
