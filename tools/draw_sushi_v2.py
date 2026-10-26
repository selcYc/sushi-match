"""第二版寿司插图（样稿）：约 30° 的侧前方视角，鱼片是「垂下来的叶片」。

用法：python tools/draw_sushi_v2.py
输出到 img/sushi-v2/<id>.svg

依据见 docs/illustration-plan.md：
- 视角降到约 30°，看得出鱼片拱在饭团上、两头垂到盘子的样子，饭团的正面也露出一截
- 生鱼片统一用叶片形，按种类调长度、宽度、厚度、下垂程度、尖头
- 每种只放大 1～2 个线索：皮边色带、标志花纹、配料
- 加一条比本色深一档的细描边，白色寿司放在白盘子上也有边界

做法：用一个很简单的 3D 模型再投影到屏幕上。
- 饭团是一个圆角的长方块；鱼片盖在饭团顶上，超出饭团的两头顺势垂到盘子，前后两边也稍微往下包
- 鱼片表面用 (u, v) 描述：u 从 0 到 1 是从左头到右头，v 从 -1 到 1 是从后边缘到前边缘。
  花纹、色带、配料都按 (u, v) 放，会跟着弯曲的表面走
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "img" / "sushi-v2"

VIEW = "0 24 120 70"
ELEV = math.radians(30)  # 视角：从 30° 仰角往下看
# 两贯左右并排、前后错开：后面那贯偏左上，前面那贯偏右下
PAIR = [(44, 61), (75, 72)]
YAW = math.radians(-16)  # 整贯在水平面上转一点，看到的是斜 3/4 面


def f(n):
    return f"{n:.1f}".rstrip("0").rstrip(".")


def poly(points):
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in points) + " Z"


def polyline(points):
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in points)


def sinp(t, p):
    return max(0.0, math.sin(math.pi * t)) ** p


def hull(points):
    """二维凸包（饭团的轮廓）。"""
    pts = sorted(set(points))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


class Piece:
    """一贯握寿司。

    饭团：长 2a、深 2c、高 hr。
    鱼片：L 长度；W 宽度（前后）；T 厚度；taper 右头收尖的程度；wp 两头圆钝（小）还是尖（大）；
    droop 前后两边往下包的程度；endh 两头离盘子的高度；ripple 边缘蓬松起伏（星鳗、鳗鱼）。
    """

    def __init__(self, ox, oy, a=21, c=11.5, hr=15, L=66, W=25.5, T=2.6, taper=0.25, wp=0.42,
                 droop=0.22, endh=0.8, ripple=0.0, seed=0):
        self.ox, self.oy = ox, oy
        self.a, self.c, self.hr = a, c, hr
        self.L, self.W, self.T = L, W, T
        self.taper, self.wp, self.droop, self.endh, self.ripple = taper, wp, droop, endh, ripple
        self.phase = random.Random(seed).uniform(0, 6)

    # 3D → 屏幕
    def proj(self, x, y, z):
        xr = x * math.cos(YAW) - z * math.sin(YAW)
        zr = x * math.sin(YAW) + z * math.cos(YAW)
        return (self.ox + xr, self.oy - y * math.cos(ELEV) + zr * math.sin(ELEV))

    # 鱼片表面上 (u, v) 那一点的 3D 位置
    def xyz(self, u, v):
        x = -self.L / 2 + self.L * u
        w = self.W / 2 * sinp(u, self.wp) * (1 - self.taper * u)
        w *= 1 + self.ripple * math.sin(u * math.pi * 13 + self.phase + (1 if v > 0 else 0))
        z = w * v
        top = self.hr + 1.2
        # 顺着饭团圆滑地垂下去，没有硬转折
        r = min(1.0, abs(x) / (self.L / 2))
        base = self.endh + (top - self.endh) * (1 - r ** 2.6) ** 0.75
        # 前后两边往下包，中间微微鼓起
        y = base * (1 - self.droop * v * v) + 1.4 * (1 - v * v) * (base / top)
        return x, y, z

    def P(self, u, v):
        return self.proj(*self.xyz(u, v))

    def us(self, n=64):
        return [i / n for i in range(n + 1)]

    def top(self):
        return poly([self.P(u, -1) for u in self.us()] + [self.P(u, 1) for u in reversed(self.us())])

    def side(self):
        """鱼片前缘露出来的一条厚度（往下 T）。"""
        front = [self.P(u, 1) for u in self.us()]
        drop = self.T * math.cos(ELEV)
        under = [(x, y + drop * (0.4 + 0.6 * sinp(u, 0.6))) for (x, y), u in zip(front, self.us())]
        return poly(front + under[::-1])

    def band(self, v1, v2, u0=0.0, u1=1.0, n=50):
        us = [u0 + (u1 - u0) * i / n for i in range(n + 1)]
        return poly([self.P(u, v1) for u in us] + [self.P(u, v2) for u in reversed(us)])

    def line(self, v, u0=0.02, u1=0.98, n=40):
        return polyline([self.P(u0 + (u1 - u0) * i / n, v) for i in range(n + 1)])

    def across(self, u, v0=-1, v1=1, n=12):
        return polyline([self.P(u, v0 + (v1 - v0) * i / n) for i in range(n + 1)])

    def rice(self, seed):
        """饭团：圆角长方块投影后的轮廓，边缘一粒粒鼓起来；上半被鱼片盖住，露出正面。"""
        rnd = random.Random(seed)
        pts = []
        for i in range(40):
            t = 2 * math.pi * i / 40
            cx, sz = math.cos(t), math.sin(t)
            x = self.a * math.copysign(abs(cx) ** 0.55, cx)
            z = self.c * math.copysign(abs(sz) ** 0.55, sz)
            for y in (0, self.hr * 0.75, self.hr):
                k = 1 if y < self.hr else 0.8
                pts.append(self.proj(x * k, y, z * k))
        outline = hull([(round(x, 2), round(y, 2)) for x, y in pts])
        # 边缘做出一粒粒米的起伏
        cx = sum(p[0] for p in outline) / len(outline)
        cy = sum(p[1] for p in outline) / len(outline)
        dense = []
        for i in range(len(outline)):
            (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % len(outline)]
            seg = max(1, int(math.hypot(x1 - x0, y1 - y0) / 2.2))
            for k in range(seg):
                dense.append((x0 + (x1 - x0) * k / seg, y0 + (y1 - y0) * k / seg))
        d = f"M{f(dense[0][0])} {f(dense[0][1])}"
        for i in range(len(dense)):
            (x0, y0), (x1, y1) = dense[i], dense[(i + 1) % len(dense)]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            nx, ny = mx - cx, my - cy
            n = math.hypot(nx, ny) or 1
            b = rnd.uniform(0.5, 1.1)
            d += f" Q{f(mx + nx / n * b)} {f(my + ny / n * b)} {f(x1)} {f(y1)}"
        d += " Z"
        out = f'<path d="{d}" fill="url(#rice)" stroke="#c2c8d0" stroke-width="0.6"/>'
        for _ in range(16):
            x, y = self.proj(rnd.uniform(-self.a * 0.85, self.a * 0.85), rnd.uniform(1.5, self.hr * 0.7), self.c)
            out += (f'<path d="M{f(x)} {f(y)} q1.3 {f(rnd.uniform(0.5, 1))} 2.6 0" transform="rotate({rnd.randint(-25, 25)} {f(x)} {f(y)})" '
                    f'fill="none" stroke="#cfd5dc" stroke-width="0.7" stroke-linecap="round"/>')
        return out


# ---------- 公用的部件 ----------

def defs():
    return """  <defs>
    <filter id="soft" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="0.7"/></filter>
    <linearGradient id="plate" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#eef1f4"/></linearGradient>
    <linearGradient id="rice" x1="0" y1="0" x2="0" y2="1"><stop offset="0.3" stop-color="#fdfdfb"/><stop offset="1" stop-color="#dde2e8"/></linearGradient>
  </defs>
"""


def plate():
    return """  <ellipse cx="60" cy="91" rx="50" ry="2.5" fill="#1c2b36" opacity="0.10"/>
  <ellipse cx="60" cy="67.5" rx="57" ry="22" fill="#cfd6dc" stroke="#bcc5cd" stroke-width="0.6"/>
  <ellipse cx="60" cy="65" rx="57" ry="22" fill="url(#plate)" stroke="#c9d0d7" stroke-width="0.6"/>
  <ellipse cx="60" cy="66.2" rx="45" ry="16.5" fill="#eef1f4"/>
  <ellipse cx="60" cy="65.8" rx="44" ry="15.9" fill="#f7f9fa"/>
  <path d="M8 61 C14 50 32 44 54 43" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
"""


def glint(s, u, v, length=0.1, width=1.2, opacity=0.9):
    pts = [s.P(u + length * i / 4, v - 0.08 * i / 4) for i in range(5)]
    return (f'<path d="{polyline(pts)}" fill="none" stroke="#fff" stroke-width="{width}" '
            f'stroke-linecap="round" opacity="{opacity}"/>')


def piece(s, item, seed):
    """一贯：接触阴影、饭团、鱼片侧面、鱼片顶面、花纹、配料。"""
    cid = f"c{seed}"
    sx, sy = s.proj(0, 0, 0)
    out = f'<ellipse cx="{f(sx)}" cy="{f(sy + 2)}" rx="30" ry="5" fill="#1c2b36" opacity="0.12"/>'
    out += item.get("under", lambda s: "")(s)
    out += s.rice(f"{seed}r")
    out += f'<path d="{s.side()}" fill="{item["side"]}" stroke="{item["line"]}" stroke-width="0.7" stroke-linejoin="round"/>'
    out += f'<clipPath id="{cid}"><path d="{s.top()}"/></clipPath>'
    out += f'<path d="{s.top()}" fill="url(#t{seed})"/>'
    out += f'<g clip-path="url(#{cid})">{(item.get("pattern") or (lambda s: ""))(s)}'
    # 两头垂下去的地方暗一点，中间拱起来的地方亮一点
    out += f'<path d="{s.band(-1, 1, 0, 0.16)}" fill="{item["shadow"]}" opacity="0.5" filter="url(#soft)"/>'
    out += f'<path d="{s.band(-1, 1, 0.84, 1)}" fill="{item["shadow"]}" opacity="0.5" filter="url(#soft)"/>'
    out += f'<path d="{s.band(0.55, 1)}" fill="{item["shadow"]}" opacity="0.25" filter="url(#soft)"/>'
    out += f'<path d="{s.line(-0.4, 0.22, 0.78)}" fill="none" stroke="#fff" stroke-width="3" opacity="{item.get("sheen", 0.3)}" filter="url(#soft)"/>'
    out += "</g>"
    out += f'<path d="{s.top()}" fill="none" stroke="{item["line"]}" stroke-width="0.7" stroke-linejoin="round"/>'
    out += item.get("over", lambda s: "")(s)
    grad = (f'<linearGradient id="t{seed}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{item["light"]}"/>'
            f'<stop offset="0.55" stop-color="{item["base"]}"/><stop offset="1" stop-color="{item["shadow"]}"/></linearGradient>')
    return f'  <g><defs>{grad}</defs>{out}</g>\n'


def nigiri(name, item):
    body = ""
    for i, (ox, oy) in enumerate(PAIR):
        s = Piece(ox, oy, seed=f"{name}{i}", **item.get("shape", {}))
        it = dict(item)
        if "pattern_i" in item:  # 每一贯花纹位置不一样（鳗鱼的焦斑）
            it["pattern"] = lambda s, i=i: item["pattern_i"](s, f"{name}{i}")
        body += piece(s, it, f"{name}{i}")
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEW}">\n{defs()}{plate()}{body}</svg>\n'


# ---------- 配料 ----------

def scallions(spots, r=1.9):
    return "".join(
        f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#4f9a3a" stroke="#356e27" stroke-width="0.4"/>'
        f'<circle cx="{f(x - 0.25)}" cy="{f(y - 0.25)}" r="{f(r * 0.65)}" fill="#86c25e"/>'
        f'<circle cx="{f(x - 0.15)}" cy="{f(y - 0.15)}" r="{f(r * 0.3)}" fill="#e6f4d6"/>'
        for x, y in spots)


def momiji(x, y):
    """红叶萝卜泥 + 细葱。"""
    rnd = random.Random("momiji")
    out = (f'<path d="M{f(x - 5)} {f(y)} C{f(x - 6)} {f(y - 3.5)} {f(x - 2)} {f(y - 5.5)} {f(x)} {f(y - 5.5)} '
           f'C{f(x + 3)} {f(y - 5.5)} {f(x + 6)} {f(y - 3.5)} {f(x + 5)} {f(y)} C{f(x + 4)} {f(y + 2)} {f(x - 4)} {f(y + 2)} {f(x - 5)} {f(y)} Z" '
           f'fill="#ef8a5a" stroke="#c9602f" stroke-width="0.5"/>')
    out += f'<path d="M{f(x - 3)} {f(y - 3)} C{f(x - 1)} {f(y - 4.5)} {f(x + 2)} {f(y - 4.5)} {f(x + 3)} {f(y - 3)}" fill="none" stroke="#ffc39c" stroke-width="1" stroke-linecap="round"/>'
    for _ in range(7):
        out += f'<circle cx="{f(x + rnd.uniform(-3.5, 3.5))}" cy="{f(y + rnd.uniform(-4, 0))}" r="0.45" fill="#c9562a"/>'
    return out + scallions([(x + 5.5, y - 3), (x + 7, y + 0.2)], r=1.4)


def ginger_dot(x, y, r=2.6):
    """一小点黄色姜泥。"""
    return (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(r)}" ry="{f(r * 0.7)}" fill="#f0cf5e" stroke="#c9a43a" stroke-width="0.5"/>'
            f'<ellipse cx="{f(x - 0.6)}" cy="{f(y - 0.5)}" rx="{f(r * 0.45)}" ry="{f(r * 0.25)}" fill="#fff3c0"/>')


def shiso(s):
    """比目鱼底下垫的紫苏叶：从鱼片后面露出锯齿状的绿叶边。"""
    pts = []
    n = 22
    for i in range(n + 1):
        u = 0.08 + 0.84 * i / n
        x, y = s.proj(-s.L / 2 + s.L * u, s.hr * 0.6, -(s.c + 3 + 3 * sinp(u, 0.8)))
        pts.append((x, y - (1.6 if i % 2 else 0)))
    x0, y0 = s.proj(-s.L * 0.42, 0.5, 0)
    x1, y1 = s.proj(s.L * 0.42, 0.5, 0)
    leaf = poly([(x0, y0)] + pts + [(x1, y1)])
    vein = polyline([s.proj(-s.L / 2 + s.L * (0.1 + 0.8 * i / 10), s.hr * 0.65, -(s.c + 1.5)) for i in range(11)])
    return (f'<path d="{leaf}" fill="#4f9a3a" stroke="#356e27" stroke-width="0.6" stroke-linejoin="round"/>'
            f'<path d="{vein}" fill="none" stroke="#8cc46a" stroke-width="0.8"/>')


# ---------- 6 个样稿 ----------

def maguro_pattern(s):
    return (f'<path d="{s.line(-0.15, 0.25, 0.75)}" fill="none" stroke="#f06a78" stroke-width="3" opacity="0.5" filter="url(#soft)"/>'
            f'<path d="{s.line(0.35, 0.3, 0.7)}" fill="none" stroke="#e04a5c" stroke-width="2" opacity="0.35" filter="url(#soft)"/>'
            + glint(s, 0.3, -0.55, 0.12, 1.8) + glint(s, 0.47, -0.65, 0.08, 1.5) + glint(s, 0.6, -0.5, 0.1, 1.6))


def hamachi_pattern(s):
    # 油甘鱼：前边缘一条深灰银色的皮，皮上方紧贴一道深红色血合
    return (f'<path d="{s.band(0.3, 0.72)}" fill="#c4505a" opacity="0.85" filter="url(#soft)"/>'
            f'<path d="{s.band(0.7, 1.05)}" fill="#6c7980"/>'
            f'<path d="{s.line(0.76)}" fill="none" stroke="#c7d2d8" stroke-width="0.9" opacity="0.9"/>'
            + glint(s, 0.3, -0.6, 0.1, 1.3) + glint(s, 0.5, -0.7, 0.08, 1.1))


def hirame_pattern(s):
    # 比目鱼：半透明，几道很淡的放射状纹
    out = f'<path d="{s.band(-0.3, 0.6, 0.15, 0.85)}" fill="#dfe4ea" opacity="0.6" filter="url(#soft)"/>'
    for u in (0.3, 0.42, 0.54, 0.66):
        out += f'<path d="{s.across(u, -1, 1)}" fill="none" stroke="#ffffff" stroke-width="0.8" opacity="0.8"/>'
    return out + glint(s, 0.3, -0.6, 0.1, 1.2)


def ika_pattern(s):
    # 鱿鱼：不透明的纯白，细细的刀纹
    out = "".join(f'<path d="{s.across(u, -1, 1)}" fill="none" stroke="#d3dbe4" stroke-width="0.6"/>'
                  for u in [0.12 + 0.045 * i for i in range(17)])
    return out + glint(s, 0.25, -0.6, 0.14, 1.5) + glint(s, 0.55, -0.7, 0.1, 1.3)


def unagi_pattern(s, seed):
    # 鳗鱼：深棕烤鱼片，不规则的焦斑，亮晶晶的酱汁
    rnd = random.Random(seed)
    out = ""
    for _ in range(16):
        u, v = rnd.uniform(0.1, 0.9), rnd.uniform(-0.9, 0.7)
        x, y = s.P(u, v)
        out += (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rnd.uniform(1.5, 4))}" ry="{f(rnd.uniform(0.8, 1.8))}" '
                f'transform="rotate({rnd.randint(-20, 20)} {f(x)} {f(y)})" fill="#2a1207" opacity="0.6" filter="url(#soft)"/>')
    # 酱汁的琥珀色光泽和纵向油脂纹，免得看起来像烤焦的面包
    out += "".join(f'<path d="{s.line(v, 0.08, 0.92)}" fill="none" stroke="#c98545" stroke-width="1" opacity="0.55"/>'
                   for v in (-0.55, -0.15, 0.25))
    out += f'<path d="{s.line(-0.35, 0.15, 0.85)}" fill="none" stroke="#ffcf8f" stroke-width="3" opacity="0.45" filter="url(#soft)"/>'
    return (out + glint(s, 0.2, -0.55, 0.14, 1.6) + glint(s, 0.42, -0.7, 0.1, 1.4)
            + glint(s, 0.62, -0.45, 0.12, 1.5) + glint(s, 0.36, 0.15, 0.08, 1.1, 0.8) + glint(s, 0.7, 0.1, 0.06, 1, 0.7))


def anago_pattern(s):
    # 星鳗：浅琥珀色，细长纵纹，一层薄酱汁的光
    out = "".join(f'<path d="{s.line(v)}" fill="none" stroke="#f5d6a8" stroke-width="0.9" opacity="0.75"/>'
                  for v in (-0.65, -0.35, -0.05, 0.25, 0.55))
    out += f'<path d="{s.band(-0.6, 0.3, 0.2, 0.8)}" fill="#8a4f20" opacity="0.18" filter="url(#soft)"/>'
    return out + glint(s, 0.3, -0.55, 0.1, 1.3) + glint(s, 0.55, -0.6, 0.08, 1.1)


ITEMS = {
    "maguro": dict(light="#e54a5c", base="#c9243a", shadow="#8c1325", side="#9b1a2d", line="#6e0d1c",
                   shape=dict(W=24, T=3), pattern=maguro_pattern, sheen=0.35),
    "hamachi": dict(light="#fff3ec", base="#f4d5c6", shadow="#d6a796", side="#5c686e", line="#a77f72",
                    shape=dict(W=23, T=2.6), pattern=hamachi_pattern),
    "hirame": dict(light="#ffffff", base="#f1f1ee", shadow="#cdd2d6", side="#dde1e4", line="#a9b0b7",
                   shape=dict(W=23, T=1.8, taper=0.3, wp=0.5), pattern=hirame_pattern, sheen=0.5,
                   under=shiso, over=lambda s: momiji(*s.P(0.5, -0.3))),
    "ika": dict(light="#ffffff", base="#fafbfc", shadow="#cbd4de", side="#e0e6ed", line="#97a6b6",
                shape=dict(W=24, T=2.6, taper=0.1, wp=0.25), pattern=ika_pattern, sheen=0.6,
                over=lambda s: ginger_dot(*s.P(0.5, -0.25))),
    "unagi": dict(light="#a86533", base="#73401d", shadow="#3d1d0b", side="#211006", line="#1e0d04",
                  shape=dict(L=62, W=25, T=2.6, taper=0.15, wp=0.32, ripple=0.05), pattern_i=unagi_pattern, sheen=0.25),
    "anago": dict(light="#f1cc93", base="#d6a063", shadow="#a26a35", side="#94602e", line="#7d4e22",
                  shape=dict(L=64, W=25, T=1.8, taper=0.15, wp=0.3, endh=0.4, droop=0.2, ripple=0.06),
                  pattern=anago_pattern, sheen=0.4),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, item in ITEMS.items():
        (OUT / f"{name}.svg").write_text(nigiri(name, item), encoding="utf-8")
    print(f"wrote {len(ITEMS)} svg to {OUT}")


if __name__ == "__main__":
    main()
