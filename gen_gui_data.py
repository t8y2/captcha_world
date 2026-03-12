"""
gen_gui_data.py
==============
为每个验证码类型生成 GUI 交互轨迹数据：
  截图(before) → 动作 → 截图(after) → ...

输出格式
--------
output/gui_data/{type}/{idx:04d}/
    t00.png       初始截图
    t01.png       执行第一个动作后截图
    ...
    final.png     最终状态
gui_data/{type}/labels.jsonl
    每行一个样本的完整轨迹 JSON

轨迹 JSON 格式
--------------
{
  "id": "geometry_click/0001",
  "type": "geometry_click",
  "task": "请点击图中所有 pentagon",
  "width": 400,
  "height": 200,
  "steps": [
    {"t": 0, "screenshot": "t00.png", "action": {"type":"click","x":185,"y":112}},
    {"t": 1, "screenshot": "t01.png", "action": {"type":"click","x":96,"y":126}},
    {"t": 2, "screenshot": "t02.png", "action": null}   // final, no more action
  ],
  "answer": [...]
}
"""
import argparse
import json
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = Path(__file__).parent
OUT  = BASE / "output"
GUI  = BASE / "gui_data"
BG_DIR = BASE / "images" / "backgrounds"

# 外部背景图路径（可通过命令行参数指定）
BACKGROUND_IMG_DIRS = None
# 背景图模糊半径（可通过命令行参数指定，0表示不模糊）
BLUR_RADIUS = 1.0
# 背景图模糊概率（0.5 表示 50% 概率模糊）
BLUR_PROB = 0.5

# ── helper ──────────────────────────────────────────────
def load_font(size=12):
    for name in ["/System/Library/Fonts/PingFang.ttc",
                 "/System/Library/Fonts/STHeiti Medium.ttc",
                 "/System/Library/Fonts/STHeiti Light.ttc",
                 "/System/Library/Fonts/Hiragino Sans GB.ttc",
                 "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(name):
            try: return ImageFont.truetype(name, size)
            except: pass
    return ImageFont.load_default()

FONT_SM = None   # loaded lazily

def draw_dot(draw, x, y, label, color=(70, 140, 255)):
    r = 13
    draw.ellipse([x-r, y-r, x+r, y+r], fill=(*color, 200), outline=(255,255,255), width=2)
    global FONT_SM
    if FONT_SM is None:
        FONT_SM = load_font(11)
    draw.text((x, y), str(label), font=FONT_SM, fill=(255,255,255,255),
              anchor="mm" if hasattr(FONT_SM, "getbbox") else None)

def draw_ring(draw, x, y, color=(30, 190, 100)):
    r = 19
    draw.ellipse([x-r, y-r, x+r, y+r], outline=(*color, 220), width=2)

def load_img(path) -> Image.Image:
    return Image.open(path).convert("RGBA")

# ── Widget 框架渲染 ─────────────────────────────────────
WIDGET_W = 390
HEADER_H = 36
FOOTER_H = 80
SLIDER_H = 44

_font_cache_gui = {}
def _font(size):
    if size not in _font_cache_gui:
        _font_cache_gui[size] = load_font(size)
    return _font_cache_gui[size]

def _rounded_rect(draw, bbox, radius, fill, outline=None):
    """画圆角矩形"""
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline)

def render_widget(captcha_img: Image.Image, title: str, instruction: str = "",
                  controls: str = "buttons", slider_pos: float = 0.0) -> Image.Image:
    """
    将验证码图片包裹进 widget 对话框。
    controls: "buttons" | "slider" | "rotation"
    slider_pos: 0.0~1.0 滑块位置
    返回完整 widget 截图 (RGB)。
    """
    cw, ch = captcha_img.size
    # 缩放验证码到 widget 宽度
    scale = WIDGET_W / cw
    scaled_h = int(ch * scale)
    captcha_resized = captcha_img.resize((WIDGET_W, scaled_h), Image.LANCZOS)

    instr_pad = 26 if instruction else 10
    if controls == "slider":
        ctrl_h = instr_pad + SLIDER_H + 8 + 28 + 8
    elif controls == "rotation":
        ctrl_h = instr_pad + 2 + 28 + 28 + 8
    else:
        ctrl_h = instr_pad + 4 + 28 + 8

    total_h = HEADER_H + scaled_h + ctrl_h
    widget = Image.new("RGBA", (WIDGET_W, total_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(widget, "RGBA")

    y = 0

    # ── Header ──
    draw.rectangle([0, y, WIDGET_W, y + HEADER_H], fill=(245, 247, 252))
    draw.line([(0, y + HEADER_H - 1), (WIDGET_W, y + HEADER_H - 1)], fill=(232, 236, 245))
    title_font = _font(12)
    draw.text((WIDGET_W // 2, y + HEADER_H // 2), title,
              fill=(68, 68, 68), font=title_font, anchor="mm")
    # 关闭按钮 (×)
    bx, by = WIDGET_W - 20, y + HEADER_H // 2
    draw.line([(bx-4, by-4), (bx+4, by+4)], fill=(187, 187, 187), width=2)
    draw.line([(bx+4, by-4), (bx-4, by+4)], fill=(187, 187, 187), width=2)
    # 刷新按钮（圆弧+箭头）
    rx, ry = WIDGET_W - 46, y + HEADER_H // 2
    rr = 5
    draw.arc([rx-rr, ry-rr, rx+rr, ry+rr], start=30, end=330, fill=(187, 187, 187), width=2)
    draw.polygon([(rx+rr-1, ry-rr+1), (rx+rr+3, ry-rr+3), (rx+rr-1, ry-rr+5)], fill=(187, 187, 187))
    y += HEADER_H

    # ── Captcha body ──
    widget.paste(captcha_resized.convert("RGBA"), (0, y))
    y += scaled_h

    # ── Footer / Controls ──
    draw.rectangle([0, y, WIDGET_W, y + ctrl_h], fill=(245, 247, 252))
    draw.line([(0, y), (WIDGET_W, y)], fill=(232, 236, 245))

    if instruction:
        instr_font = _font(11)
        draw.text((14, y + 8), instruction, fill=(119, 119, 119), font=instr_font)
        ctrl_y = y + 26
    else:
        ctrl_y = y + 10

    if controls == "slider":
        # 滑块轨道
        track_x, track_w = 14, WIDGET_W - 28
        track_y = ctrl_y
        _rounded_rect(draw, [track_x, track_y, track_x + track_w, track_y + SLIDER_H],
                      8, fill=(227, 232, 243))
        # 填充
        fill_w = max(22, int(slider_pos * track_w))
        _rounded_rect(draw, [track_x, track_y, track_x + fill_w, track_y + SLIDER_H],
                      8, fill=(200, 220, 248))
        # 滑块
        thumb_x = track_x + int(slider_pos * (track_w - 36)) + 4
        thumb_y = track_y + 4
        _rounded_rect(draw, [thumb_x, thumb_y, thumb_x + 36, thumb_y + 36],
                      7, fill=(255, 255, 255), outline=(220, 220, 230))
        # 右箭头
        ax, ay = thumb_x + 18, thumb_y + 18
        draw.line([(ax-6, ay), (ax+6, ay)], fill=(21, 101, 192), width=2)
        draw.polygon([(ax+3, ay-4), (ax+8, ay), (ax+3, ay+4)], fill=(21, 101, 192))
        # 提示文字
        if slider_pos < 0.05:
            hint_font = _font(11)
            draw.text((track_x + track_w // 2, track_y + SLIDER_H // 2),
                      "向右拖动完成验证", fill=(170, 170, 187), font=hint_font, anchor="mm")
        # 按钮行
        btn_y = track_y + SLIDER_H + 8
        _draw_buttons(draw, btn_y)
    elif controls == "rotation":
        # 旋转滑条
        row_y = ctrl_y + 2
        label_font = _font(11)
        draw.text((14, row_y + 4), "旋转:", fill=(136, 136, 136), font=label_font)
        # 滑条轨道
        bar_x, bar_w = 56, WIDGET_W - 120
        bar_y = row_y + 8
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 4], fill=(210, 215, 228))
        # 滑块位置
        knob_x = bar_x + int(slider_pos * bar_w)
        draw.ellipse([knob_x - 7, bar_y - 5, knob_x + 7, bar_y + 9], fill=(21, 101, 192))
        # 角度显示
        deg_font = _font(12)
        draw.text((WIDGET_W - 40, row_y + 2), f"{int((slider_pos - 0.5) * 360)}°",
                  fill=(21, 101, 192), font=deg_font)
        btn_y = row_y + 28
        _draw_buttons(draw, btn_y)
    else:
        # 纯按钮
        _draw_buttons(draw, ctrl_y + 4)

    y += ctrl_h

    return widget.convert("RGBA")


def _draw_buttons(draw, y):
    """画刷新+确认按钮行"""
    # 刷新按钮
    _rounded_rect(draw, [14, y, 50, y + 28], 6, fill=(235, 238, 245))
    # 刷新图标（圆弧+箭头）
    cx, cy = 32, y + 14
    rr = 6
    draw.arc([cx-rr, cy-rr, cx+rr, cy+rr], start=30, end=330, fill=(119, 119, 119), width=2)
    draw.polygon([(cx+rr-1, cy-rr+1), (cx+rr+3, cy-rr+4), (cx+rr-1, cy-rr+7)], fill=(119, 119, 119))
    # 确认按钮
    _rounded_rect(draw, [58, y, WIDGET_W - 14, y + 28], 6, fill=(21, 101, 192))
    confirm_font = _font(12)
    draw.text(((58 + WIDGET_W - 14) // 2, y + 14), "确认",
              fill=(255, 255, 255), font=confirm_font, anchor="mm")

def save(img: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(str(path))

def overlay(base: Image.Image, marks: Image.Image) -> Image.Image:
    out = base.convert("RGBA").copy()
    out.paste(marks, (0, 0), marks)
    return out

def blank_marks(img: Image.Image) -> Image.Image:
    return Image.new("RGBA", img.size, (0, 0, 0, 0))

def to_permille(record, captcha_w, captcha_h):
    """将记录中的像素坐标转换为千分比 [0, 999]，基于 widget 图片尺寸。"""
    w, h = record["width"], record["height"]
    scale = WIDGET_W / captcha_w

    def px(x, y):
        """captcha 像素 → widget 像素 → 千分比"""
        wx = x * scale
        wy = y * scale + HEADER_H
        return (min(999, round(wx / w * 999)), min(999, round(wy / h * 999)))

    def wpx(x, y):
        """widget 像素 → 千分比（已在 widget 坐标系）"""
        return (min(999, round(x / w * 999)), min(999, round(y / h * 999)))

    def px_x(x):
        return min(999, round(x * scale / w * 999))

    for step in record["steps"]:
        a = step.get("action")
        if not a:
            continue
        conv = wpx if a.pop("_widget", False) else px
        if a["type"] == "left_click" and "start_box" in a:
            a["start_box"] = list(conv(a["start_box"][0], a["start_box"][1]))
        elif a["type"] == "left_drag" and "start_box" in a:
            a["start_box"] = list(conv(a["start_box"][0], a["start_box"][1]))
            a["end_box"]   = list(conv(a["end_box"][0], a["end_box"][1]))

    ans = record["answer"]
    if isinstance(ans, list) and ans and isinstance(ans[0], dict) and "x" in ans[0]:
        for pt in ans:
            if isinstance(pt.get("y"), int) and pt["y"] > 10:
                pt["x"], pt["y"] = px(pt["x"], pt["y"])
    elif isinstance(ans, int) and record["type"] == "slide":
        record["answer"] = px_x(ans)

    return record

# ── 网页截图合成增强 ──────────────────────────────────────

AUGMENT_W, AUGMENT_H = 1280, 800  # 合成画布尺寸
AUGMENT_SCALE = 1.15              # widget 放大倍数（约占画面 35%）

def _load_webpage_bg() -> Image.Image:
    """加载一张随机背景图作为网页底图，拉伸到画布尺寸并模糊处理。"""
    import glob as glob_module
    
    bgs = []
    # 优先使用外部指定的背景图路径
    if BACKGROUND_IMG_DIRS:
        for img_dir in BACKGROUND_IMG_DIRS:
            bgs += glob_module.glob(os.path.join(img_dir, '*.png'))
            bgs += glob_module.glob(os.path.join(img_dir, '*.jpg'))
            bgs += glob_module.glob(os.path.join(img_dir, '*.jpeg'))
    
    # 如果外部路径没有图片，则使用本地背景
    if not bgs:
        bgs = list(BG_DIR.glob("*.jpg")) + list(BG_DIR.glob("*.png"))
    
    if bgs:
        bg = Image.open(random.choice(bgs)).convert("RGB")
        bg = bg.resize((AUGMENT_W, AUGMENT_H), Image.LANCZOS)
        # 按概率应用模糊（如果 BLUR_RADIUS > 0）
        if BLUR_RADIUS > 0 and random.random() < BLUR_PROB:
            bg = bg.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))
    else:
        bg = Image.new("RGB", (AUGMENT_W, AUGMENT_H), (245, 245, 250))
    return bg


def augment_screenshot(widget_img: Image.Image) -> tuple[Image.Image, int, int]:
    """
    将 widget 截图放大后合成到模拟网页截图上。
    返回 (合成图, widget 左上角 x 偏移, widget 左上角 y 偏移)。
    """
    ww, wh = widget_img.size
    sw, sh = int(ww * AUGMENT_SCALE), int(wh * AUGMENT_SCALE)
    widget_up = widget_img.resize((sw, sh), Image.LANCZOS)

    canvas = _load_webpage_bg()

    # 半透明深色遮罩模拟模态弹窗
    overlay_mask = Image.new("RGBA", (AUGMENT_W, AUGMENT_H), (0, 0, 0, 120))
    canvas = canvas.convert("RGBA")
    canvas = Image.alpha_composite(canvas, overlay_mask)

    # 完全随机位置（在不超出屏幕范围内）
    cx = random.randint(0, max(0, AUGMENT_W - sw))
    cy = random.randint(0, max(0, AUGMENT_H - sh))

    # 给 widget 加投影
    shadow = Image.new("RGBA", (sw + 16, sh + 16), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle([0, 0, sw + 15, sh + 15], radius=12, fill=(0, 0, 0, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
    canvas.paste(shadow, (cx - 4, cy + 2), shadow)

    canvas.paste(widget_up.convert("RGBA"), (cx, cy), widget_up.convert("RGBA"))
    return canvas.convert("RGB"), cx, cy


def apply_augment(record: dict, type_dir: Path) -> dict:
    """
    对 record 中每张截图做网页合成增强，更新坐标为增强后画布的千分比。
    """
    sample_dir = type_dir / record["id"].split("/")[-1]

    # 先确定一组固定偏移（同一 sample 所有步骤使用相同偏移）
    first_shot = Image.open(sample_dir / record["steps"][0]["screenshot"])
    _, offset_x, offset_y = augment_screenshot(first_shot)

    # 加载一张固定背景（同一 sample 各步骤保持一致）
    bg_base = _load_webpage_bg()

    for step in record["steps"]:
        shot_path = sample_dir / step["screenshot"]
        widget_img = Image.open(shot_path)
        ww, wh = widget_img.size
        sw, sh = int(ww * AUGMENT_SCALE), int(wh * AUGMENT_SCALE)
        widget_up = widget_img.resize((sw, sh), Image.LANCZOS)

        canvas = bg_base.copy().convert("RGBA")
        overlay_mask = Image.new("RGBA", (AUGMENT_W, AUGMENT_H), (0, 0, 0, 120))
        canvas = Image.alpha_composite(canvas, overlay_mask)
        shadow = Image.new("RGBA", (sw + 16, sh + 16), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle([0, 0, sw + 15, sh + 15], radius=12, fill=(0, 0, 0, 60))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
        canvas.paste(shadow, (offset_x - 4, offset_y + 2), shadow)
        canvas.paste(widget_up.convert("RGBA"), (offset_x, offset_y), widget_up.convert("RGBA"))
        canvas.convert("RGB").save(str(shot_path))

        # 重新计算动作坐标（从 widget 千分比 → 放大后画布千分比）
        a = step.get("action")
        if a and "start_box" in a:
            old_w, old_h = record["width"], record["height"]
            a["start_box"] = _remap_coord(a["start_box"], old_w, old_h, offset_x, offset_y)
            if "end_box" in a:
                a["end_box"] = _remap_coord(a["end_box"], old_w, old_h, offset_x, offset_y)

    record["width"] = AUGMENT_W
    record["height"] = AUGMENT_H
    return record


def _remap_coord(pt_permille: list, old_w: int, old_h: int,
                 offset_x: int, offset_y: int) -> list:
    """千分比坐标从 widget 空间转换到增强画布空间（含放大）。"""
    # 千分比 → widget 像素
    wx = pt_permille[0] / 999 * old_w
    wy = pt_permille[1] / 999 * old_h
    # widget 像素 → 放大后画布像素
    cx = wx * AUGMENT_SCALE + offset_x
    cy = wy * AUGMENT_SCALE + offset_y
    # 画布像素 → 新千分比
    return [min(999, round(cx / AUGMENT_W * 999)),
            min(999, round(cy / AUGMENT_H * 999))]

# ── per-type generators ──────────────────────────────────

def gen_slide(sample, type_dir):
    bg_path = OUT / "slide" / sample["bg"]
    sl_path = OUT / "slide" / sample["slide"]
    bg = load_img(bg_path)
    piece = load_img(sl_path)
    W, H = bg.size
    PW, PH = piece.size
    gap_x = sample["answer"]
    gap_y = sample["gap_y"]

    steps = []
    title = "请完成拼图验证"
    instr = "向右拖动滑块，将拼图滑入缺口"

    def composite(pos_x):
        frame = bg.convert("RGBA").copy()
        frame.paste(piece, (pos_x, gap_y), piece)
        return frame

    # t00: piece at left, slider at 0
    t00_raw = composite(0)
    t00 = render_widget(t00_raw, title, instr, controls="slider", slider_pos=0.0)

    # 计算滑块 thumb 在 widget 上的像素坐标
    scale = WIDGET_W / W
    scaled_h = int(H * scale)
    track_x, track_w = 14, WIDGET_W - 28
    track_y = HEADER_H + scaled_h + 26  # instr_pad=26
    thumb_cy = track_y + 22              # thumb 垂直中心
    thumb_start_cx = track_x + 4 + 18   # slider_pos=0 时 thumb 中心 X
    slider_ratio = gap_x / max(1, W - PW)
    thumb_end_cx = track_x + int(slider_ratio * (track_w - 36)) + 4 + 18

    steps.append({"t": 0, "screenshot": "t00.png",
                  "desc": "向右拖动滑块，将拼图滑入缺口",
                  "element_info": "滑块",
                  "action": {"type": "left_drag", "_widget": True,
                             "start_box": [thumb_start_cx, thumb_cy],
                             "end_box": [thumb_end_cx, thumb_cy]}})

    # t01: piece at answer, slider at target
    t01_raw = composite(gap_x)
    t01 = render_widget(t01_raw, title, instr, controls="slider", slider_pos=slider_ratio)
    steps.append({"t": 1, "screenshot": "t01.png", "desc": "验证完成", "action": None})

    idx = sample["idx"]
    d = type_dir / idx
    save(t00, d / "t00.png")
    save(t01, d / "t01.png")

    record = {"id": f"slide/{idx}", "type": "slide",
              "task": title,
              "width": t00.width, "height": t00.height, "steps": steps, "answer": gap_x}
    return to_permille(record, W, H)


def _click_sequence(base_img, answer_pts, label_fn, task, idx, type_dir, type_name):
    """通用：多点点击序列。answer_pts: list of {x,y}。"""
    steps = []
    marks = blank_marks(base_img)
    draw = ImageDraw.Draw(marks, "RGBA")

    # t00: clean image
    t00_raw = overlay(base_img, blank_marks(base_img))
    t00 = render_widget(t00_raw, task)
    save(t00, type_dir / idx / "t00.png")

    for i, pt in enumerate(answer_pts):
        action = {"type": "left_click", "start_box": [pt["x"], pt["y"]]}
        desc = label_fn(i, pt)
        steps.append({"t": i, "screenshot": f"t{i:02d}.png",
                      "desc": f"点击第{desc}个目标", "action": action})
        draw_dot(draw, pt["x"], pt["y"], label_fn(i, pt))
        t_next_raw = overlay(base_img, marks.copy())
        t_next = render_widget(t_next_raw, task)
        save(t_next, type_dir / idx / f"t{i+1:02d}.png")

    # final: no action
    steps.append({"t": len(answer_pts), "screenshot": f"t{len(answer_pts):02d}.png",
                  "desc": "验证完成", "action": None})

    cw, ch = base_img.size
    record = {"id": f"{type_name}/{idx}", "type": type_name,
              "task": task, "width": t00.width, "height": t00.height,
              "steps": steps, "answer": answer_pts}
    return to_permille(record, cw, ch)


def gen_geometry_click(sample, type_dir):
    img = load_img(OUT / "geometry_click" / sample["image"])
    task = f"请点击图中所有「{sample['target_shape']}」"
    return _click_sequence(img, sample["answer"],
                           lambda i, _: i+1, task,
                           sample["idx"], type_dir, "geometry_click")


def gen_click_order(sample, type_dir):
    img = load_img(OUT / "click_order" / sample["image"])
    mode = "字母" if sample["mode"] == "letter" else "数字"
    task = f"请按{mode}顺序依次点击图中字符"

    ans = sample["answer"]
    steps = []
    marks = blank_marks(img)
    draw = ImageDraw.Draw(marks, "RGBA")

    t00_raw = overlay(img, blank_marks(img))
    t00 = render_widget(t00_raw, task)
    save(t00, type_dir / sample["idx"] / "t00.png")

    for i, pt in enumerate(ans):
        action = {"type": "left_click",
                  "start_box": [pt["x"], pt["y"]],
                  "label": pt["label"]}
        steps.append({"t": i, "screenshot": f"t{i:02d}.png",
                      "desc": f"点击字符 {pt['label']}", "action": action})
        draw_dot(draw, pt["x"], pt["y"], pt["label"], (30, 120, 220))
        next_lbl = ans[i+1]["label"] if i+1 < len(ans) else "完成"
        t_next = render_widget(overlay(img, marks.copy()), task)
        save(t_next, type_dir / sample["idx"] / f"t{i+1:02d}.png")

    steps.append({"t": len(ans), "screenshot": f"t{len(ans):02d}.png",
                  "desc": "验证完成", "action": None})
    cw, ch = img.size
    record = {"id": f"click_order/{sample['idx']}", "type": "click_order",
              "task": task, "width": t00.width, "height": t00.height,
              "steps": steps, "answer": ans}
    return to_permille(record, cw, ch)


def gen_rotation_match(sample, type_dir):
    from PIL import Image as PILImage
    img_path = OUT / "rotation_match" / sample["image"]
    img = PILImage.open(img_path).convert("RGBA")
    IW, IH = img.size

    steps = []
    deg = sample["answer"]
    title = "旋转左侧图形与右侧参考对齐"
    instr = "拖动滑块旋转，使其对齐（误差≤5°通过）"

    # t00: original (current angle), slider at center
    t00 = render_widget(img.copy(), title, instr, controls="rotation", slider_pos=0.5)
    save(t00, type_dir / sample["idx"] / "t00.png")
    # 计算旋转滑条的起止像素位置（widget 坐标系）
    bar_x, bar_w = 56, WIDGET_W - 120
    instr_pad = 26
    bar_pixel_y = HEADER_H + int(IH * WIDGET_W / IW) + instr_pad + 2 + 8 + 2
    knob_start_x = bar_x + int(0.5 * bar_w)      # 初始中点
    knob_end_x   = bar_x + int(((deg + 180) / 360) * bar_w)
    steps.append({"t": 0, "screenshot": "t00.png",
                  "desc": f"拖动滑块旋转 {deg}° 对齐",
                  "element_info": "旋转滑块",
                  "action": {"type": "left_drag",
                             "start_box": [knob_start_x, bar_pixel_y],
                             "end_box": [knob_end_x, bar_pixel_y],
                             "degrees": deg}})

    # t01: left half rotated by answer degrees
    result = img.copy()
    left_crop = img.crop((0, 0, IW//2, IH)).convert("RGBA")

    rotated = PILImage.new("RGBA", (IW//2, IH), (240, 242, 248, 255))
    tmp = left_crop.rotate(-deg, resample=PILImage.BICUBIC,
                            center=(IW//4, IH//2), expand=False)
    rotated.paste(tmp, (0, 0), tmp)
    result.paste(rotated, (0, 0))

    slider_ratio = (deg + 180) / 360  # map [-180,180] → [0,1]
    t01 = render_widget(result, title, f"已旋转 {deg}°", controls="rotation", slider_pos=slider_ratio)
    save(t01, type_dir / sample["idx"] / "t01.png")
    steps.append({"t": 1, "screenshot": "t01.png", "desc": "验证完成", "action": None})

    # 将 widget 像素坐标转换为千分比
    ww, wh = t00.width, t00.height
    for step in steps:
        a = step.get("action")
        if a and "start_box" in a:
            a["start_box"] = [min(999, round(a["start_box"][0] / ww * 999)),
                              min(999, round(a["start_box"][1] / wh * 999))]
            a["end_box"]   = [min(999, round(a["end_box"][0] / ww * 999)),
                              min(999, round(a["end_box"][1] / wh * 999))]
    return {"id": f"rotation_match/{sample['idx']}", "type": "rotation_match",
            "task": title,
            "width": ww, "height": wh, "steps": steps, "answer": deg}


def gen_coordinates(sample, type_dir):
    ORIGIN_X, CELL = 40, 40
    img = load_img(OUT / "coordinates" / sample["image"])
    IH = img.height
    ORIGIN_Y = IH - ORIGIN_X
    idx = sample["idx"]
    icon_pos = sample.get("icon_pos", {"x": 0, "y": 0})
    task = f"将蓝色图标拖至坐标 ({sample['answer']['x']}, {sample['answer']['y']})"

    from_x = ORIGIN_X + icon_pos["x"] * CELL
    from_y = ORIGIN_Y - icon_pos["y"] * CELL
    to_x = ORIGIN_X + sample["answer"]["x"] * CELL
    to_y = ORIGIN_Y - sample["answer"]["y"] * CELL

    t00 = render_widget(img, task, f"请将蓝色图标拖动到坐标 ({sample['answer']['x']}, {sample['answer']['y']})")
    save(t00, type_dir / idx / "t00.png")

    marks = blank_marks(img)
    d = ImageDraw.Draw(marks, "RGBA")
    draw_dot(d, to_x, to_y, "✓", (30, 160, 90))
    t01 = render_widget(overlay(img, marks), task, "已完成")
    save(t01, type_dir / idx / "t01.png")

    steps = [
        {"t": 0, "screenshot": "t00.png",
         "desc": f"将蓝色图标拖至坐标 ({sample['answer']['x']}, {sample['answer']['y']})",
         "element_info": f"蓝色图标，当前位于坐标 ({icon_pos['x']}, {icon_pos['y']})",
         "action": {"type": "left_drag",
                    "start_box": [from_x, from_y],
                    "end_box": [to_x, to_y],
                    "grid_x": sample["answer"]["x"], "grid_y": sample["answer"]["y"]}},
        {"t": 1, "screenshot": "t01.png", "desc": "验证完成", "action": None},
    ]
    cw_val, ch_val = img.size
    record = {"id": f"coordinates/{idx}", "type": "coordinates",
              "task": task,
              "width": t00.width, "height": t00.height, "steps": steps, "answer": sample["answer"]}
    return to_permille(record, cw_val, ch_val)


# ── main ────────────────────────────────────────────────

GENERATORS = {
    "slide":          (lambda s, d: gen_slide(s, d),          "output/slide/labels.json"),
    "geometry_click": (gen_geometry_click,     "output/geometry_click/labels.json"),
    "rotation_match": (gen_rotation_match,     "output/rotation_match/labels.json"),
    "coordinates":    (gen_coordinates,        "output/coordinates/labels.json"),
    "click_order":    (gen_click_order,        "output/click_order/labels.json"),
}


def main():
    global BACKGROUND_IMG_DIRS, BLUR_RADIUS, BLUR_PROB
    
    parser = argparse.ArgumentParser(description="生成 GUI 交互轨迹数据（图片序列 + 千分比坐标标注）")
    parser.add_argument("--count", "-n", type=int, default=0,
                        help="每种类型生成的样本数（0=全部）")
    parser.add_argument("--type", "-t", default="all",
                        help="验证码类型，可选: " + ", ".join(GENERATORS.keys()) + ", all（默认 all）")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="并发线程数（默认 4）")
    parser.add_argument("--augment", "-a", action="store_true",
                        help="将 widget 合成到网页截图上做数据增强")
    parser.add_argument("--bg-dirs", nargs="+",
                        help="指定背景图路径（可多个），用于 augment 时随机选择")
    parser.add_argument("--blur-radius", type=float, default=1.0,
                        help="背景图模糊半径（默认 1.0，0 表示不模糊）")
    parser.add_argument("--blur-prob", type=float, default=0.5,
                        help="背景图模糊概率（默认 0.5 即 50%%，范围 0-1）")
    args = parser.parse_args()
    
    # 设置全局背景图路径
    if args.bg_dirs:
        BACKGROUND_IMG_DIRS = args.bg_dirs
        print(f"使用外部背景图路径: {BACKGROUND_IMG_DIRS}")
    
    # 设置全局模糊参数
    BLUR_RADIUS = args.blur_radius
    BLUR_PROB = args.blur_prob
    if BLUR_RADIUS == 0:
        print("背景图不应用模糊")
    else:
        print(f"背景图模糊半径: {BLUR_RADIUS}, 模糊概率: {BLUR_PROB*100:.0f}%")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    total = 0
    target_types = list(GENERATORS.keys()) if args.type == "all" else [args.type]

    for type_name in target_types:
        if type_name not in GENERATORS:
            print(f"[skip] 未知类型: {type_name}")
            continue
        fn, labels_file = GENERATORS[type_name]
        labels_path = BASE / labels_file
        if not labels_path.exists():
            print(f"[skip] {type_name}: {labels_file} not found")
            continue

        samples = json.loads(labels_path.read_text(encoding="utf-8"))
        if args.count > 0:
            samples = samples[:args.count]
        type_dir = GUI / type_name
        records = [None] * len(samples)

        def _process(idx_sample):
            i, sample = idx_sample
            rec = fn(sample, type_dir)
            sample_dir = type_dir / rec["id"].split("/")[-1]
            for step in rec["steps"]:
                step["screenshot"] = str(sample_dir / step["screenshot"])
            if args.augment:
                rec = apply_augment(rec, type_dir)
            return i, rec

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(_process, (i, s)): i for i, s in enumerate(samples)}
            for fut in as_completed(futures):
                try:
                    i, rec = fut.result()
                    records[i] = rec
                    total += 1
                except Exception as e:
                    idx = futures[fut]
                    print(f"  [err] {type_name}/{samples[idx].get('idx','?')}: {e}")

        records = [r for r in records if r is not None]
        if records:
            out_jsonl = type_dir / "labels.jsonl"
            out_jsonl.parent.mkdir(parents=True, exist_ok=True)
            out_jsonl.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
                encoding="utf-8"
            )
            print(f"  [{type_name}] {len(records)} samples → {type_dir}/")

    print(f"\n完成: 共 {total} 条轨迹数据 → {GUI}/")


if __name__ == "__main__":
    main()
