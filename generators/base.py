"""所有验证码生成器的基类"""
import os
import json
from abc import ABC, abstractmethod
from pathlib import Path
from PIL import ImageFont

_font_cache = {}

def load_font(size: int = 14) -> ImageFont.FreeTypeFont:
    """加载支持中文的字体，结果缓存"""
    if size in _font_cache:
        return _font_cache[size]
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                _font_cache[size] = font
                return font
            except Exception:
                continue
    font = ImageFont.load_default()
    _font_cache[size] = font
    return font


class BaseGenerator(ABC):
    """
    子类需实现 generate_one(idx) → dict
    返回的 dict 中必须包含 'answer' 字段。
    """

    name: str = "base"          # 每个子类覆盖

    def __init__(self, output_dir: str, count: int, **kwargs):
        self.count = count
        self.out = Path(output_dir) / self.name
        self._setup_dirs()
        self.kwargs = kwargs

    def _setup_dirs(self):
        self.out.mkdir(parents=True, exist_ok=True)

    def img_path(self, idx: int, suffix: str = "png") -> Path:
        return self.out / f"{idx:04d}.{suffix}"

    @abstractmethod
    def generate_one(self, idx: int) -> dict:
        """生成第 idx 张验证码，保存图片，返回标注 dict（含 answer）"""

    def run(self) -> list[dict]:
        labels = []
        for i in range(1, self.count + 1):
            info = self.generate_one(i)
            info["idx"] = f"{i:04d}"
            info["type"] = self.name
            labels.append(info)
            if i % max(1, self.count // 10) == 0 or i == self.count:
                print(f"  [{self.name}] {i}/{self.count}")

        # 保存标注
        json_path = self.out / "labels.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)

        return labels
