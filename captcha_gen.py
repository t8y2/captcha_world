#!/usr/bin/env python3
"""
验证码批量生成器 — 统一 CLI
用法：
  python captcha_gen.py --type slide --count 50
  python captcha_gen.py --type dice_count --count 100
  python captcha_gen.py --type all --count 30
  python captcha_gen.py --list

支持的 type：
  slide           滑块缺口（单缺口拼图）
  dice_count      骰子计分
  geometry_click  几何图形点击
  rotation_match  旋转对齐
  dart_count      飞镖计分
  object_match    对象数量匹配
  coordinates     坐标拖拽
  path_finder     迷宫寻路
  place_dot       指定位置放点
  click_order     顺序点击
  all             全部类型
"""
import argparse
import json
import os
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(
        description="批量生成验证码",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--type", "-t", default="slide",
                        help="验证码类型（默认 slide），可用 all 生成全部")
    parser.add_argument("--count", "-n", type=int, default=50,
                        help="生成数量（默认 50）")
    parser.add_argument("--output", "-o", default="output",
                        help="输出根目录（默认 output）")
    parser.add_argument("--bg-dir", default="images/backgrounds",
                        help="slide 类型使用的背景图目录（可选）")
    parser.add_argument("--list", "-l", action="store_true",
                        help="列出所有支持的验证码类型")
    return parser.parse_args()


def main():
    args = parse_args()

    # 延迟导入（避免在 --list 时加载所有生成器）
    from generators import REGISTRY

    if args.list:
        print("支持的验证码类型：")
        for name in sorted(REGISTRY.keys()):
            cls = REGISTRY[name]
            print(f"  {name:<20} {cls.__doc__.strip().splitlines()[0] if cls.__doc__ else ''}")
        return

    target_types = list(REGISTRY.keys()) if args.type == "all" else [args.type]

    for t in target_types:
        if t not in REGISTRY:
            print(f"[ERROR] 未知类型: {t}，使用 --list 查看支持的类型", file=sys.stderr)
            sys.exit(1)

    total_labels = []
    t_start = time.time()

    for type_name in target_types:
        cls = REGISTRY[type_name]
        kwargs = {}
        if type_name == "slide" and os.path.isdir(args.bg_dir):
            kwargs["bg_dir"] = args.bg_dir

        gen = cls(output_dir=args.output, count=args.count, **kwargs)
        print(f"\n[生成] {type_name}  ×{args.count}  → {args.output}/{type_name}/")
        labels = gen.run()
        total_labels.extend(labels)

    elapsed = time.time() - t_start

    # 如果生成了多种类型，输出汇总
    if len(target_types) > 1:
        summary_path = os.path.join(args.output, "all_labels.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(total_labels, f, ensure_ascii=False, indent=2)
        print(f"\n[汇总] {summary_path}")

    print(f"\n[完成] 共生成 {len(total_labels)} 条  耗时 {elapsed:.1f}s")
    print(f"       输出目录: {os.path.abspath(args.output)}/")


if __name__ == "__main__":
    main()
