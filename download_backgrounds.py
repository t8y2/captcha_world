"""
批量下载风景图作为验证码背景
来源：随机从以下 API 获取：
  - 必应每日壁纸 https://bing.img.run/rand_1366x768.php
  - 风景图 API   https://tu.ltyuanfang.cn/api/fengjing.php
输出：images/backgrounds/
"""

import os
import time
import random
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

# ──────────── 配置 ────────────────────
CONFIG = {
    "count": 50,                        # 要下载的图片数量
    "output_dir": "images/backgrounds", # 保存目录
    "width": 400,                       # 图片宽度（裁剪后）
    "height": 180,                      # 图片高度（裁剪后）
    "source_urls": [
        "https://bing.img.run/rand_1366x768.php",
        "https://tu.ltyuanfang.cn/api/fengjing.php",
    ],
    "workers": 4,                       # 并发下载线程数
    "timeout": 20,                      # 单张超时（秒）
    "retry": 2,                         # 失败重试次数
    "delay": 0.3,                       # 每次请求间隔（秒）
}
# ─────────────────────────────────────


def ensure_dir():
    os.makedirs(CONFIG["output_dir"], exist_ok=True)


def build_url() -> str:
    """随机选择一个图片源 API"""
    return random.choice(CONFIG["source_urls"])


def download_one(idx: int) -> dict:
    """下载单张图片并裁剪到目标尺寸，返回状态信息"""
    import io
    from PIL import Image

    w, h = CONFIG["width"], CONFIG["height"]
    url = build_url()
    save_path = os.path.join(CONFIG["output_dir"], f"bg_{idx:04d}.jpg")

    if os.path.exists(save_path):
        return {"idx": idx, "status": "skip", "path": save_path}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    max_attempts = CONFIG["retry"] + 2
    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=CONFIG["timeout"]) as resp:
                data = resp.read()
            if len(data) < 5000:
                raise ValueError(f"图片过小 ({len(data)} bytes)")
            # 裁剪到目标尺寸（居中裁剪）
            img = Image.open(io.BytesIO(data)).convert("RGB")
            src_w, src_h = img.size
            scale = max(w / src_w, h / src_h)
            new_w = int(src_w * scale)
            new_h = int(src_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img = img.crop((left, top, left + w, top + h))
            img.save(save_path, "JPEG", quality=92)
            return {"idx": idx, "status": "ok", "path": save_path}
        except Exception as e:
            if attempt < max_attempts:
                time.sleep(0.8)
            else:
                return {"idx": idx, "status": "fail", "error": str(e), "url": url}

    return {"idx": idx, "status": "fail", "error": "unknown"}


def main():
    ensure_dir()
    count = CONFIG["count"]
    print(f"[INFO] 开始下载 {count} 张背景图 → {CONFIG['output_dir']}/")
    print(f"[INFO] 并发线程: {CONFIG['workers']}，超时: {CONFIG['timeout']}s\n")

    ok_count = 0
    fail_list = []

    with ThreadPoolExecutor(max_workers=CONFIG["workers"]) as pool:
        futures = {}
        for i in range(1, count + 1):
            time.sleep(CONFIG["delay"])  # 控制请求频率
            fut = pool.submit(download_one, i)
            futures[fut] = i

        for fut in as_completed(futures):
            result = fut.result()
            if result["status"] == "ok":
                ok_count += 1
                print(f"  [{ok_count:>3}/{count}] ✓ {result['path']}")
            elif result["status"] == "skip":
                ok_count += 1
                print(f"  [skip] {result['path']}")
            else:
                fail_list.append(result)
                print(f"  [FAIL] #{result['idx']}  {result.get('error','')}")

    print(f"\n[完成] 成功 {ok_count} 张，失败 {len(fail_list)} 张")
    if fail_list:
        print("失败列表：")
        for r in fail_list:
            print(f"  #{r['idx']}  {r.get('url','')}  {r.get('error','')}")

    print(f"\n下载完成后，运行以下命令生成验证码：")
    print(f"  python slider_captcha_generator.py")


if __name__ == "__main__":
    main()
