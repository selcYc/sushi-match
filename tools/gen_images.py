"""用 Gemini（Nano Banana）批量生成寿司插图，再处理成游戏用的 WebP。

提示词来自 docs/gemini-prompts.md（第一个代码块是风格，第二个是「带参考图」的模板，表格里是每个词的描述），
改提示词只改那个文件就行。

准备：
  1. 在 Google AI Studio 申请 API key，设成环境变量 GEMINI_API_KEY（脚本只从环境变量读）
  2. pip install google-genai pillow
  3. 把满意的那张风格参考图放在 img/raw/_reference.png（默认用金枪鱼）

用法（在项目文件夹里运行）：
  python tools/gen_images.py generate maguro salmon tamago   # 只生成这几种（先试几种确认风格）
  python tools/gen_images.py generate --n 3                  # 全部，每种 3 张候选（已有的候选会保留、只补不够的）
  python tools/gen_images.py sheet                           # 生成候选一览 img/raw/index.html
  python tools/gen_images.py pick maguro=2 salmon=1          # 记下挑中的候选（没挑的默认用第 1 张）
  python tools/gen_images.py process                         # 去白底、裁剪、压成 WebP，放进 img/sushi/

候选图在 img/raw/<id>/1.png、2.png……；挑选结果在 img/raw/picks.json；
处理好的图是 img/sushi/<id>.webp，清单在 data/images.json（游戏按清单决定用 WebP 还是旧的 SVG）。
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "docs" / "gemini-prompts.md"
RAW = ROOT / "img" / "raw"
REFERENCE = RAW / "_reference.png"
PICKS = RAW / "picks.json"
OUT = ROOT / "img" / "sushi"
MANIFEST = ROOT / "data" / "images.json"

DEFAULT_MODEL = "gemini-nano-banana-2.1"
# 每张 1K 图的大概价格（美元），只用来在开始前估算；以 Google 官方价目表为准
PRICE = {"gemini-nano-banana-2.1": 0.034, "gemini-3.1-flash-lite-image": 0.034, "gemini-3.1-flash-image": 0.067,
         "gemini-3-pro-image": 0.134, "gemini-2.5-flash-image": 0.039}
OUT_WIDTH = 480
TIMEOUT = 150  # 单张图最多等多少秒；正常 15 秒左右


# ---------- 提示词 ----------

def load_prompts():
    """从 docs/gemini-prompts.md 读出风格、模板和每个词的描述（按文件里的顺序）。"""
    text = PROMPTS.read_text(encoding="utf-8")
    # 按内容认代码块：带 "Sushi:" 的是第一张的完整提示词，带 {寿司描述} 的是模板（文件里还有用法说明的代码块）
    blocks = re.findall(r"^```[a-z]*\n(.*?)\n```$", text, re.S | re.M)
    first = next((b for b in blocks if "\nSushi:" in b), None)
    template = next((b for b in blocks if "{寿司描述}" in b), None)
    if not first or not template:
        sys.exit(f"{PROMPTS} 里没找到提示词代码块（第一张的完整提示词、带 {{寿司描述}} 的模板）")
    style = "\n".join(line for line in first.splitlines() if not line.startswith("Sushi:"))
    ids = {w["id"] for w in json.loads((ROOT / "data" / "words.json").read_text(encoding="utf-8"))["words"]}
    items = {}
    for m in re.finditer(r"^\| ([a-z]+) \| (.+?) \| [^|]+ \|$", text, re.M):
        if m.group(1) in ids:
            items[m.group(1)] = m.group(2).strip()
    missing = ids - items.keys()
    if missing:
        print("提示词表里还没有这些词：", ", ".join(sorted(missing)))
    return style, template, items


def build_prompt(style, template, desc, with_reference):
    if with_reference:
        return template.replace("{寿司描述}", desc)
    return f"{style}\nSushi: {desc}"


# ---------- 调用 Gemini ----------

def to_png(data):
    """Gemini 返回的其实常是 JPEG，统一转成 PNG 存。"""
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).save(buf, "PNG")
    return buf.getvalue()


def generate_one(client, model, prompt, ref_bytes, size):
    """生成一张图，返回 PNG 字节。优先用新的 Interactions 接口，SDK 太旧时退回 generate_content。"""
    if hasattr(client, "interactions"):
        parts = [{"type": "text", "text": prompt}]
        if ref_bytes:
            parts.append({"type": "image", "data": base64.b64encode(ref_bytes).decode(), "mime_type": "image/png"})
        it = client.interactions.create(
            model=model, input=parts,
            response_format={"type": "image", "aspect_ratio": "16:9", "image_size": size},
            timeout=TIMEOUT,
        )
        img = getattr(it, "output_image", None)
        if img is None or not img.data:
            raise RuntimeError(f"返回里没有图片（status={getattr(it, 'status', '?')}）")
        return to_png(base64.b64decode(img.data))

    from google.genai import types
    contents = [prompt]
    if ref_bytes:
        contents.append(types.Part.from_bytes(data=ref_bytes, mime_type="image/png"))
    resp = client.models.generate_content(
        model=model, contents=contents,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"],
                                           image_config=types.ImageConfig(aspect_ratio="16:9"),
                                           http_options=types.HttpOptions(timeout=TIMEOUT * 1000)),
    )
    for part in resp.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            data = part.inline_data.data
            return to_png(data if isinstance(data, bytes) else base64.b64decode(data))
    raise RuntimeError("返回里没有图片")


def candidates(wid):
    folder = RAW / wid
    return sorted(folder.glob("[0-9]*.png"), key=lambda p: int(p.stem)) if folder.exists() else []


def cmd_generate(args):
    style, template, items = load_prompts()
    ids = args.ids or list(items)
    unknown = [i for i in ids if i not in items]
    if unknown:
        sys.exit("提示词表里没有：" + ", ".join(unknown))

    ref_bytes = REFERENCE.read_bytes() if REFERENCE.exists() and not args.no_reference else None
    if ref_bytes is None and not args.no_reference:
        print(f"没找到参考图 {REFERENCE.relative_to(ROOT)}，会用「第一张」的完整风格提示词生成（风格可能不统一）")

    # 参考图本身就是金枪鱼的话，直接当作它的第 1 张候选
    if ref_bytes and "maguro" in ids and not candidates("maguro"):
        (RAW / "maguro").mkdir(parents=True, exist_ok=True)
        (RAW / "maguro" / "1.png").write_bytes(ref_bytes)

    todo = [(wid, args.n - len(candidates(wid))) for wid in ids]
    todo = [(wid, k) for wid, k in todo if k > 0]
    calls = sum(k for _, k in todo)
    if not calls:
        print("每种都已经有足够的候选了。要重新生成就先删掉 img/raw/<id>/ 里的图。")
        return
    price = PRICE.get(args.model)
    cost = f"，大约 ${calls * price:.2f}" if price else ""
    print(f"模型 {args.model}，要生成 {calls} 张（{len(todo)} 种）{cost}")
    if not args.yes and input("继续吗？[y/N] ").strip().lower() != "y":
        return

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        sys.exit("没有设置环境变量 GEMINI_API_KEY")
    from google import genai
    client = genai.Client()

    done = 0
    for wid, k in todo:
        prompt = build_prompt(style, template, items[wid], ref_bytes is not None)
        folder = RAW / wid
        folder.mkdir(parents=True, exist_ok=True)
        for _ in range(k):
            n = len(candidates(wid)) + 1
            for attempt in range(3):
                print(f"[{done + 1}/{calls}] {wid} #{n} 生成中……", end=" ", flush=True)
                t = time.time()
                try:
                    data = generate_one(client, args.model, prompt, ref_bytes, args.size)
                    (folder / f"{n}.png").write_bytes(data)
                    done += 1
                    print(f"好了（{time.time() - t:.0f} 秒）")
                    break
                except Exception as e:  # 网络错误、限流、超时等：等一会儿再试
                    wait = 5 * (attempt + 1)
                    print(f"失败（{type(e).__name__}: {e}），{wait} 秒后重试")
                    time.sleep(wait)
            else:
                print(f"  {wid} #{n} 跳过")
    print("完成。运行 `python tools/gen_images.py sheet` 生成候选一览来挑图。")


# ---------- 挑图 ----------

def load_picks():
    return json.loads(PICKS.read_text(encoding="utf-8")) if PICKS.exists() else {}


def cmd_pick(args):
    picks = load_picks()
    for item in args.choices:
        wid, _, k = item.partition("=")
        if not k.isdigit() or not (RAW / wid / f"{k}.png").exists():
            sys.exit(f"找不到候选 {item}（应写成 id=序号，比如 maguro=2）")
        picks[wid] = int(k)
    PICKS.write_text(json.dumps(picks, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已记下：", ", ".join(f"{k}={v}" for k, v in sorted(picks.items())))


def cmd_sheet(args):
    _, _, items = load_prompts()
    picks = load_picks()
    rows = ""
    for wid in items:
        cands = candidates(wid)
        if not cands:
            continue
        chosen = picks.get(wid, 1)
        cells = "".join(
            f'<figure class="{"on" if int(p.stem) == chosen else ""}"><img src="{wid}/{p.name}" loading="lazy"><figcaption>{wid}={p.stem}</figcaption></figure>'
            for p in cands)
        rows += f'<section><h2>{wid}</h2><p>{items[wid]}</p><div>{cells}</div></section>\n'
    html = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>候选插图</title>
<style>
body {{ font: 14px/1.5 system-ui, sans-serif; margin: 16px; background: #f3f4f6; color: #1c2b36; }}
section {{ background: #fff; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }}
h2 {{ margin: 0; font-size: 16px; }} p {{ margin: 4px 0 8px; color: #5c6b75; font-size: 12px; }}
section div {{ display: flex; gap: 8px; flex-wrap: wrap; }}
figure {{ margin: 0; width: 260px; border: 3px solid transparent; border-radius: 6px; }}
figure.on {{ border-color: #2b67a8; }}
img {{ width: 100%; display: block; }} figcaption {{ text-align: center; font-family: monospace; }}
</style>
<h1>候选插图</h1>
<p>蓝框是现在选中的（默认第 1 张）。要换就运行：python tools/gen_images.py pick id=序号</p>
{rows}"""
    (RAW / "index.html").write_text(html, encoding="utf-8")
    print(f"写好了 {(RAW / 'index.html').relative_to(ROOT)}。在项目文件夹运行 python -m http.server 8790，打开 http://localhost:8790/img/raw/")


# ---------- 去白底、裁剪、压缩 ----------

def cut_out(path):
    """从四边往里把接近纯白的背景变透明。盘子有灰色描边，会挡住，盘子本身的白不会被吃掉。"""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = bytearray(w * h)

    def white(c):
        return c[0] > 236 and c[1] > 236 and c[2] > 236

    q = deque([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])
    while q:
        x, y = q.popleft()
        i = y * w + x
        if bg[i] or not white(px[x, y]):
            continue
        bg[i] = 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not bg[ny * w + nx]:
                q.append((nx, ny))

    for y in range(h):
        for x in range(w):
            if bg[y * w + x]:
                px[x, y] = (255, 255, 255, 0)
            else:
                # 紧挨着背景、又很浅的一圈像素（抗锯齿的边）做成半透明，免得在深色背景上出现白边
                near = any(0 <= nx < w and 0 <= ny < h and bg[ny * w + nx]
                           for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
                if near:
                    r, g, b, _ = px[x, y]
                    alpha = max(0, min(255, (255 - min(r, g, b)) * 6))
                    px[x, y] = (r, g, b, alpha)
    return im.crop(im.getbbox())


def cmd_process(args):
    from PIL import Image
    _, _, items = load_prompts()
    picks = load_picks()
    ids = args.ids or [wid for wid in items if candidates(wid)]
    OUT.mkdir(parents=True, exist_ok=True)
    for wid in ids:
        src = RAW / wid / f"{picks.get(wid, 1)}.png"
        if not src.exists():
            print(f"{wid}：没有候选图，跳过")
            continue
        im = cut_out(src)
        im = im.resize((OUT_WIDTH, round(im.height * OUT_WIDTH / im.width)), Image.LANCZOS)
        dst = OUT / f"{wid}.webp"
        im.save(dst, "WEBP", quality=82, method=6)
        print(f"{wid}: {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}（{dst.stat().st_size // 1024} KB）")
    done = sorted(p.stem for p in OUT.glob("*.webp"))
    MANIFEST.write_text(json.dumps(done, indent=0) + "\n", encoding="utf-8")
    print(f"{len(done)} 种已经有 WebP（清单 {MANIFEST.relative_to(ROOT)}），其余继续用 SVG。")
    print("提醒：上线前把 app.js 的 ASSET_VERSION 改一下，免得手机用缓存里的旧图。")


def main():
    sys.stdout.reconfigure(line_buffering=True)  # 进度马上显示，不攒到最后
    ap =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="调用 Gemini 生成候选图")
    g.add_argument("ids", nargs="*", help="只生成这些词（默认全部）")
    g.add_argument("--n", type=int, default=2, help="每种要有几张候选（默认 2）")
    g.add_argument("--model", default=DEFAULT_MODEL)
    g.add_argument("--size", default="1K", choices=["1K", "2K", "4K"])
    g.add_argument("--no-reference", action="store_true", help="不带参考图，只用文字提示词")
    g.add_argument("--yes", action="store_true", help="不问确认直接开始")
    g.set_defaults(func=cmd_generate)
    s = sub.add_parser("sheet", help="生成候选一览 img/raw/index.html")
    s.set_defaults(func=cmd_sheet)
    p = sub.add_parser("pick", help="记下挑中的候选，比如 maguro=2")
    p.add_argument("choices", nargs="+")
    p.set_defaults(func=cmd_pick)
    r = sub.add_parser("process", help="去白底、裁剪、压成 WebP")
    r.add_argument("ids", nargs="*", help="只处理这些词（默认所有有候选的）")
    r.set_defaults(func=cmd_process)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
