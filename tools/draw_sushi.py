"""生成寿司插图：斜俯视的盘子上，斜着摆两贯（卷物是三块）。

用法：python tools/draw_sushi.py
输出到 img/sushi/<id>.svg

画法参考了图库里辨识度高的回转寿司插画（调研见 docs/illustration-research.md）：
- 不描黑边，靠「亮面 / 固有色 / 暗面」三档色块分出形体
- 鱼片是一头宽一头尖的「楔形」，拱在米饭上，尖头往下垂
- 每种寿司只抓一两个最有辨识度的特征，并且放大（三文鱼的白纹、虾尾、葱花……）
- 高光用几道短短的白色小笔触，显得新鲜、湿润
- 米饭大部分被盖住，只露出底下一圈，带一点冷色阴影

每种寿司在一贯自己的坐标里描述（长轴横放，宽头在左，x 约 -33..34，y 约 -12..11），
盘子、米饭、厚度、旋转都由这里统一处理。
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "img" / "sushi"

ANGLE = -30  # 斜放角度：左下到右上
SCALE = 0.86
PAIR = [(52, 44), (68, 60)]

# 鱼片：拱在米饭上的月牙形，中间高、两头往下垂；左头宽，右头收尖
WEDGE = ("M-34 6 C-34 -4 -22 -13 -2 -13.5 C16 -13.8 30 -6 37 5 "
         "C30 4.5 16 8 -2 9.5 C-16 10.6 -26 12 -31 11.2 C-33.5 10.6 -34 8.5 -34 6 Z")
# 鱼片前缘露出来的侧面：沿着前缘往下一条带子，两头垂得多、中间少
SIDE = ("M-34 6 C-34 8.5 -33.5 10.6 -31 11.2 C-26 12 -16 10.6 -2 9.5 C16 8 30 4.5 37 5 "
        "C37.5 8 36 10.5 33 11 C24 10 14 11.5 -2 12.2 C-16 13 -26 16.5 -31 16.8 C-34 17 -35 12 -34 6 Z")
# 两头垂下去的地方颜色更暗
END_SHADE = ('<ellipse cx="-31" cy="6" rx="7" ry="10" fill="{c}" opacity="0.45" filter="url(#soft)"/>'
             '<ellipse cx="32" cy="3" rx="6" ry="6" fill="{c}" opacity="0.45" filter="url(#soft)"/>')

COMMON_DEFS = """    <filter id="soft" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="0.8"/></filter>
    <linearGradient id="plate" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#eef1f4"/>
    </linearGradient>
"""


def f(n):
    return f"{n:.1f}".rstrip("0").rstrip(".")


def bumpy_ellipse(rx, ry, n, seed, bump=(0.3, 0.9)):
    """边缘一粒粒鼓起来的椭圆，用来画米饭。"""
    rnd = random.Random(seed)
    pts = [(rx * math.cos(2 * math.pi * i / n), ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    d = f"M{f(pts[0][0])} {f(pts[0][1])}"
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        mx, my = rx * math.cos(a), ry * math.sin(a)
        nx, ny = math.cos(a) / rx, math.sin(a) / ry
        k = math.hypot(nx, ny)
        b = rnd.uniform(*bump) * 1.6
        x, y = pts[(i + 1) % n]
        d += f" Q{f(mx + nx / k * b)} {f(my + ny / k * b)} {f(x)} {f(y)}"
    return d + " Z"


def grain_marks(seed, count, xr, yr, color="#cdd4dc"):
    """米饭上几道短短的弧线，暗示一粒粒的米。"""
    rnd = random.Random(seed)
    out = ""
    for _ in range(count):
        x, y = rnd.uniform(*xr), rnd.uniform(*yr)
        out += (f'<path d="M{f(x)} {f(y)} q1.4 {f(rnd.uniform(0.6, 1.2))} 2.8 0" transform="rotate({rnd.randint(-30, 30)} {f(x)} {f(y)})" '
                f'fill="none" stroke="{color}" stroke-width="0.8" stroke-linecap="round"/>')
    return out


def glints(points):
    """湿润感：几道白色小笔触。"""
    return "".join(
        f'<path d="M{f(x)} {f(y)} l{f(l)} {f(-l * 0.18)}" stroke="#fff" stroke-width="{f(w)}" stroke-linecap="round" opacity="0.9"/>'
        for x, y, l, w in points
    )


def svg(defs, body):
    return (
        # 上面 10 个单位是空白（最高的虾尾也在 y=15 以下），裁掉，同样高度下寿司显得更大
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 10 120 86">\n'
        f"  <defs>\n{COMMON_DEFS}{defs}  </defs>\n{body}</svg>\n"
    )


def plate():
    return """  <ellipse cx="60" cy="90" rx="52" ry="5" fill="#1c2b36" opacity="0.10"/>
  <ellipse cx="60" cy="63" rx="56" ry="27" fill="#cfd6dc"/>
  <ellipse cx="60" cy="60" rx="56" ry="27" fill="url(#plate)"/>
  <ellipse cx="60" cy="61.5" rx="44" ry="19.5" fill="#e8ecf0"/>
  <ellipse cx="60" cy="60.5" rx="43" ry="18.5" fill="#f6f8fa"/>
  <path d="M10 56 C18 42 38 35 60 34" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>
"""


def layer(x, y, dy, content):
    """把一层内容放到 (x, y)，先往下挪 dy（屏幕方向），再斜着转。"""
    return f'  <g transform="translate({f(x)} {f(y + dy)}) rotate({ANGLE}) scale({SCALE})">{content}</g>\n'


def rice(x, y, seed):
    """米饭：冷灰色的底 + 白色的饭团，只露出鱼片下面那一圈。"""
    mound = bumpy_ellipse(23, 11.5, 44, seed)
    out = layer(x, y, 10.5, f'<path d="{mound}" fill="#d3d9e1"/>')
    for d in (8.5, 6.5, 4.5):
        out += layer(x, y, d, f'<path d="{mound}" fill="#fbfbf8"/>')
    out += layer(x, y, 8.5, grain_marks(seed, 10, (-18, 16), (4, 10)))
    return out


def nigiri(name, item):
    shape = item.get("shape", WEDGE)
    body = ""
    for i, (x, y) in enumerate(PAIR):
        body += rice(x, y, f"{name}{i}")
        side = item.get("side_shape", SIDE if shape == WEDGE else None)
        if side:
            # 鱼片前缘的侧面（两头往下垂）
            body += layer(x, y, 0, f'<path d="{side}" fill="{item.get("side", item["shadow"])}"/>')
        else:
            # 方块（玉子）：每 0.5 叠一层，做出均匀的厚度
            thick = item.get("thick", 2.6)
            for d in [thick] + [k / 2 for k in range(int(thick * 2) - 1, 0, -1)]:
                body += layer(x, y, d, f'<path d="{shape}" fill="{item["shadow"]}"/>{item.get("side_extra", "") if d == thick else ""}')
        body += layer(
            x, y, 0,
            f'{item.get("under", "")}'
            f'<clipPath id="c{i}"><path d="{shape}"/></clipPath>'
            f'<path d="{shape}" fill="url(#t)"/>'
            f'<g clip-path="url(#c{i})">{item.get("pattern", "")}'
            f'{END_SHADE.format(c=item["shadow"]) if item.get("drape", True) else ""}</g>'
            f'{item.get("over", "")}',
        )
    defs = (f'    <linearGradient id="t" x1="0" y1="0" x2="0.15" y2="1">'
            f'<stop offset="0" stop-color="{item["light"]}"/><stop offset="0.45" stop-color="{item["base"]}"/>'
            f'<stop offset="1" stop-color="{item["shadow"]}"/></linearGradient>\n') + item.get("defs", "")
    return svg(defs, plate() + body)


NORI_DEFS = """    <linearGradient id="noriSide" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#2a362f"/><stop offset="0.3" stop-color="#3b4a41"/><stop offset="1" stop-color="#1a221e"/>
    </linearGradient>
"""


def gunkan(name, item):
    oval = "M-25 0 C-25 -9 -13 -12.5 0 -12.5 C13 -12.5 25 -9 25 0 C25 9 13 12.5 0 12.5 C-13 12.5 -25 9 -25 0 Z"
    inner = "M-21.5 -0.5 C-21.5 -7.5 -11 -10 0 -10 C11 -10 21.5 -7.5 21.5 -0.5 C21.5 6.5 11 9.5 0 9.5 C-11 9.5 -21.5 6.5 -21.5 -0.5 Z"
    body = ""
    for i, (x, y) in enumerate(PAIR):
        for d in (13, 11, 9, 7, 5, 3, 1):
            body += layer(x, y, d, f'<path d="{oval}" fill="{"#141b17" if d == 13 else "url(#noriSide)"}"/>')
        body += layer(x, y, 8, '<path d="M-22 4 C-12 9 4 10 16 7" fill="none" stroke="#3d4d43" stroke-width="0.8" opacity="0.7"/>')
        body += layer(
            x, y, 0,
            f'<path d="{oval}" fill="#2c3a31"/><path d="{inner}" fill="{item["base"]}"/>'
            f'{item["filling"](f"{name}{i}")}',
        )
    return svg(item.get("defs", "") + NORI_DEFS, plate() + body)


def maki(name, item):
    top = "M-12.5 0 C-12.5 -5.5 -7 -8.5 0 -8.5 C7 -8.5 12.5 -5.5 12.5 0 C12.5 5.5 7 8.5 0 8.5 C-7 8.5 -12.5 5.5 -12.5 0 Z"
    body = ""
    for i, (x, y) in enumerate([(84, 40), (60, 50), (36, 60)]):
        seed = f"{name}{i}"
        r = bumpy_ellipse(10, 6.6, 20, seed, bump=(0.2, 0.6))
        body += f'  <g transform="translate({x} {y}) scale(1.22)">'
        body += '<path d="M-12.5 0 V13 C-12.5 18.5 -7 21.5 0 21.5 C7 21.5 12.5 18.5 12.5 13 V0 Z" fill="url(#noriSide)"/>'
        body += '<path d="M-9 4 V17" stroke="#56685c" stroke-width="1.6" stroke-linecap="round" opacity="0.7"/>'
        body += f'<path d="{top}" fill="#2c3a31"/><path d="{r}" fill="#fbfbf8"/>'
        body += grain_marks(seed, 6, (-8, 6), (-5, 4))
        body += item["core"]
        body += "</g>\n"
    return svg(item.get("defs", "") + NORI_DEFS, plate() + body)


# ---------- 各种寿司的特征 ----------

def ridge_light(color="#ffffff", opacity=0.35):
    """顶面靠上的一道柔光，表现鱼片拱起来的弧度。"""
    return (f'<path d="M-28 -5 C-14 -10.5 10 -10.5 30 -3.5" fill="none" stroke="{color}" stroke-width="4" '
            f'opacity="{opacity}" filter="url(#soft)"/>')


def salmon_pattern():
    out = ""
    for x, w in ((-26, 2.4), (-15, 1.6), (-5, 2.4), (6, 1.8), (16, 2.2), (26, 1.4)):
        # 白色脂肪纹：顺着鱼片拱起来的弧线，粗细不一
        out += (f'<path d="M{x + 5} -14 C{x} -7 {x + 4} 3 {x - 2} 13" fill="none" stroke="#fff3e8" stroke-width="{w}" opacity="0.95"/>'
                f'<path d="M{x + 9} -14 C{x + 4} -7 {x + 8} 3 {x + 2} 13" fill="none" stroke="#ffc9a5" stroke-width="0.7" opacity="0.7"/>')
    return out + ridge_light() + glints([(-20, -7, 4, 1.2), (-6, -9, 5, 1.3), (10, -8.5, 3.5, 1.1)])


def maguro_pattern():
    out = "".join(
        f'<path d="M{x} -13 C{x + 3} -5 {x - 1} 4 {x + 2} 12" fill="none" stroke="#f0707c" stroke-width="0.8" opacity="0.25"/>'
        for x in range(-24, 34, 11)
    )
    return out + ridge_light(opacity=0.25) + glints([(-22, -6, 4, 1.3), (-9, -9, 6, 1.4), (6, -9.5, 3, 1.1), (15, -8, 4.5, 1.2)])


def ebi_pattern():
    out = ""
    for x in (-27, -16, -5, 6, 16):
        out += f'<path d="M{x} -13 C{x + 3} -5 {x + 3} 4 {x} 12 H{x + 7} C{x + 10} 4 {x + 10} -5 {x + 7} -13 Z" fill="url(#shell)"/>'
        out += f'<path d="M{x + 7} -13 C{x + 10} -5 {x + 10} 4 {x + 7} 12" fill="none" stroke="#fff" stroke-width="1" opacity="0.6"/>'
    return out + ridge_light(opacity=0.3) + glints([(-18, -8, 3.5, 1.1), (-4, -9.5, 4, 1.2), (10, -8.5, 3, 1)])


def saba_pattern(seed):
    rnd = random.Random(seed)
    # 背上是青色、肚子是银白：先铺背色，再画深色波浪纹
    out = '<path d="M-40 -16 H40 V-1 C20 -3 -10 -2 -40 2 Z" fill="url(#back)"/>'
    for x in range(-30, 34, 5):
        x += rnd.uniform(-1, 1)
        d = f"M{f(x)} -13"
        yy = -13
        while yy < -1:
            step = rnd.uniform(3.5, 5)
            d += f" q{f(rnd.uniform(1.5, 3) * rnd.choice([-1, 1]))} {f(step / 2)} {f(rnd.uniform(-1.2, 0.6))} {f(step)}"
            yy += step
        out += f'<path d="{d}" fill="none" stroke="#163246" stroke-width="{f(rnd.uniform(1.2, 2.2))}" stroke-linecap="round" opacity="0.85"/>'
    out += '<path d="M-40 0.5 C-10 -2 15 -2.5 40 -1" fill="none" stroke="#d8e4ea" stroke-width="1.6" opacity="0.9"/>'
    out += '<path d="M-30 5 C-10 7 10 6.5 30 3" fill="none" stroke="#d6c8f0" stroke-width="2.5" opacity="0.35" filter="url(#soft)"/>'
    return out + glints([(-22, -6, 4, 1.2), (-8, -9, 5, 1.3), (8, -9, 3.5, 1.1), (-14, 4, 4, 1)])


def aji_pattern():
    out = '<path d="M-40 -16 H40 V-2 C20 -4 -10 -3 -40 1 Z" fill="url(#back)"/>'
    out += '<path d="M-40 0 C-10 -3 15 -3.5 40 -2" fill="none" stroke="#e1c96a" stroke-width="1.1"/>'
    out += '<path d="M-30 4 C-10 6.5 10 6 30 2.5" fill="none" stroke="#ffffff" stroke-width="2.5" opacity="0.6" filter="url(#soft)"/>'
    return out + glints([(-24, -5, 3.5, 1.1), (-12, 3.5, 5, 1.2), (14, -7.5, 3.5, 1)])


def aji_garnish():
    rnd = random.Random("aji")
    out = '<path d="M-8 -1 C-9.5 -6 -3 -8.5 2 -8 C7 -7.5 10 -4 8.5 -0.5 C7 2.5 1 4 -2 3.5 C-5.5 3 -7.5 1.5 -8 -1 Z" fill="#f2d98c"/>'
    out += '<path d="M-6 -3 C-2 -6 4 -6 7 -3" fill="none" stroke="#fff3c4" stroke-width="1.4" stroke-linecap="round"/>'
    for _ in range(10):
        x, y = rnd.uniform(-6, 6), rnd.uniform(-6, 2)
        out += f'<path d="M{f(x)} {f(y)} l{f(rnd.uniform(-1.4, 1.4))} {f(rnd.uniform(0.6, 1.4))}" stroke="#cfa94a" stroke-width="0.6" stroke-linecap="round"/>'
    for cx, cy in [(-4, -4), (2.5, -5), (5.5, -0.5), (-1, 0.5), (-5.5, 1)]:
        out += (f'<circle cx="{cx}" cy="{cy}" r="2.3" fill="#4f9a3a"/>'
                f'<circle cx="{cx - 0.3}" cy="{cy - 0.3}" r="1.6" fill="#86c25e"/>'
                f'<circle cx="{cx - 0.2}" cy="{cy - 0.2}" r="0.75" fill="#e6f4d6"/>')
    return out


def ikura_filling(seed):
    rnd = random.Random(seed)
    spots = [(-16, -2), (-10, -6.5), (-2, -8), (6, -7.5), (13, -5), (18, 0), (-12, 3), (-4, 0), (4, 0), (12, 2.5),
             (-7, 6.5), (1, 7), (9, 6.5), (16, 5), (-17, 5)]
    out = ""
    for cx, cy in spots:
        cx += rnd.uniform(-0.5, 0.5)
        cy += rnd.uniform(-0.5, 0.5)
        out += (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="3.9" fill="url(#roe)"/>'
                f'<circle cx="{f(cx + 0.8)}" cy="{f(cy + 1)}" r="1.2" fill="#e0581f" opacity="0.8"/>'
                f'<circle cx="{f(cx - 1.3)}" cy="{f(cy - 1.4)}" r="0.95" fill="#fff"/>')
    # 两片立起来的黄瓜，军舰上最常见的点缀
    for tx, rot in ((-15, -12), (-8, 4)):
        out += (f'<g transform="translate({tx} -7) rotate({rot})">'
                '<path d="M-6 0 A6 6.5 0 0 1 6 0 Z" fill="#2f6e2a"/>'
                '<path d="M-5 0 A5 5.4 0 0 1 5 0 Z" fill="#cfe8a6"/>'
                '<path d="M-3.4 0 A3.4 3.6 0 0 1 3.4 0 Z" fill="#e4f2c8"/>'
                '<g fill="#f6fbea"><ellipse cx="-1.6" cy="-1.4" rx="0.5" ry="0.8"/><ellipse cx="0" cy="-2" rx="0.5" ry="0.8"/><ellipse cx="1.6" cy="-1.4" rx="0.5" ry="0.8"/></g>'
                "</g>")
    return out


ITEMS = {
    "maguro": dict(kind=nigiri, light="#ec6672", base="#d23545", shadow="#9c1f30", pattern=maguro_pattern()),
    "salmon": dict(kind=nigiri, light="#ffaa70", base="#f7823e", shadow="#d45f26", pattern=salmon_pattern()),
    "ebi": dict(
        kind=nigiri, light="#ffffff", base="#fbeee8", shadow="#e9c2b3",
        shape=("M-34 6 C-34 -4 -22 -12.5 -2 -12.5 C14 -12.5 24 -7 29 -1 C30.5 1 30 3 28 3.6 "
               "C20 5 12 8 -2 9.5 C-16 10.6 -26 12 -31 11.2 C-33.5 10.6 -34 8.5 -34 6 Z"),
        side_shape=("M-34 6 C-34 8.5 -33.5 10.6 -31 11.2 C-26 12 -16 10.6 -2 9.5 C12 8 20 5 28 3.6 "
                    "C29 6 28.5 8 26.5 8.8 C20 9.5 12 11 -2 12.2 C-16 13 -26 16.5 -31 16.8 C-34 17 -35 12 -34 6 Z"),
        defs='    <linearGradient id="shell" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff8a55"/><stop offset="1" stop-color="#e2402a"/></linearGradient>\n'
             '    <linearGradient id="tail" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f25a38"/><stop offset="1" stop-color="#9e2016"/></linearGradient>\n',
        under='<path d="M25 -2 L42 -12 C39.5 -4 39.5 4 42 12 L25 3 Z" fill="url(#tail)"/>'
              '<path d="M29 -3 L40 -9.5 M30 0 L40.5 -2.5 M30 1.5 L40.5 4 M29 3.5 L40 10" stroke="#7d1810" stroke-width="0.7" opacity="0.7"/>'
              '<path d="M40.5 -10 C39.3 -4 39.3 4 40.5 10" fill="none" stroke="#5a140c" stroke-width="1.8" opacity="0.6"/>',
        pattern=ebi_pattern(),
    ),
    "tamago": dict(
        kind=nigiri, light="#ffe98f", base="#f7cf4a", shadow="#dba42c", thick=5, drape=False,
        shape="M-29 -11 H29 Q32 -11 32 -8 V8 Q32 11 29 11 H-29 Q-32 11 -32 8 V-8 Q-32 -11 -29 -11 Z",
        side_extra='<path d="M-31 8.5 H31 M-31 10.5 H31" stroke="#bf8a1e" stroke-width="0.6" opacity="0.8"/>'
                   '<path d="M-5.5 -11 H5.5 V11 H-5.5 Z" fill="#141b17"/>',
        pattern='<g fill="#d99a35" opacity="0.4"><ellipse cx="-21" cy="-3" rx="3.4" ry="1.3"/><ellipse cx="-14" cy="5" rx="2.4" ry="1"/>'
                '<ellipse cx="15" cy="-5" rx="2.8" ry="1.2"/><ellipse cx="22" cy="4" rx="3.2" ry="1.3"/></g>'
                '<path d="M-6 -12 H6 V12 H-6 Z" fill="url(#band)"/>'
                '<path d="M-3 -10 V10 M2 -10 V10" stroke="#4b5d51" stroke-width="0.6" opacity="0.8"/>'
                + glints([(-25, -7, 5, 1.3), (11, -7.5, 6, 1.3)]),
        defs='    <linearGradient id="band" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3a4a40"/><stop offset="1" stop-color="#18201b"/></linearGradient>\n',
    ),
    "saba": dict(
        kind=nigiri, light="#ffffff", base="#e6ecf0", shadow="#c3ced6", side="#efd6cf",
        defs='    <linearGradient id="back" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b6878"/><stop offset="1" stop-color="#7fa6b0"/></linearGradient>\n',
        pattern=saba_pattern("saba"),
    ),
    "aji": dict(
        kind=nigiri, light="#ffffff", base="#dde4e7", shadow="#b4c2c8", side="#e8b4ac",
        defs='    <linearGradient id="back" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5b7d84"/><stop offset="1" stop-color="#a9bfc2"/></linearGradient>\n',
        pattern=aji_pattern(),
        over=f'<g transform="translate(-2 -1) scale(1.3)">{aji_garnish()}</g>',
    ),
    "ikura": dict(
        kind=gunkan, base="#a52e10",
        defs='    <radialGradient id="roe" cx="0.36" cy="0.32" r="0.72"><stop offset="0" stop-color="#ffc99c"/>'
             '<stop offset="0.4" stop-color="#f7702e"/><stop offset="0.85" stop-color="#cf3c10"/><stop offset="1" stop-color="#93270a"/></radialGradient>\n',
        filling=ikura_filling,
    ),
    "kappamaki": dict(
        kind=maki,
        core='<rect x="-4.4" y="-3.2" width="8.8" height="5.6" rx="1" fill="#2f6e2a"/>'
             '<rect x="-3.8" y="-2" width="7.6" height="4" rx="0.8" fill="#c5e397"/>'
             '<g fill="#f2f8e4"><ellipse cx="-2" cy="0.2" rx="0.6" ry="0.4"/><ellipse cx="0.2" cy="0.5" rx="0.6" ry="0.4"/><ellipse cx="2.2" cy="0.1" rx="0.6" ry="0.4"/></g>',
    ),
}


# ---------- 常用的点缀 ----------

GINGER_SCALLION = f'<g transform="translate(-2 -1) scale(1.3)">{aji_garnish()}</g>'


def back_band(fill, y=-1):
    """鱼皮那一侧（顶面靠后）的一条颜色带。"""
    return f'<path d="M-40 -16 H40 V{f(y - 2)} C20 {f(y - 4)} -10 {f(y - 3)} -40 {f(y + 1)} Z" fill="{fill}"/>'


def scallions(spots, r=2.3):
    """葱花：一个个空心的绿圈。"""
    return "".join(
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="#4f9a3a"/>'
        f'<circle cx="{f(cx - 0.3)}" cy="{f(cy - 0.3)}" r="{f(r * 0.7)}" fill="#86c25e"/>'
        f'<circle cx="{f(cx - 0.2)}" cy="{f(cy - 0.2)}" r="{f(r * 0.33)}" fill="#e6f4d6"/>'
        for cx, cy in spots
    )


def marbling(xs, color, widths, opacity):
    """顺着鱼片弧度的脂肪纹（中腹、大腹）。"""
    return "".join(
        f'<path d="M{f(x + 5)} -14 C{f(x)} -7 {f(x + 4)} 3 {f(x - 2)} 13" fill="none" stroke="{color}" '
        f'stroke-width="{widths[i % len(widths)]}" opacity="{opacity}"/>'
        for i, x in enumerate(xs)
    )


def momiji_chives():
    """红叶萝卜泥 + 细葱，比目鱼常见的配料。"""
    rnd = random.Random("momiji")
    out = '<path d="M-6 0 C-7 -4 -3 -6.5 0 -6.5 C4 -6.5 7 -4 6 0 C5 2.5 -4 2.8 -6 0 Z" fill="#ef8a5a"/>'
    out += '<path d="M-4 -3 C-1 -5 2 -5 4 -3" fill="none" stroke="#ffc39c" stroke-width="1.2" stroke-linecap="round"/>'
    for _ in range(8):
        out += f'<circle cx="{f(rnd.uniform(-4.5, 4.5))}" cy="{f(rnd.uniform(-5, 0.5))}" r="0.5" fill="#d0602f"/>'
    return out + scallions([(6.5, -3.5), (8.5, 0.3), (4, 1.6)], r=1.6)


def onion_slivers():
    """炙烤长鳍金枪鱼上的洋葱丝 + 葱花。"""
    out = ""
    for d in ("M-9 -2 C-6 -5 -2 -5 1 -3", "M-4 1 C-1 -2 3 -2 6 0", "M0 -5 C3 -7 7 -6 9 -4"):
        out += f'<path d="{d}" fill="none" stroke="#e3dccb" stroke-width="2.6" stroke-linecap="round"/>'
        out += f'<path d="{d}" fill="none" stroke="#fffdf6" stroke-width="1.6" stroke-linecap="round"/>'
    return out + scallions([(-3, -5.5), (4, -1.5)], r=1.8)


def dots(seed, n, xr, yr, color, r=(0.6, 1.1), opacity=1):
    rnd = random.Random(seed)
    return "".join(
        f'<circle cx="{f(rnd.uniform(*xr))}" cy="{f(rnd.uniform(*yr))}" r="{f(rnd.uniform(*r))}" fill="{color}" opacity="{opacity}"/>'
        for _ in range(n)
    )


def grad(gid, stops, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'    <linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient>\n'


def radial(gid, stops, cx=0.4, cy=0.35, r=0.7):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'    <radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>\n'


STD_GLINTS = glints([(-20, -7, 4, 1.2), (-6, -9.5, 5, 1.3), (10, -8.5, 3.5, 1.1)])
EBI_SHAPE = ITEMS["ebi"]["shape"]
EBI_SIDE = ITEMS["ebi"]["side_shape"]
HOTATE = "M-32 3 C-32 -7 -18 -13 0 -13 C18 -13 32 -7 32 3 C32 9 18 12 0 12 C-18 12 -32 9 -32 3 Z"
HOTATE_SIDE = ("M-32 3 C-32 9 -18 12 0 12 C18 12 32 9 32 3 C32.5 8 31 13 26 15 "
               "C18 17.5 -18 17.5 -26 15 C-31 13 -32.5 8 -32 3 Z")


ENGAWA = ("M-34 4 C-34 -2 -24 -8 -2 -8.5 C16 -8.8 30 -4 36 3 "
          "C30 3 16 5.5 -2 6.5 C-16 7.2 -26 8.5 -31 8 C-33.5 7.6 -34 6 -34 4 Z")
ENGAWA_SIDE = ("M-34 4 C-34 6 -33.5 7.6 -31 8 C-26 8.5 -16 7.2 -2 6.5 C16 5.5 30 3 36 3 "
               "C36.5 6 35 8.5 32 9 C24 8.5 14 9.5 -2 10 C-16 10.6 -26 13.5 -31 13.8 C-34 14 -35 9 -34 4 Z")
IKA = "M-30 -9 Q-30 -12 -27 -12 H28 Q31 -12 31 -9 V8 Q31 11 28 11 H-27 Q-30 11 -30 8 Z"
IKA_SIDE = "M-30 8 Q-30 11 -27 11 H28 Q31 11 31 8 V11 Q31 14 28 14 H-27 Q-30 14 -30 11 Z"


def crosshatch(color, step=3.5, width=0.6, opacity=0.9):
    out = ""
    for k in range(-14, 14):
        x = k * step
        out += f'<path d="M{f(x)} -16 l16 32 M{f(x)} 16 l16 -32" stroke="{color}" stroke-width="{width}" opacity="{opacity}"/>'
    return out


def chiai(color, d, opacity=0.9):
    """血合：靠背骨那一侧的一块深红色。"""
    return f'<path d="{d}" fill="{color}" opacity="{opacity}" filter="url(#soft)"/>'


def suckers():
    out = ""
    for x in range(-24, 28, 7):
        out += f'<circle cx="{x}" cy="-6.5" r="2.3" fill="#f2c4d0"/><circle cx="{x}" cy="-6.5" r="1.1" fill="#d996aa"/>'
    return out


# ---------- 军舰的料 ----------

def uni_filling(seed):
    rnd = random.Random(seed)
    lobes = [(-12, -5, -20), (0, -6.5, -8), (12, -4, 12), (-13, 3, -14), (-1, 2, -4), (11, 3.5, 10), (-5, 7.5, 2), (7, 8, 6)]
    out = ""
    for cx, cy, rot in lobes:
        out += (f'<g transform="translate({cx} {cy}) rotate({rot})"><ellipse rx="8" ry="3.8" fill="url(#uni)"/>'
                f'<path d="M-5 -1.6 C-2 -2.6 2 -2.6 5 -1.6" fill="none" stroke="#ffe3a0" stroke-width="1" stroke-linecap="round"/></g>')
    out += dots(seed, 40, (-19, 19), (-8, 9), "#ffd98a", r=(0.35, 0.6), opacity=0.8)
    return out


def tobikko_filling(seed):
    rnd = random.Random(seed)
    out = ""
    for _ in range(90):
        a, rr = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random())
        x, y = 20 * rr * math.cos(a), 8.3 * rr * math.sin(a)
        out += f'<circle cx="{f(x)}" cy="{f(y)}" r="1.5" fill="#ff8a2a"/><circle cx="{f(x - 0.5)}" cy="{f(y - 0.5)}" r="0.45" fill="#fff1d2"/>'
    return out


def kanimiso_filling(seed):
    out = '<ellipse cx="0" cy="0" rx="20" ry="8.4" fill="#86814b"/>'
    out += ('<path d="M-14 -3 C-8 -7 2 -6 8 -3 C12 -1 16 -3 18 0" fill="none" stroke="#b0a764" stroke-width="3" opacity="0.8" filter="url(#soft)"/>'
            '<path d="M-16 4 C-8 1 0 5 8 3 C12 2 15 4 17 3" fill="none" stroke="#5d5930" stroke-width="2.4" opacity="0.7" filter="url(#soft)"/>')
    out += dots(seed, 10, (-16, 16), (-6, 6), "#c96a3a", r=(0.5, 0.9), opacity=0.7)
    return out + glints([(-10, -4, 4, 1.1), (5, -5, 3, 1)])


def shirasu_filling(seed):
    rnd = random.Random(seed)
    out = ""
    for _ in range(30):
        a, rr = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random())
        x, y = 18 * rr * math.cos(a), 7.5 * rr * math.sin(a)
        rot = rnd.randint(0, 180)
        out += (f'<g transform="translate({f(x)} {f(y)}) rotate({rot})">'
                '<path d="M-2.4 0 Q0 -1.3 2.4 0" fill="none" stroke="#cfc9b8" stroke-width="2"/>'
                '<path d="M-2.4 0 Q0 -1.3 2.4 0" fill="none" stroke="#fdfbf3" stroke-width="1.2"/>'
                '<circle cx="-2.2" cy="-0.1" r="0.45" fill="#2b2b2b"/></g>')
    return out + scallions([(-6, -4), (5, 2)], r=1.7)


def negitoro_filling(seed):
    out = '<ellipse cx="0" cy="0" rx="20" ry="8.4" fill="#ea8592"/>'
    out += dots(seed, 30, (-17, 17), (-7, 7), "#f6a7b1", r=(1, 2), opacity=0.8)
    out += dots(seed + "b", 18, (-17, 17), (-7, 7), "#d9677a", r=(0.8, 1.6), opacity=0.7)
    return out + scallions([(-10, -3), (-3, -5), (4, -2), (11, -4), (-6, 3), (2, 4), (9, 3)], r=2.2)


# ---------- 豆皮寿司 ----------

POUCH = ("M-27 -6 C-27 -11 -23 -13 -17 -13 H17 C23 -13 27 -11 27 -6 V5 "
         "C27 10 23 12 17 12 H-17 C-23 12 -27 10 -27 5 Z")


def inari(name, item):
    body = ""
    for i, (x, y) in enumerate(PAIR):
        for k in range(12, 0, -1):
            body += layer(x, y, k / 2, f'<path d="{POUCH}" fill="{"#9a5a1e" if k == 12 else "#b8742c"}"/>')
        body += layer(
            x, y, 0,
            f'<clipPath id="c{i}"><path d="{POUCH}"/></clipPath><path d="{POUCH}" fill="url(#t)"/>'
            f'<g clip-path="url(#c{i})">{dots(f"{name}{i}", 26, (-25, 25), (-11, 10), "#a8651f", r=(0.5, 1.1), opacity=0.55)}'
            f'<path d="M-22 -8 C-10 -11 10 -11 22 -8" fill="none" stroke="#fff3d6" stroke-width="3" opacity="0.45" filter="url(#soft)"/>'
            f'<path d="M-20 -2 C-14 -3 -10 -1 -6 -2 M4 3 C10 2 14 4 20 3" fill="none" stroke="#b9732b" stroke-width="1" opacity="0.7"/></g>'
            + glints([(-16, -8, 4, 1.1), (8, -9, 3, 1)]),
        )
    return svg(grad("t", [(0, "#efbd73"), (0.5, "#dc9b4c"), (1, "#bd7a32")]), plate() + body)


# ---------- 副菜：碗、杯子、小碟 ----------

def bowl(defs, outer, rim, soup, contents, band=""):
    body = f"""  <ellipse cx="60" cy="87" rx="42" ry="5" fill="#1c2b36" opacity="0.12"/>
  <ellipse cx="60" cy="80" rx="18" ry="4.5" fill="#1c2b36" opacity="0.25"/>
  <path d="M14 40 C16 64 36 81 60 81 C84 81 104 64 106 40 Z" fill="{outer}"/>
  {band}
  <path d="M22 52 C28 66 40 74 52 76" fill="none" stroke="#fff" stroke-width="2.4" opacity="0.25" stroke-linecap="round"/>
  <ellipse cx="60" cy="40" rx="46" ry="17.5" fill="{rim}"/>
  <ellipse cx="60" cy="41.2" rx="41.5" ry="15" fill="{soup}"/>
  {contents}
"""
    return svg(defs, body)


def misoshiru(name, item):
    c ='<path d="M30 40 C40 34 56 36 64 40 C72 44 84 42 90 38" fill="none" stroke="#e2b27a" stroke-width="6" opacity="0.5" filter="url(#soft)"/>'
    for x, y, r in ((44, 38, -8), (62, 45, 12), (76, 37, 4)):  # 豆腐
        c += (f'<g transform="translate({x} {y}) rotate({r})"><rect x="-4.5" y="-2.5" width="9" height="6.5" rx="1" fill="#e9e3d6"/>'
              '<rect x="-4.5" y="-3.5" width="9" height="5" rx="1" fill="#fffdf6"/></g>')
    for x, y in ((52, 47), (70, 41), (38, 44)):  # 海带
        c += (f'<path d="M{x - 5} {y} C{x - 3} {y - 4} {x + 3} {y - 4} {x + 6} {y - 1} C{x + 2} {y + 2} {x - 2} {y + 3} {x - 5} {y} Z" fill="#2f5a2a"/>'
              f'<path d="M{x - 3} {y - 1} C{x} {y - 3} {x + 3} {y - 2} {x + 4} {y - 1}" fill="none" stroke="#4f7d45" stroke-width="0.8"/>')
    c += scallions([(56, 36), (66, 34), (48, 42), (82, 43), (60, 40)], r=1.9)
    c += glints([(30, 36, 5, 1.2), (84, 36, 4, 1)])
    defs = (grad("lacq", [(0, "#3a3436"), (1, "#141012")], x2=1, y2=0.4)
            + radial("miso", [(0, "#d9a56a"), (1, "#a96f3a")], cx=0.45, cy=0.4, r=0.65))
    return bowl(defs, "url(#lacq)", "#8f2a1e", "url(#miso)", c)


def udon(name, item):
    c = ""
    for d in ("M24 40 C36 32 50 50 64 40 C76 32 86 46 98 40", "M28 46 C40 38 54 54 70 44 C80 38 88 48 94 45",
              "M30 35 C42 30 54 42 66 35 C76 30 84 38 92 34", "M36 50 C48 44 60 54 74 49"):
        c += f'<path d="{d}" fill="none" stroke="#e0cfa6" stroke-width="5.2" stroke-linecap="round"/>'
        c += f'<path d="{d}" fill="none" stroke="#fdf8ea" stroke-width="3.8" stroke-linecap="round"/>'
    c += ('<g transform="translate(78 38) rotate(-10)"><path d="M-8 2 C-8 -5 8 -5 8 2 Z" fill="#fffaf2"/>'
          '<path d="M-8 2 C-8 -5 8 -5 8 2" fill="none" stroke="#f07d9a" stroke-width="1.6"/>'
          '<path d="M-4 1 C-4 -2 4 -2 4 1" fill="none" stroke="#f7b4c5" stroke-width="0.9"/></g>')
    c += scallions([(46, 38), (54, 34), (60, 44), (40, 45), (68, 36)], r=1.9)
    c += dots("udon7", 8, (40, 70), (34, 46), "#c8402a", r=(0.4, 0.7))
    band = '<path d="M17 50 C26 62 44 70 60 70 C76 70 94 62 103 50" fill="none" stroke="#2e5f9e" stroke-width="3"/>'
    defs = grad("ub", [(0, "#ffffff"), (1, "#dfe5ec")], x2=1, y2=0.3)
    return bowl(defs, "url(#ub)", "#f4f6f8", "#e7c27c", c, band=band)


def chawanmushi(name, item):
    body = """  <ellipse cx="60" cy="86" rx="42" ry="5" fill="#1c2b36" opacity="0.12"/>
  <ellipse cx="60" cy="74" rx="44" ry="12" fill="#cfd6dc"/>
  <ellipse cx="60" cy="72" rx="44" ry="12" fill="#f6f8fa"/>
  <path d="M30 36 C31 60 44 74 60 74 C76 74 89 60 90 36 Z" fill="url(#cup)"/>
  <path d="M33 50 C40 60 50 64 60 64 C70 64 80 60 87 50" fill="none" stroke="#2e4f8a" stroke-width="2"/>
  <path d="M38 58 l4 -3 l4 3 l4 -3 l4 3 l4 -3 l4 3 l4 -3 l4 3 l4 -3 l4 3" fill="none" stroke="#2e4f8a" stroke-width="1"/>
  <ellipse cx="60" cy="36" rx="30" ry="11" fill="#fbfcfd"/>
  <ellipse cx="60" cy="37" rx="26.5" ry="9" fill="url(#custard)"/>
  <path d="M42 34 C50 30 62 30 72 32" fill="none" stroke="#fff" stroke-width="2.4" opacity="0.6" stroke-linecap="round"/>
  <g transform="translate(66 38)"><path d="M-6 1 C-6 -4 2 -6 6 -2 C3 -1 1 2 -2 3 C-4 3.5 -6 3 -6 1 Z" fill="#f58a6a"/>
    <path d="M-4 0 C-2 -3 2 -3.5 4 -2" fill="none" stroke="#fff" stroke-width="1" opacity="0.8"/></g>
  <g transform="translate(52 36)"><ellipse cx="-3" cy="0" rx="3.2" ry="2" fill="#5ea34a"/><ellipse cx="3" cy="0" rx="3.2" ry="2" fill="#5ea34a"/>
    <ellipse cx="0" cy="-2.6" rx="2" ry="3" fill="#6fb655"/><path d="M0 0 L0 4" stroke="#3f7a2c" stroke-width="0.9"/></g>
"""
    defs = grad("cup", [(0, "#ffffff"), (1, "#dde4eb")], x2=1, y2=0.3) + grad("custard", [(0, "#fdf0c2"), (1, "#f0d27c")])
    return svg(defs, body)


def wasabi(name, item):
    c = ('  <ellipse cx="60" cy="62" rx="16" ry="5" fill="#1c2b36" opacity="0.12"/>\n'
         '  <path d="M44 60 C42 52 50 46 56 44 C60 40 62 34 66 33 C66 38 64 42 68 45 C76 48 78 56 74 60 C68 65 50 65 44 60 Z" fill="url(#w)"/>\n'
         '  <path d="M50 52 C54 48 60 47 64 48 M48 58 C56 56 66 57 72 55" fill="none" stroke="#b9dc84" stroke-width="1.4" opacity="0.8" stroke-linecap="round"/>\n'
         f'  {dots("wasabi", 26, (46, 74), (46, 62), "#4f8a2a", r=(0.4, 0.8), opacity=0.6)}\n'
         f'  {glints([(52, 49, 4, 1.1), (62, 38, 2.5, 1)])}\n')
    c = f'  <g transform="translate(60 56) scale(1.5) translate(-60 -56)">\n{c}  </g>\n'
    return svg(grad("w", [(0, "#a8d266"), (1, "#5f9a35")], x2=0.3, y2=1), plate() + c)


def gari(name, item):
    rnd = random.Random(name)
    c = '  <ellipse cx="60" cy="64" rx="20" ry="6" fill="#1c2b36" opacity="0.10"/>\n'
    for _ in range(9):
        x, y = 60 + rnd.uniform(-12, 12), 54 + rnd.uniform(-6, 6)
        rot, rx = rnd.randint(-40, 40), rnd.uniform(8, 11)
        c += (f'  <g transform="translate({f(x)} {f(y)}) rotate({rot})">'
              f'<ellipse rx="{f(rx)}" ry="{f(rx * 0.6)}" fill="#f9d8d2" opacity="0.92"/>'
              f'<ellipse rx="{f(rx)}" ry="{f(rx * 0.6)}" fill="none" stroke="#efb2aa" stroke-width="0.9"/>'
              f'<path d="M{f(-rx * 0.6)} 0 C0 -1.5 {f(rx * 0.3)} 1 {f(rx * 0.6)} 0" fill="none" stroke="#f3c2bb" stroke-width="0.6"/></g>\n')
    c += f'  {glints([(54, 48, 4, 1.1), (66, 52, 3, 1)])}\n'
    c = f'  <g transform="translate(60 56) scale(1.4) translate(-60 -56)">\n{c}  </g>\n'
    return svg("", plate() + c)


ITEMS.update({
    # 赤身
    "chutoro": dict(kind=nigiri, light="#f9a6ac", base="#ea6f7d", shadow="#c24658",
                    pattern=marbling(range(-28, 36, 7), "#ffe3e5", (1.4, 0.8), 0.8) + ridge_light() + STD_GLINTS),
    "otoro": dict(kind=nigiri, light="#ffdcdb", base="#f4adb2", shadow="#d97b86",
                  pattern=marbling([x / 2 for x in range(-60, 76, 9)], "#fff5f3", (2.2, 1.2, 1.6), 0.9) + ridge_light() + STD_GLINTS),
    "katsuo": dict(kind=nigiri, light="#d65463", base="#b52a3d", shadow="#7e1828",
                   defs=grad("sear", [(0, "#5f666f"), (1, "#a3a8ad")]),
                   pattern=back_band("url(#sear)", -3)
                   + "".join(f'<path d="M{x} -12 l3 6" stroke="#3a2a22" stroke-width="1.6" opacity="0.6" stroke-linecap="round"/>' for x in range(-26, 30, 6))
                   + STD_GLINTS,
                   over=GINGER_SCALLION),
    "bincho": dict(kind=nigiri, light="#fbe1dc", base="#f0c3bb", shadow="#d49a91",
                   pattern=chiai("#c4844f", "M-34 -16 H38 V-4 C20 -7 -10 -6 -34 -2 Z", 0.55)
                   + dots("bincho", 14, (-28, 28), (-12, -4), "#7a4a2a", r=(0.5, 1), opacity=0.6) + STD_GLINTS,
                   over=onion_slivers()),
    # 白身
    "tai": dict(kind=nigiri, light="#ffffff", base="#f6ecea", shadow="#e0c6c2",
                defs=grad("skin", [(0, "#d93b52"), (1, "#f4a3a6")]),
                pattern=back_band("url(#skin)", -5)
                + '<path d="M-40 -5 C-10 -9 15 -9.5 40 -6" fill="none" stroke="#ffffff" stroke-width="1.4" opacity="0.9"/>'
                + marbling(range(-26, 34, 9), "#ffffff", (0.8,), 0.6) + STD_GLINTS),
    # 比目鱼：通透的白色月牙，靠正中间放大的红叶萝卜泥 + 葱来认
    "hirame": dict(kind=nigiri, light="#ffffff", base="#eeedea", shadow="#cdd0d3",
                   pattern='<ellipse cx="2" cy="1" rx="22" ry="6" fill="#dfe3e8" opacity="0.6" filter="url(#soft)"/>'
                   + "".join(f'<path d="M-32 8 Q{x - 10} -2 {x} -14" fill="none" stroke="#ffffff" stroke-width="0.9" opacity="0.75"/>'
                             for x in range(-24, 40, 7))
                   + ridge_light(opacity=0.5) + STD_GLINTS,
                   over=f'<g transform="translate(0 -3) scale(1.6)">{momiji_chives()}</g>'),
    # 鳍边肉：窄长的一条奶黄色，表面一道道粗横纹（下面露出更多米饭）
    "engawa": dict(kind=nigiri, light="#fffcf0", base="#f4e9cc", shadow="#d6bf8d", side="#cdb582",
                   shape=ENGAWA, side_shape=ENGAWA_SIDE,
                   pattern="".join(
                       f'<path d="M{f(x + 2)} -12 C{f(x)} -5 {f(x + 1.5)} 2 {f(x - 0.5)} 9" fill="none" stroke="#d6bd88" stroke-width="1.8"/>'
                       f'<path d="M{f(x + 3.6)} -12 C{f(x + 1.6)} -5 {f(x + 3.1)} 2 {f(x + 1.1)} 9" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.9"/>'
                       for x in [k * 4 for k in range(-9, 10)])
                   + ridge_light(opacity=0.5) + STD_GLINTS),
    "hamachi": dict(kind=nigiri, light="#fff3ec", base="#f6d5c6", shadow="#dcab98",
                    pattern=chiai("#c4525c", "M-36 -16 H8 C-2 -11 -18 -8 -36 -5 Z") + ridge_light() + STD_GLINTS),
    "buri": dict(kind=nigiri, light="#fff0e6", base="#f0cab5", shadow="#d39c85",
                 pattern=chiai("#a3343d", "M-36 -16 H20 C8 -9 -14 -5 -36 -1 Z")
                 + marbling(range(-10, 34, 9), "#fff7f0", (1.2,), 0.8) + ridge_light() + STD_GLINTS),
    "kanpachi": dict(kind=nigiri, light="#ffffff", base="#f8e8e0", shadow="#ddbcae",
                     pattern=chiai("#e79a9a", "M-36 -16 H40 V-10 C20 -11 -10 -10 -36 -7 Z", 0.8) + ridge_light() + STD_GLINTS),
    # 光物
    "iwashi": dict(kind=nigiri, light="#ffffff", base="#e2e8ec", shadow="#b9c5cd", side="#e4b0a6",
                   defs=grad("back", [(0, "#3e5f7c"), (1, "#8aa5b8")]),
                   pattern=back_band("url(#back)", -1)
                   + "".join(f'<circle cx="{x}" cy="{f(1.2 - abs(x) * 0.04)}" r="1.1" fill="#1f2f3d"/>' for x in range(-26, 26, 7))
                   + STD_GLINTS,
                   over=GINGER_SCALLION),
    "kohada": dict(kind=nigiri, light="#ffffff", base="#e8ebe4", shadow="#b9c1ba", side="#efd2c8",
                   defs=grad("back", [(0, "#7f918a"), (1, "#c3ccc4")]),
                   pattern=back_band("url(#back)", 0)
                   + "".join(f'<circle cx="{x + (2.5 if row % 2 else 0)}" cy="{y}" r="0.85" fill="#3a4a48"/>'
                             for row, y in enumerate((-10, -6.5, -3)) for x in range(-30, 34, 5))
                   + '<path d="M-6 -12 l-4 22 M8 -12 l-4 22" stroke="#ffffff" stroke-width="1" opacity="0.8"/>'
                   + '<path d="M-40 2 C-10 -1 15 -1.5 40 0" fill="none" stroke="#d6c66e" stroke-width="1"/>' + STD_GLINTS),
    "sanma": dict(kind=nigiri, light="#ffffff", base="#dfe5ea", shadow="#aeb9c2", side="#e3b1a8",
                  defs=grad("back", [(0, "#2e3c5a"), (1, "#6c7f9e")]),
                  pattern=back_band("url(#back)", 1)
                  + '<path d="M-40 2.5 C-10 -0.5 15 -1 40 0.5" fill="none" stroke="#ffffff" stroke-width="1.6"/>' + STD_GLINTS,
                  over=scallions([(-6, -4), (0, -6), (6, -4.5), (-2, -1), (4, 0)], r=2.3)),
    # 贝类
    "hotate": dict(kind=nigiri, light="#fffdf6", base="#f6ecdc", shadow="#d9c6a8", shape=HOTATE, side_shape=HOTATE_SIDE, drape=False,
                   # 纹路很淡：扇贝看起来是一整块光滑圆润的贝肉，免得和有粗横纹的鳍边肉混
                   pattern="".join(f'<path d="M{x} -14 C{x + 1} -4 {x - 1} 5 {x} 13" fill="none" stroke="#eadabb" stroke-width="0.7" opacity="0.4"/>' for x in range(-28, 30, 6))
                   + '<path d="M0 -13 C1 -3 -1 6 0 12" fill="none" stroke="#e2cfac" stroke-width="1.3"/>'
                   + ridge_light(opacity=0.5) + STD_GLINTS),
    "akagai": dict(kind=nigiri, light="#ff9d74", base="#ee5d3a", shadow="#c03a22",
                   pattern='<path d="M-34 7 C-26 4 -22 9 -14 6 C-6 3 -2 8 6 5 C14 2 18 6 26 3 C30 1.5 34 3 38 2" fill="none" stroke="#ffbf9e" stroke-width="2.2"/>'
                   + '<path d="M-22 -2 C-8 -5 8 -5 24 -2" fill="none" stroke="#a82a17" stroke-width="1.3"/>'
                   + ridge_light() + STD_GLINTS),
    "tsubugai": dict(kind=nigiri, light="#ffffff", base="#f4f1ea", shadow="#cfc6b5", side="#a99a85",
                     pattern=f'<path d="{WEDGE}" fill="none" stroke="#8f7f6a" stroke-width="6" opacity="0.55" filter="url(#soft)"/>'
                     + "".join(f'<path d="M{x} -10 l1 4" stroke="#dcd2c1" stroke-width="0.8"/>' for x in range(-24, 28, 4))
                     + STD_GLINTS),
    "hokkigai": dict(kind=nigiri, light="#ffffff", base="#f3edef", shadow="#d6c6ca",
                     # 煮过的北极贝，尖端是红的：从右往左褪色
                     defs='    <linearGradient id="tip" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#e8485e"/>'
                          '<stop offset="0.55" stop-color="#f39aa8"/><stop offset="1" stop-color="#f3edef"/></linearGradient>\n',
                     pattern='<path d="M2 -16 H40 V16 H2 Z" fill="url(#tip)" filter="url(#soft)"/>'
                     + '<path d="M-24 -1 C-10 -4 6 -4 22 -1" fill="none" stroke="#c8b0b6" stroke-width="1"/>' + STD_GLINTS),
    "awabi": dict(kind=nigiri, light="#efe6c6", base="#d6c897", shadow="#a99a66", side="#8f8456",
                  pattern=crosshatch("#b5a674", step=4, width=0.7)
                  + f'<path d="{WEDGE}" fill="none" stroke="#6e6a40" stroke-width="4" opacity="0.5" filter="url(#soft)"/>' + STD_GLINTS),
    # 虾蟹乌贼章鱼
    "amaebi": dict(kind=nigiri, light="#ffd8cc", base="#ffaa96", shadow="#e57d6b", side="#f19d8b",
                   shape=EBI_SHAPE, side_shape=EBI_SIDE,
                   under='<path d="M24 -4 L36 -11 C34 -7 34 -3 35 -1 L25 0 Z" fill="#ff6b4a"/>'
                         '<path d="M24 1 L35 1 C34 4 34 8 36 11 L25 4 Z" fill="#f2583a"/>',
                   pattern='<path d="M-34 1 C-10 -2 14 -2 30 0.5" fill="none" stroke="#ffd2c6" stroke-width="1.4"/>'
                   + "".join(f'<path d="M{x} -12 C{x + 2} -6 {x + 2} 6 {x} 12" fill="none" stroke="#f59a86" stroke-width="0.8" opacity="0.7"/>' for x in range(-24, 26, 8))
                   + ridge_light(opacity=0.5) + STD_GLINTS),
    "botanebi": dict(kind=nigiri, light="#ffc6b8", base="#f78a7a", shadow="#d65a4e", side="#e98374",
                     shape=EBI_SHAPE, side_shape=EBI_SIDE,
                     defs=ITEMS["ebi"]["defs"],
                     under=ITEMS["ebi"]["under"],
                     pattern=dots("botan", 40, (-30, 26), (-12, 10), "#d0302a", r=(0.4, 0.9), opacity=0.7)
                     + "".join(f'<path d="M{x} -12 C{x + 2} -6 {x + 2} 6 {x} 12" fill="none" stroke="#ffb3a3" stroke-width="1" opacity="0.8"/>' for x in range(-24, 26, 9))
                     + ridge_light(opacity=0.45) + STD_GLINTS),
    "kani": dict(kind=nigiri, light="#ffffff", base="#f8f3ee", shadow="#dacfc4",
                 defs=grad("crab", [(0, "#e8432c"), (1, "#ff9a7a")]),
                 pattern="".join(f'<path d="M-40 {y} C-10 {y - 2} 15 {y - 2.5} 40 {y - 1}" fill="none" stroke="#e8ddd2" stroke-width="0.7"/>' for y in range(0, 12, 2))
                 + back_band("url(#crab)", -2) + STD_GLINTS),
    # 鱿鱼：切成方方正正的一片，雪白、很亮，一个方向的细斜刀纹
    "ika": dict(kind=nigiri, light="#ffffff", base="#f5f8fb", shadow="#bccad8", side="#b9c7d5",
                shape=IKA, side_shape=IKA_SIDE, drape=False,
                pattern="".join(f'<path d="M{x} -14 l9 28" stroke="#c7d2de" stroke-width="0.9"/>' for x in range(-40, 36, 5))
                # 白色放在白盘上会糊成一片：边缘压一圈冷灰，轮廓才出得来
                + f'<path d="{IKA}" fill="none" stroke="#a9b8c8" stroke-width="3.5" opacity="0.7" filter="url(#soft)"/>'
                + '<path d="M-28 -8 H26" stroke="#ffffff" stroke-width="3.5" opacity="0.8" filter="url(#soft)" stroke-linecap="round"/>'
                + glints([(-24, -9, 7, 1.4), (-8, -9.5, 5, 1.3), (10, -9, 8, 1.4), (-18, 5, 4, 1)])),
    "tako": dict(kind=nigiri, light="#ffffff", base="#f6edf0", shadow="#dcc4cb", side="#9b3550",
                 defs=grad("skin", [(0, "#7e2240"), (1, "#c45a7a")]),
                 pattern=back_band("url(#skin)", -3) + suckers() + STD_GLINTS),
    # 军舰
    "uni": dict(kind=gunkan, base="#c9781e",
                defs=radial("uni", [(0, "#ffd877"), (0.6, "#f0a232"), (1, "#c97418")]), filling=uni_filling),
    "tobikko": dict(kind=gunkan, base="#e0661a", filling=tobikko_filling),
    "kanimiso": dict(kind=gunkan, base="#6e6a3c", filling=kanimiso_filling),
    "shirasu": dict(kind=gunkan, base="#ece8dc", filling=shirasu_filling),
    "negitoro": dict(kind=gunkan, base="#e07a88", filling=negitoro_filling),
    # 卷物
    "tekkamaki": dict(kind=maki, core='<rect x="-4.6" y="-3.4" width="9.2" height="6.4" rx="1.4" fill="#c8323a"/>'
                                       '<rect x="-4" y="-3" width="8" height="2" rx="1" fill="#e5606c"/>'),
    "kanpyomaki": dict(kind=maki, core='<rect x="-4.6" y="-3.4" width="9.2" height="3" rx="1.2" fill="#8a5428"/>'
                                        '<rect x="-4.2" y="-0.2" width="8.4" height="3" rx="1.2" fill="#a86a35"/>'
                                        '<path d="M-3 -2.6 H3" stroke="#c48a52" stroke-width="0.8"/>'),
    "nattomaki": dict(kind=maki, core="".join(
        f'<ellipse cx="{x}" cy="{y}" rx="1.9" ry="1.4" fill="#b98144"/><ellipse cx="{x - 0.5}" cy="{y - 0.5}" rx="0.8" ry="0.5" fill="#e6bd80"/>'
        for x, y in ((-2.5, -1.5), (1.5, -2), (3, 1), (-1, 1.5), (-4, 1)))
        + '<path d="M-4 -2 C-1 0 1 -1 4 2 M-3 2 C0 0 2 1 3 -2" fill="none" stroke="#fff8ea" stroke-width="0.4" opacity="0.9"/>'),
    "shinkomaki": dict(kind=maki, core='<rect x="-4.6" y="-3.4" width="9.2" height="6.4" rx="1.2" fill="#ecc832"/>'
                                        '<rect x="-4" y="-3" width="8" height="2" rx="1" fill="#f8e47a"/>'),
    # 其他
    "inari": dict(kind=inari),
    "anago": dict(kind=nigiri, light="#e9bb84", base="#c98d50", shadow="#8f5a2c", side="#7a4a22",
                  pattern="".join(f'<path d="M-36 {y} C-14 {y - 3} 10 {y + 2} 38 {y - 1}" fill="none" stroke="#f1cfa0" stroke-width="1.2" opacity="0.6"/>' for y in (-7, -2, 3))
                  + '<ellipse cx="0" cy="-2" rx="26" ry="7" fill="#5e3216" opacity="0.35" filter="url(#soft)"/>'
                  + glints([(-22, -7, 5, 1.4), (-6, -9.5, 7, 1.5), (12, -8, 4, 1.2), (-12, 3, 3, 1)])),
    "unagi": dict(kind=nigiri, light="#b8703e", base="#8a4a22", shadow="#5a2d14", side="#4a2410",
                  defs=ITEMS["tamago"]["defs"],
                  pattern="".join(f'<path d="M{x} -14 l-5 28" stroke="#3a1a0c" stroke-width="3" opacity="0.5"/>' for x in (-22, -12, 10, 20))
                  + '<path d="M-6 -16 H6 V16 H-6 Z" fill="url(#band)"/>'
                  + glints([(-24, -6, 5, 1.4), (-14, -9, 4, 1.3), (12, -8, 5, 1.3), (22, -5, 3, 1.1)])),
    # 副菜
    "misoshiru": dict(kind=misoshiru),
    "chawanmushi": dict(kind=chawanmushi),
    "wasabi": dict(kind=wasabi),
    "gari": dict(kind=gari),
    "udon": dict(kind=udon),
})


def main():
    import json
    OUT.mkdir(parents=True, exist_ok=True)
    for name, item in ITEMS.items():
        (OUT / f"{name}.svg").write_text(item["kind"](name, item), encoding="utf-8")
    words = json.loads((OUT.parent.parent / "data" / "words.json").read_text(encoding="utf-8"))["words"]
    ids = {w["id"] for w in words}
    print(f"wrote {len(ITEMS)} svg")
    missing, extra = ids - ITEMS.keys(), ITEMS.keys() - ids
    if missing:
        print("题库里有、但还没画的：", sorted(missing))
    if extra:
        print("画了、但题库里没有的：", sorted(extra))


if __name__ == "__main__":
    main()
