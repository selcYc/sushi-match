"""生成寿司插图：约 30° 的侧前方视角，盘子上左右并排两贯。

用法：python tools/draw_sushi.py
输出到 img/sushi/<id>.svg，最后对照题库检查有没有漏画的词。

依据见 docs/illustration-plan.md（第二轮调研：回转寿司店的实物照片 + いらすとや 等插画）：
- 握寿司是鱼片「趴」在饭团上：比饭团长，中间被顶起，两头顺势垂到盘子
- 分辨靠「轮廓 + 皮边色带 + 配料」，每种只放大 1～2 个线索
- 每样东西都有一条比本色深一档的细描边，白色寿司放在白盘子上也有边界

做法：用很简单的 3D 模型再投影到屏幕上（从 30° 仰角看，整贯在水平面上转一点）。
鱼片表面用 (u, v) 描述：u 从 0 到 1 是从左头到右头，v 从 -1 到 1 是从后边缘到前边缘。
花纹、色带、配料都按 (u, v) 放，会跟着弯曲的表面走。
"""

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "img" / "sushi"

VIEW = "0 24 120 70"
ELEV = math.radians(30)  # 从 30° 仰角往下看
COS_E, SIN_E = math.cos(ELEV), math.sin(ELEV)
YAW = math.radians(-16)  # 整贯在水平面上转一点，看到的是斜 3/4 面
# 两贯左右并排、前后错开：后面那贯偏左上，前面那贯偏右下
PAIR = [(44, 61), (75, 72)]


# ---------- 基础 ----------

def f(n):
    return f"{n:.1f}".rstrip("0").rstrip(".")


def poly(points):
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in points) + " Z"


def polyline(points):
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in points)


def sinp(t, p):
    return max(0.0, math.sin(math.pi * t)) ** p


def proj(ox, oy, x, y, z, yaw=YAW):
    """3D → 屏幕。x 左右、y 向上、z 朝向看的人。"""
    xr = x * math.cos(yaw) - z * math.sin(yaw)
    zr = x * math.sin(yaw) + z * math.cos(yaw)
    return (ox + xr, oy - y * COS_E + zr * SIN_E)


def hull(points):
    """二维凸包。"""
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in points))

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


def bumpy(outline, seed, step=2.2, bump=(0.5, 1.1)):
    """把轮廓的边缘做成一粒粒鼓起来（米饭）。"""
    rnd = random.Random(seed)
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    dense = []
    for i in range(len(outline)):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % len(outline)]
        seg = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        dense += [(x0 + (x1 - x0) * k / seg, y0 + (y1 - y0) * k / seg) for k in range(seg)]
    d = f"M{f(dense[0][0])} {f(dense[0][1])}"
    for i in range(len(dense)):
        (x0, y0), (x1, y1) = dense[i], dense[(i + 1) % len(dense)]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        nx, ny = mx - cx, my - cy
        n = math.hypot(nx, ny) or 1
        b = rnd.uniform(*bump)
        d += f" Q{f(mx + nx / n * b)} {f(my + ny / n * b)} {f(x1)} {f(y1)}"
    return d + " Z"


def loaf(ox, oy, a, c, h, yaw=YAW, p=0.55):
    """圆角长方块投影后的轮廓（饭团、豆皮）。"""
    pts = []
    for i in range(40):
        t = 2 * math.pi * i / 40
        cx, sz = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(cx) ** p, cx)
        z = c * math.copysign(abs(sz) ** p, sz)
        for y, k in ((0, 1), (h * 0.75, 1), (h, 0.8)):
            pts.append(proj(ox, oy, x * k, y, z * k, yaw))
    return hull(pts)


def grains(ox, oy, a, c, h, seed, n=16, yaw=YAW):
    """饭团正面几道短弧线，暗示一粒粒的米。"""
    rnd = random.Random(seed)
    out = ""
    for _ in range(n):
        x, y = proj(ox, oy, rnd.uniform(-a * 0.85, a * 0.85), rnd.uniform(1.5, h * 0.7), c, yaw)
        out += (f'<path d="M{f(x)} {f(y)} q1.3 {f(rnd.uniform(0.5, 1))} 2.6 0" transform="rotate({rnd.randint(-25, 25)} {f(x)} {f(y)})" '
                f'fill="none" stroke="#cfd5dc" stroke-width="0.7" stroke-linecap="round"/>')
    return out


def rice(ox, oy, seed, a=21, c=11.5, h=15, yaw=YAW):
    out = f'<path d="{bumpy(loaf(ox, oy, a, c, h, yaw), seed)}" fill="url(#rice)" stroke="#c2c8d0" stroke-width="0.6"/>'
    return out + grains(ox, oy, a, c, h, seed, yaw=yaw)


def contact_shadow(ox, oy, rx=30, ry=5):
    return f'<ellipse cx="{f(ox)}" cy="{f(oy + 2)}" rx="{rx}" ry="{ry}" fill="#1c2b36" opacity="0.12"/>'


DEFS = """  <defs>
    <filter id="soft" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="0.7"/></filter>
    <linearGradient id="plate" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#eef1f4"/></linearGradient>
    <linearGradient id="rice" x1="0" y1="0" x2="0" y2="1"><stop offset="0.3" stop-color="#fdfdfb"/><stop offset="1" stop-color="#dde2e8"/></linearGradient>
    <linearGradient id="nori" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2b3830"/><stop offset="0.35" stop-color="#3d4c43"/><stop offset="1" stop-color="#18201b"/></linearGradient>
    <radialGradient id="roe" cx="0.36" cy="0.32" r="0.72"><stop offset="0" stop-color="#ffc99c"/><stop offset="0.4" stop-color="#f7702e"/><stop offset="0.85" stop-color="#cf3c10"/><stop offset="1" stop-color="#93270a"/></radialGradient>
  </defs>
"""

PLATE = """  <ellipse cx="60" cy="91" rx="50" ry="2.5" fill="#1c2b36" opacity="0.10"/>
  <ellipse cx="60" cy="67.5" rx="57" ry="22" fill="#cfd6dc" stroke="#bcc5cd" stroke-width="0.6"/>
  <ellipse cx="60" cy="65" rx="57" ry="22" fill="url(#plate)" stroke="#c9d0d7" stroke-width="0.6"/>
  <ellipse cx="60" cy="66.2" rx="45" ry="16.5" fill="#eef1f4"/>
  <ellipse cx="60" cy="65.8" rx="44" ry="15.9" fill="#f7f9fa"/>
  <path d="M8 61 C14 50 32 44 54 43" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
"""


def svg(body, extra_defs="", plate=True):
    defs = DEFS.replace("  </defs>\n", extra_defs + "  </defs>\n")
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEW}">\n{defs}{PLATE if plate else ""}{body}</svg>\n'


def glints_at(spots):
    """湿润感：几道白色小笔触，spots 是 (x, y, 长, 粗)。"""
    return "".join(
        f'<path d="M{f(x)} {f(y)} l{f(l)} {f(-l * 0.2)}" stroke="#fff" stroke-width="{f(w)}" stroke-linecap="round" opacity="0.9"/>'
        for x, y, l, w in spots)


# ---------- 鱼片 ----------

class Slice:
    """一片趴在饭团上的鱼片（饭团：长 2a、深 2c、高 hr）。

    L 长度；W 宽度（前后）；T 厚度；taper 右头收尖的程度；wp 两头圆钝（小）还是尖（大）；
    droop 前后两边往下包的程度；crown 中间鼓起多少；endh 两头离盘子的高度；
    ripple / rf 边缘起伏（星鳗、赤贝、章鱼）；zoff 前后偏移（甜虾、蟹腿两条并排）。
    """

    def __init__(self, ox, oy, a=21, c=11.5, hr=15, L=66, W=25.5, T=2.6, taper=0.25, wp=0.42,
                 droop=0.22, crown=1.4, endh=0.8, ripple=0.0, rf=13, zoff=0.0, seed=0):
        self.ox, self.oy, self.a, self.c, self.hr = ox, oy, a, c, hr
        self.L, self.W, self.T = L, W, T
        self.taper, self.wp, self.droop, self.crown, self.endh = taper, wp, droop, crown, endh
        self.ripple, self.rf, self.zoff = ripple, rf, zoff
        self.phase = random.Random(seed).uniform(0, 6)

    def xyz(self, u, v):
        x = -self.L / 2 + self.L * u
        w = self.W / 2 * sinp(u, self.wp) * (1 - self.taper * u)
        w *= 1 + self.ripple * math.sin(u * math.pi * self.rf + self.phase + (1.3 if v > 0 else 0))
        z = w * v + self.zoff
        top = self.hr + 1.2
        # 顺着饭团圆滑地垂下去，没有硬转折
        r = min(1.0, abs(x) / (self.L / 2))
        base = self.endh + (top - self.endh) * (1 - r ** 2.6) ** 0.75
        # 前后两边往下包，中间微微鼓起
        y = base * (1 - self.droop * v * v) + self.crown * (1 - v * v) * (base / top)
        return x, y, z

    def P(self, u, v):
        return proj(self.ox, self.oy, *self.xyz(u, v))

    def us(self, n=44):
        return [i / n for i in range(n + 1)]

    def top(self):
        return poly([self.P(u, -1) for u in self.us()] + [self.P(u, 1) for u in reversed(self.us())])

    def side(self):
        """前缘露出来的一条厚度。"""
        front = [self.P(u, 1) for u in self.us()]
        drop = self.T * COS_E
        under = [(x, y + drop * (0.4 + 0.6 * sinp(u, 0.6))) for (x, y), u in zip(front, self.us())]
        return poly(front + under[::-1])

    def band(self, v1, v2, u0=0.0, u1=1.0, n=30):
        us = [u0 + (u1 - u0) * i / n for i in range(n + 1)]
        return poly([self.P(u, v1) for u in us] + [self.P(u, v2) for u in reversed(us)])

    def line(self, v, u0=0.02, u1=0.98, n=28):
        return polyline([self.P(u0 + (u1 - u0) * i / n, v) for i in range(n + 1)])

    def across(self, u, v0=-1, v1=1, n=12, wobble=0.0, k=0):
        return polyline([self.P(u + wobble * math.sin((v0 + (v1 - v0) * i / n) * 5 + k), v0 + (v1 - v0) * i / n)
                         for i in range(n + 1)])

    def glint(self, u, v, length=0.1, width=1.3, opacity=0.9):
        pts = [self.P(u + length * i / 4, v - 0.08 * i / 4) for i in range(5)]
        return (f'<path d="{polyline(pts)}" fill="none" stroke="#fff" stroke-width="{width}" '
                f'stroke-linecap="round" opacity="{opacity}"/>')


def slice_layers(s, item, sid):
    """一片鱼的侧面、顶面、花纹和描边。"""
    cid = f"c{sid}"
    grad = (f'<linearGradient id="t{sid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{item["light"]}"/>'
            f'<stop offset="0.55" stop-color="{item["base"]}"/><stop offset="1" stop-color="{item["shadow"]}"/></linearGradient>')
    out = f'<defs>{grad}<clipPath id="{cid}"><path d="{s.top()}"/></clipPath></defs>'
    out += f'<path d="{s.side()}" fill="{item["side"]}" stroke="{item["line"]}" stroke-width="0.7" stroke-linejoin="round"/>'
    out += f'<path d="{s.top()}" fill="url(#t{sid})"/>'
    out += f'<g clip-path="url(#{cid})">{pattern_of(item, s, sid)}'
    # 两头垂下去的地方暗一点，前缘往下包的地方暗一点，中间拱起来的地方亮一点
    out += f'<path d="{s.band(-1, 1, 0, 0.16)}" fill="{item["shadow"]}" opacity="0.5" filter="url(#soft)"/>'
    out += f'<path d="{s.band(-1, 1, 0.84, 1)}" fill="{item["shadow"]}" opacity="0.5" filter="url(#soft)"/>'
    out += f'<path d="{s.band(0.55, 1)}" fill="{item["shadow"]}" opacity="0.25" filter="url(#soft)"/>'
    out += f'<path d="{s.line(-0.4, 0.22, 0.78)}" fill="none" stroke="#fff" stroke-width="3" opacity="{item.get("sheen", 0.3)}" filter="url(#soft)"/>'
    out += "</g>"
    out += f'<path d="{s.top()}" fill="none" stroke="{item["line"]}" stroke-width="0.7" stroke-linejoin="round"/>'
    return out


def pattern_of(item, s, sid):
    p = item.get("pattern")
    if p is None:
        return ""
    return p(s, sid) if item.get("seeded") else p(s)


def nigiri(name, item):
    """握寿司：每贯一个饭团，上面盖一片（或并排几条）鱼。"""
    body = ""
    for i, (ox, oy) in enumerate(PAIR):
        sid = f"{name}{i}"
        shape = item.get("shape", {})
        strips = item.get("strips", [0.0])  # 甜虾、蟹腿：前后并排几条
        slices = [Slice(ox, oy, seed=f"{sid}{k}", zoff=z, **shape) for k, z in enumerate(strips)]
        out = contact_shadow(ox, oy)
        out += "".join(item.get("under", lambda s: "")(s) for s in slices)
        out += rice(ox, oy, f"{sid}r")
        for k, s in enumerate(slices):
            out += slice_layers(s, item, f"{sid}{k}")
        out += "".join(item.get("over", lambda s: "")(s) for s in slices[:1])
        body += f"  <g>{out}</g>\n"
    return svg(body, item.get("defs", ""))


# ---------- 配料 ----------

def scallions(spots, r=1.9):
    return "".join(
        f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#4f9a3a" stroke="#356e27" stroke-width="0.4"/>'
        f'<circle cx="{f(x - 0.25)}" cy="{f(y - 0.25)}" r="{f(r * 0.65)}" fill="#86c25e"/>'
        f'<circle cx="{f(x - 0.15)}" cy="{f(y - 0.15)}" r="{f(r * 0.3)}" fill="#e6f4d6"/>'
        for x, y in spots)


def ginger_dot(x, y, r=3):
    """一小点黄色姜泥（竹荚鱼、沙丁鱼、鱿鱼、白子……）。"""
    return (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(r)}" ry="{f(r * 0.7)}" fill="#f0cf5e" stroke="#c9a43a" stroke-width="0.5"/>'
            f'<ellipse cx="{f(x - 0.6)}" cy="{f(y - 0.5)}" rx="{f(r * 0.45)}" ry="{f(r * 0.25)}" fill="#fff3c0"/>')


def ginger_scallion(x, y):
    """姜泥 + 葱花一小撮（竹荚鱼、鲣鱼）。"""
    return ginger_dot(x, y, 4) + scallions([(x - 4, y - 2), (x + 3.4, y - 2.8), (x + 0.2, y + 0.8), (x - 1.2, y - 3.6)], r=2.2)


def momiji(x, y):
    """红叶萝卜泥 + 细葱（比目鱼）。"""
    rnd = random.Random("momiji")
    out = (f'<path d="M{f(x - 5)} {f(y)} C{f(x - 6)} {f(y - 3.5)} {f(x - 2)} {f(y - 5.5)} {f(x)} {f(y - 5.5)} '
           f'C{f(x + 3)} {f(y - 5.5)} {f(x + 6)} {f(y - 3.5)} {f(x + 5)} {f(y)} C{f(x + 4)} {f(y + 2)} {f(x - 4)} {f(y + 2)} {f(x - 5)} {f(y)} Z" '
           f'fill="#ef8a5a" stroke="#c9602f" stroke-width="0.5"/>')
    out += f'<path d="M{f(x - 3)} {f(y - 3)} C{f(x - 1)} {f(y - 4.5)} {f(x + 2)} {f(y - 4.5)} {f(x + 3)} {f(y - 3)}" fill="none" stroke="#ffc39c" stroke-width="1" stroke-linecap="round"/>'
    for _ in range(7):
        out += f'<circle cx="{f(x + rnd.uniform(-3.5, 3.5))}" cy="{f(y + rnd.uniform(-4, 0))}" r="0.45" fill="#c9562a"/>'
    return out + scallions([(x + 5.5, y - 3), (x + 7, y + 0.2)], r=1.4)


def onion_slivers(x, y):
    """洋葱丝 + 葱花（炙烤长鳍金枪鱼）。"""
    out = ""
    for dx, dy, w in ((-6, 0, 8), (-1, -2.5, 9), (2, 0.5, 7)):
        d = f"M{f(x + dx)} {f(y + dy)} q{f(w / 2)} -3 {f(w)} 0"
        out += f'<path d="{d}" fill="none" stroke="#d9d2c0" stroke-width="2.4" stroke-linecap="round"/>'
        out += f'<path d="{d}" fill="none" stroke="#fffdf6" stroke-width="1.4" stroke-linecap="round"/>'
    return out + scallions([(x - 2, y - 3.5), (x + 5, y - 2)], r=1.5)


def shiso(s):
    """比目鱼底下垫的紫苏叶：从鱼片后面露出锯齿状的绿叶边。"""
    pts = []
    n = 22
    for i in range(n + 1):
        u = 0.08 + 0.84 * i / n
        x, y = proj(s.ox, s.oy, -s.L / 2 + s.L * u, s.hr * 0.6, -(s.c + 3 + 3 * sinp(u, 0.8)))
        pts.append((x, y - (1.6 if i % 2 else 0)))
    x0, y0 = proj(s.ox, s.oy, -s.L * 0.42, 0.5, 0)
    x1, y1 = proj(s.ox, s.oy, s.L * 0.42, 0.5, 0)
    vein = polyline([proj(s.ox, s.oy, -s.L / 2 + s.L * (0.1 + 0.8 * i / 10), s.hr * 0.65, -(s.c + 1.5)) for i in range(11)])
    return (f'<path d="{poly([(x0, y0)] + pts + [(x1, y1)])}" fill="#4f9a3a" stroke="#356e27" stroke-width="0.6" stroke-linejoin="round"/>'
            f'<path d="{vein}" fill="none" stroke="#8cc46a" stroke-width="0.8"/>')


def tail(s, color="#e2452f", dark="#8f1f14", size=1.0):
    """虾尾：从鱼片右头伸出来的扇形。"""
    x, y = s.P(0.97, 0)
    k = size
    fan = [(x, y), (x + 9 * k, y - 9 * k), (x + 12 * k, y - 4 * k), (x + 13 * k, y + 1 * k), (x + 10 * k, y + 5 * k), (x + 2 * k, y + 2 * k)]
    return (f'<path d="{poly(fan)}" fill="{color}" stroke="{dark}" stroke-width="0.6" stroke-linejoin="round"/>'
            f'<path d="M{f(x + 2 * k)} {f(y)} L{f(x + 10 * k)} {f(y - 7 * k)} M{f(x + 2 * k)} {f(y + 0.5 * k)} L{f(x + 12 * k)} {f(y - 1 * k)} '
            f'M{f(x + 2 * k)} {f(y + 1 * k)} L{f(x + 11 * k)} {f(y + 4 * k)}" stroke="{dark}" stroke-width="0.6" opacity="0.7"/>')


# ---------- 各种鱼片的花纹 ----------

def gl(*spots):
    """在鱼片表面 (u, v) 放几道高光。"""
    return lambda s: "".join(s.glint(*sp) for sp in spots)


STD_GL = gl((0.3, -0.55, 0.11, 1.5), (0.48, -0.65, 0.08, 1.3), (0.62, -0.5, 0.09, 1.3))


def combine(*parts):
    return lambda s: "".join(p(s) for p in parts)


def soft_band(v1, v2, color, opacity=0.85, u0=0.0, u1=1.0):
    return lambda s: f'<path d="{s.band(v1, v2, u0, u1)}" fill="{color}" opacity="{opacity}" filter="url(#soft)"/>'


def hard_band(v1, v2, color, opacity=1.0, u0=0.0, u1=1.0):
    return lambda s: f'<path d="{s.band(v1, v2, u0, u1)}" fill="{color}" opacity="{opacity}"/>'


def lines_along(vs, color, width=0.9, opacity=0.75):
    return lambda s: "".join(f'<path d="{s.line(v)}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}"/>' for v in vs)


def lines_across(us, color, width=0.9, opacity=0.75, v0=-1, v1=1, wobble=0.0, slant=0.0):
    def draw(s):
        out = ""
        for k, u in enumerate(us):
            pts = []
            for i in range(13):
                v = v0 + (v1 - v0) * i / 12
                pts.append(s.P(u + slant * v + wobble * math.sin(v * 5 + k), v))
            out += f'<path d="{polyline(pts)}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}"/>'
        return out
    return draw


def dots_along(v, us, color, r=1.0):
    return lambda s: "".join(f'<circle cx="{f(s.P(u, v)[0])}" cy="{f(s.P(u, v)[1])}" r="{r}" fill="{color}"/>' for u in us)


def marble(seed, color, n=40, width=1.1):
    """大腹的白色脂肪网。"""
    def draw(s):
        rnd = random.Random(seed)
        out = ""
        for _ in range(n):
            u, v = rnd.uniform(0.08, 0.92), rnd.uniform(-0.95, 0.95)
            du, dv = rnd.uniform(0.03, 0.07), rnd.uniform(-0.4, 0.4)
            pts = [s.P(u + du * t, v + dv * t + 0.1 * math.sin(t * 3)) for t in (0, 0.33, 0.66, 1)]
            out += f'<path d="{polyline(pts)}" fill="none" stroke="{color}" stroke-width="{width}" opacity="0.85" stroke-linecap="round"/>'
        return out
    return draw


def blotches(seed, color, n=16, v_range=(-0.9, 0.7), size=(1.5, 4), opacity=0.6):
    def draw(s):
        rnd = random.Random(seed)
        out = ""
        for _ in range(n):
            x, y = s.P(rnd.uniform(0.1, 0.9), rnd.uniform(*v_range))
            out += (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rnd.uniform(*size))}" ry="{f(rnd.uniform(size[0] * 0.5, size[1] * 0.45))}" '
                    f'transform="rotate({rnd.randint(-20, 20)} {f(x)} {f(y)})" fill="{color}" opacity="{opacity}" filter="url(#soft)"/>')
        return out
    return draw


def mackerel_stripes(s):
    """鲭鱼背上粗黑的斑马波浪纹。"""
    out = ""
    for k in range(13):
        u = 0.1 + 0.064 * k
        pts = [s.P(u + 0.018 * math.sin(v * 7 + k * 1.7), v) for v in [-1 + 1.45 * i / 10 for i in range(11)]]
        out += f'<path d="{polyline(pts)}" fill="none" stroke="#12283a" stroke-width="{1.6 + 0.8 * (k % 2)}" opacity="0.95" stroke-linecap="round"/>'
    return out


def suckers(s):
    """章鱼前缘的一排吸盘。"""
    out = ""
    for k in range(9):
        u = 0.14 + 0.09 * k
        x, y = s.P(u, 0.82)
        out += f'<circle cx="{f(x)}" cy="{f(y)}" r="1.6" fill="#f2c4d0" stroke="#b9607d" stroke-width="0.4"/><circle cx="{f(x)}" cy="{f(y)}" r="0.7" fill="#d48aa2"/>'
    return out


def inner_rim(color, width=4, opacity=0.5):
    return lambda s: f'<path d="{s.top()}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}" filter="url(#soft)"/>'


def slit(u0=0.3, u1=0.75, v=0.0):
    return lambda s: (f'<path d="{s.line(v, u0, u1)}" fill="none" stroke="#ffffff" stroke-width="1.1" opacity="0.9"/>'
                      f'<path d="{s.line(v + 0.08, u0, u1)}" fill="none" stroke="#000" stroke-width="0.5" opacity="0.18"/>')


def over_at(u, v, fn):
    return lambda s: fn(*s.P(u, v))


def unagi_pattern(s, seed):
    return (blotches(seed, "#2a1207")(s)
            + lines_along((-0.55, -0.15, 0.25), "#c98545", 1, 0.55)(s)
            + f'<path d="{s.line(-0.35, 0.15, 0.85)}" fill="none" stroke="#ffcf8f" stroke-width="3" opacity="0.45" filter="url(#soft)"/>'
            + gl((0.2, -0.55, 0.14, 1.6), (0.42, -0.7, 0.1, 1.4), (0.62, -0.45, 0.12, 1.5), (0.36, 0.15, 0.08, 1.1), (0.7, 0.1, 0.06, 1.0))(s))


# ---------- 方块（玉子） ----------

def box_faces(ox, oy, x0, x1, y0, y1, z0, z1, yaw=YAW):
    """返回看得见的面（按从后到前的顺序）：[(名字, 顶点)]。"""
    P = lambda x, y, z: proj(ox, oy, x, y, z, yaw)
    faces = {
        "front": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
        "back": ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
        "left": ([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], (-1, 0, 0)),
        "right": ([(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)], (1, 0, 0)),
        "top": ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)),
    }
    out = []
    for name, (corners, (nx, ny, nz)) in faces.items():
        # 法线转到屏幕方向后，朝着看的人才画
        nzr = nx * math.sin(yaw) + nz * math.cos(yaw)
        if nzr * SIN_E + ny * COS_E > 0.02:
            out.append((name, [P(*c) for c in corners]))
    order = {"back": 0, "left": 1, "right": 1, "front": 2, "top": 3}
    return sorted(out, key=lambda t: order[t[0]])


def tamago(name, item):
    body = ""
    for i, (ox, oy) in enumerate(PAIR):
        out = contact_shadow(ox, oy) + rice(ox, oy, f"{name}{i}r")
        x0, x1, z0, z1, y0, y1 = -25, 25, -11, 11, 14, 23
        colors = {"top": "#f8d755", "front": "#ebb935", "left": "#e2a92b", "right": "#e2a92b", "back": "#e2a92b"}
        for face, pts in box_faces(ox, oy, x0, x1, y0, y1, z0, z1):
            out += f'<path d="{poly(pts)}" fill="{colors[face]}" stroke="#b98318" stroke-width="0.7" stroke-linejoin="round"/>'
            if face == "front":  # 侧面能看到一层层卷起来的纹
                for yy in (16.5, 19, 21.5):
                    a, b = proj(ox, oy, x0 + 1, yy, z1), proj(ox, oy, x1 - 1, yy, z1)
                    out += f'<path d="M{f(a[0])} {f(a[1])} L{f(b[0])} {f(b[1])}" stroke="#c9901f" stroke-width="0.6" opacity="0.8"/>'
            if face == "top":
                for sx, sz in ((-18, -4), (-10, 5), (12, -6), (19, 4)):
                    cx, cy = proj(ox, oy, sx, y1, sz)
                    out += f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="3" ry="1.1" fill="#d99a35" opacity="0.4"/>'
                a, b = proj(ox, oy, -22, y1, -8), proj(ox, oy, -6, y1, -8)
                out += f'<path d="M{f(a[0])} {f(a[1])} L{f(b[0])} {f(b[1])}" stroke="#fff6c8" stroke-width="1.6" stroke-linecap="round" opacity="0.9"/>'
        # 海苔带：横跨顶面，顺着正面垂下来，一直包到饭团底
        bx0, bx1 = -4, 4
        band = [(bx0, y1, z0), (bx1, y1, z0), (bx1, y1, z1), (bx0, y1, z1)]
        out += f'<path d="{poly([proj(ox, oy, *p) for p in band])}" fill="#2b3a31" stroke="#141b17" stroke-width="0.6"/>'
        front = [(bx0, y1, z1), (bx1, y1, z1), (bx1, 0, z1 - 1), (bx0, 0, z1 - 1)]
        out += f'<path d="{poly([proj(ox, oy, *p) for p in front])}" fill="#1d2822" stroke="#141b17" stroke-width="0.6"/>'
        body += f"  <g>{out}</g>\n"
    return svg(body)


# ---------- 军舰卷 ----------

GA, GC, GH = 17.5, 10.5, 15  # 军舰：海苔围成的椭圆筒，长 2*GA、深 2*GC、高 GH


def ellipse_pts(ox, oy, a, c, y, t0=0, t1=2 * math.pi, n=40):
    return [proj(ox, oy, a * math.cos(t0 + (t1 - t0) * i / n), y, c * math.sin(t0 + (t1 - t0) * i / n), 0) for i in range(n + 1)]


def gunkan(name, item):
    body = ""
    for i, (ox, oy) in enumerate(PAIR):
        sid = f"{name}{i}"
        rnd = random.Random(sid)
        out = contact_shadow(ox, oy, 24, 4.5)
        out += item.get("behind", lambda ox, oy: "")(ox, oy)
        # 后半圈海苔的内侧 + 料
        out += f'<path d="{poly(ellipse_pts(ox, oy, GA, GC, GH))}" fill="#18201b" stroke="#0f1511" stroke-width="0.6"/>'
        out += f'<path d="{poly(ellipse_pts(ox, oy, GA - 1.6, GC - 1.6, GH - 1))}" fill="{item["base"]}"/>'
        out += item["filling"](ox, oy, rnd)
        # 前半圈海苔：挡住料的前缘
        front = ellipse_pts(ox, oy, GA, GC, GH, 0, math.pi) + ellipse_pts(ox, oy, GA, GC, 0, math.pi, 0)
        out += f'<path d="{poly(front)}" fill="url(#nori)" stroke="#0f1511" stroke-width="0.6" stroke-linejoin="round"/>'
        for k in range(3):
            pts = ellipse_pts(ox, oy, GA + 0.1, GC + 0.1, GH * (0.3 + 0.22 * k) + rnd.uniform(-1, 1), 0.3, math.pi - 0.3, 16)
            out += f'<path d="{polyline(pts)}" fill="none" stroke="#4d5f53" stroke-width="0.6" opacity="0.7"/>'
        hx = ellipse_pts(ox, oy, GA, GC, GH * 0.8, math.pi * 0.62, math.pi * 0.75, 4)
        out += f'<path d="{polyline(hx + [(x, y + 8) for x, y in reversed(hx)])}" fill="#ffffff" opacity="0.12"/>'
        body += f"  <g>{out}</g>\n"
    return svg(body, item.get("defs", ""))


def scatter(ox, oy, rnd, n, a=GA - 2.5, c=GC - 2.5, base=GH - 1, dome=3.0):
    """在军舰的料面上均匀撒点，按从后到前排好（后面的先画）。"""
    pts = []
    for _ in range(n):
        t, r = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random())
        x, z = a * r * math.cos(t), c * r * math.sin(t)
        y = base + dome * (1 - r * r)
        pts.append((z, proj(ox, oy, x, y, z, 0)))
    return [p for _, p in sorted(pts)]


def cucumbers(ox, oy):
    """军舰后面插着的两片黄瓜（藏寿司的做法）。"""
    out = ""
    for dx, rot in ((-7, -14), (2, 8)):
        x, y = proj(ox, oy, dx, GH + 1, -GC + 2, 0)
        out += (f'<g transform="translate({f(x)} {f(y)}) rotate({rot})">'
                '<path d="M-7 0 A7 7.5 0 0 1 7 0 Z" fill="#2f6e2a" stroke="#1f4d1b" stroke-width="0.5"/>'
                '<path d="M-5.8 0 A5.8 6.2 0 0 1 5.8 0 Z" fill="#cfe8a6"/>'
                '<path d="M-3.8 0 A3.8 4 0 0 1 3.8 0 Z" fill="#e4f2c8"/>'
                '<g fill="#f6fbea"><ellipse cx="-1.8" cy="-1.6" rx="0.5" ry="0.9"/><ellipse cx="0" cy="-2.3" rx="0.5" ry="0.9"/><ellipse cx="1.8" cy="-1.6" rx="0.5" ry="0.9"/></g></g>')
    return out


def ikura_fill(ox, oy, rnd):
    out = ""
    for x, y in scatter(ox, oy, rnd, 24):
        out += (f'<circle cx="{f(x)}" cy="{f(y)}" r="2.7" fill="url(#roe)" stroke="#8a2408" stroke-width="0.4"/>'
                f'<circle cx="{f(x + 0.6)}" cy="{f(y + 0.7)}" r="0.9" fill="#e0581f" opacity="0.8"/>'
                f'<circle cx="{f(x - 0.9)}" cy="{f(y - 1)}" r="0.7" fill="#fff"/>')
    return out


def uni_fill(ox, oy, rnd):
    out = ""
    for x, y in scatter(ox, oy, rnd, 9, dome=2.5):
        rot = rnd.randint(-30, 30)
        out += (f'<g transform="translate({f(x)} {f(y)}) rotate({rot})"><ellipse rx="6" ry="2.6" fill="url(#uni)" stroke="#b9650f" stroke-width="0.5"/>'
                '<path d="M-4 -1 C-1.5 -2 1.5 -2 4 -1" fill="none" stroke="#ffe3a0" stroke-width="0.8" stroke-linecap="round"/></g>')
    for x, y in scatter(ox, oy, rnd, 30, dome=3):
        out += f'<circle cx="{f(x)}" cy="{f(y)}" r="0.4" fill="#ffd98a" opacity="0.8"/>'
    return out


def tobikko_fill(ox, oy, rnd):
    out = ""
    for x, y in scatter(ox, oy, rnd, 110, dome=2.5):
        out += f'<circle cx="{f(x)}" cy="{f(y)}" r="1.15" fill="#ff8a2a" stroke="#d2600f" stroke-width="0.25"/><circle cx="{f(x - 0.4)}" cy="{f(y - 0.4)}" r="0.35" fill="#fff1d2"/>'
    return out


def kanimiso_fill(ox, oy, rnd):
    x, y = proj(ox, oy, 0, GH + 0.5, 0, 0)
    out = f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{GA - 2}" ry="{f((GC - 2) * SIN_E + 1)}" fill="#86814b"/>'
    out += (f'<path d="M{f(x - 10)} {f(y - 1)} C{f(x - 5)} {f(y - 3)} {f(x + 2)} {f(y - 2)} {f(x + 8)} {f(y - 1)}" fill="none" stroke="#b5ab68" stroke-width="2.5" opacity="0.8" filter="url(#soft)"/>'
            f'<path d="M{f(x - 12)} {f(y + 2)} C{f(x - 5)} {f(y + 1)} {f(x + 3)} {f(y + 3)} {f(x + 12)} {f(y + 1.5)}" fill="none" stroke="#5d5930" stroke-width="2" opacity="0.7" filter="url(#soft)"/>')
    for px, py in scatter(ox, oy, rnd, 8, dome=1.5):
        out += f'<circle cx="{f(px)}" cy="{f(py)}" r="0.7" fill="#c96a3a" opacity="0.7"/>'
    return out + glints_at([(x - 8, y - 2, 4, 1.1), (x + 3, y - 2.5, 3, 1)])


def shirasu_fill(ox, oy, rnd):
    out = ""
    for x, y in scatter(ox, oy, rnd, 34, dome=3):
        rot = rnd.randint(0, 180)
        out += (f'<g transform="translate({f(x)} {f(y)}) rotate({rot})">'
                '<path d="M-2.2 0 Q0 -1.2 2.2 0" fill="none" stroke="#c9c3b2" stroke-width="1.8"/>'
                '<path d="M-2.2 0 Q0 -1.2 2.2 0" fill="none" stroke="#fdfbf3" stroke-width="1.1"/>'
                '<circle cx="-2" cy="-0.1" r="0.4" fill="#2b2b2b"/></g>')
    x, y = proj(ox, oy, 0, GH + 3, 0, 0)
    return out + ginger_dot(x, y - 1, 2.6)


def negitoro_fill(ox, oy, rnd):
    x, y = proj(ox, oy, 0, GH + 0.5, 0, 0)
    out = f'<ellipse cx="{f(x)}" cy="{f(y - 1)}" rx="{GA - 2}" ry="{f((GC - 2) * SIN_E + 2)}" fill="#ea8592"/>'
    for px, py in scatter(ox, oy, rnd, 26, dome=3):
        out += f'<circle cx="{f(px)}" cy="{f(py)}" r="{f(rnd.uniform(0.9, 1.7))}" fill="{rnd.choice(["#f6a7b1", "#d9677a"])}" opacity="0.8"/>'
    return out + scallions([(p[0], p[1] - 1.5) for p in scatter(ox, oy, rnd, 7, dome=4)], r=1.8)


# ---------- 卷物 ----------

def maki(name, item):
    r, h = 12, 15
    body = ""
    for i, (ox, oy) in enumerate([(86, 55), (60, 62), (34, 69)]):
        rnd = random.Random(f"{name}{i}")
        out = contact_shadow(ox, oy, 15, 3.5)
        side = ellipse_pts(ox, oy, r, r, h, 0, math.pi) + ellipse_pts(ox, oy, r, r, 0, math.pi, 0)
        out += f'<path d="{poly(side)}" fill="url(#nori)" stroke="#0f1511" stroke-width="0.6" stroke-linejoin="round"/>'
        hx = ellipse_pts(ox, oy, r, r, h * 0.85, math.pi * 0.62, math.pi * 0.74, 4)
        out += f'<path d="{polyline(hx + [(x, y + 8) for x, y in reversed(hx)])}" fill="#ffffff" opacity="0.14"/>'
        out += f'<path d="{poly(ellipse_pts(ox, oy, r, r, h))}" fill="#1d2822" stroke="#0f1511" stroke-width="0.6"/>'
        rice_top = bumpy(ellipse_pts(ox, oy, r - 1.6, r - 1.6, h, n=30)[:-1], f"{name}{i}", step=1.6, bump=(0.2, 0.5))
        out += f'<path d="{rice_top}" fill="#fbfbf8" stroke="#c2c8d0" stroke-width="0.5"/>'
        for _ in range(6):
            t, rr = rnd.uniform(0, 2 * math.pi), rnd.uniform(4, 7)
            x, y = proj(ox, oy, rr * math.cos(t), h, rr * math.sin(t), 0)
            out += f'<path d="M{f(x)} {f(y)} q1 0.6 2 0" fill="none" stroke="#cfd5dc" stroke-width="0.6"/>'
        # 芯是区分几种卷物的唯一线索，放大 1.5 倍
        cx, cy = proj(ox, oy, 0, h, 0, 0)
        out += f'<g transform="translate({f(cx)} {f(cy)}) scale(1.5) translate({f(-cx)} {f(-cy)})">{item["core"](ox, oy, h, rnd)}</g>'
        body += f"  <g>{out}</g>\n"
    return svg(body)


def core_rect(w, d, fill, edge, top=None):
    """卷物正中的芯：一块方的（俯视看压成扁的）。"""
    def draw(ox, oy, h, rnd):
        pts = [proj(ox, oy, x, h + 0.2, z, 0) for x, z in ((-w, -d), (w, -d), (w, d), (-w, d))]
        out = f'<path d="{poly(pts)}" fill="{fill}" stroke="{edge}" stroke-width="0.6" stroke-linejoin="round"/>'
        if top:
            a, b = proj(ox, oy, -w + 0.6, h + 0.2, -d + 0.8, 0), proj(ox, oy, w - 0.6, h + 0.2, -d + 0.8, 0)
            out += f'<path d="M{f(a[0])} {f(a[1])} L{f(b[0])} {f(b[1])}" stroke="{top}" stroke-width="1.2" stroke-linecap="round"/>'
        return out
    return draw


def core_cucumber(ox, oy, h, rnd):
    out = ""
    for dx, dz in ((-2.6, -1.2), (2.4, -0.8), (0, 2)):
        pts = [proj(ox, oy, dx + x, h + 0.2, dz + z, 0) for x, z in ((-2.2, -1.5), (2.2, -1.5), (2.2, 1.5), (-2.2, 1.5))]
        out += f'<path d="{poly(pts)}" fill="#c5e397" stroke="#2f6e2a" stroke-width="0.9" stroke-linejoin="round"/>'
    return out


def core_natto(ox, oy, h, rnd):
    out = ""
    for _ in range(7):
        x, y = proj(ox, oy, rnd.uniform(-3.5, 3.5), h + 0.5, rnd.uniform(-3, 3), 0)
        out += f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="1.6" ry="1.1" fill="#b98144" stroke="#8a5a28" stroke-width="0.3"/><ellipse cx="{f(x - 0.4)}" cy="{f(y - 0.4)}" rx="0.6" ry="0.35" fill="#e6bd80"/>'
    x, y = proj(ox, oy, 0, h + 0.6, 0, 0)
    return out + f'<path d="M{f(x - 3)} {f(y - 1)} C{f(x - 1)} {f(y + 1)} {f(x + 1)} {f(y - 1.5)} {f(x + 3)} {f(y + 0.8)}" fill="none" stroke="#fff8ea" stroke-width="0.4" opacity="0.9"/>'


def core_kanpyo(ox, oy, h, rnd):
    out = ""
    for dz, c in ((-1.6, "#8a5428"), (1.2, "#a86a35")):
        pts = [proj(ox, oy, x, h + 0.2, dz + z, 0) for x, z in ((-4, -1.3), (4, -1.3), (4, 1.3), (-4, 1.3))]
        out += f'<path d="{poly(pts)}" fill="{c}" stroke="#5e3614" stroke-width="0.5" stroke-linejoin="round"/>'
    return out


# ---------- 豆皮寿司 ----------

def inari(name, item):
    body = ""
    for i, (ox, oy) in enumerate(PAIR):
        rnd = random.Random(f"{name}{i}")
        out = contact_shadow(ox, oy)
        outline = loaf(ox, oy, 22, 12, 13, p=0.5)
        out += f'<path d="{bumpy(outline, f"{name}{i}", step=4, bump=(0.1, 0.4))}" fill="url(#inari)" stroke="#8f561c" stroke-width="0.7"/>'
        # 顶面亮一点
        top = [proj(ox, oy, 18 * math.cos(t), 13, 9 * math.sin(t)) for t in [2 * math.pi * k / 30 for k in range(30)]]
        out += f'<path d="{poly(top)}" fill="#f0c27e" opacity="0.6" filter="url(#soft)"/>'
        for _ in range(28):
            x, y = proj(ox, oy, rnd.uniform(-19, 19), rnd.uniform(3, 13), rnd.uniform(-10, 12))
            out += f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rnd.uniform(0.4, 0.9))}" fill="#a8651f" opacity="0.5"/>'
        for _ in range(7):  # 几粒芝麻
            x, y = proj(ox, oy, rnd.uniform(-14, 14), 13.2, rnd.uniform(-7, 7))
            out += f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="0.9" ry="0.45" transform="rotate({rnd.randint(-40, 40)} {f(x)} {f(y)})" fill="{rnd.choice(["#2b2b2b", "#fff4dc"])}"/>'
        a, b = proj(ox, oy, -16, 12, -8), proj(ox, oy, 6, 13, -9)
        out += glints_at([(a[0], a[1], 6, 1.3), (b[0], b[1], 4, 1.1)])
        body += f"  <g>{out}</g>\n"
    defs = '    <linearGradient id="inari" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9b56a"/><stop offset="0.6" stop-color="#d4934a"/><stop offset="1" stop-color="#b8762f"/></linearGradient>\n'
    return svg(body, defs)


# ---------- 副菜：碗、杯子、小碟 ----------

def bowl(defs, outer, rim, soup, contents, band=""):
    body = f"""  <g transform="translate(0 4)">
  <ellipse cx="60" cy="87" rx="42" ry="4" fill="#1c2b36" opacity="0.12"/>
  <ellipse cx="60" cy="80" rx="18" ry="4.5" fill="#1c2b36" opacity="0.25"/>
  <path d="M14 40 C16 64 36 81 60 81 C84 81 104 64 106 40 Z" fill="{outer}" stroke="#1c1416" stroke-width="0.7"/>
  {band}
  <path d="M22 52 C28 66 40 74 52 76" fill="none" stroke="#fff" stroke-width="2.4" opacity="0.25" stroke-linecap="round"/>
  <ellipse cx="60" cy="40" rx="46" ry="17.5" fill="{rim}" stroke="#1c1416" stroke-width="0.7"/>
  <ellipse cx="60" cy="41.2" rx="41.5" ry="15" fill="{soup}"/>
  {contents}
  </g>
"""
    return svg(body, defs, plate=False)


def misoshiru(name, item):
    c = '<path d="M30 40 C40 34 56 36 64 40 C72 44 84 42 90 38" fill="none" stroke="#e2b27a" stroke-width="6" opacity="0.5" filter="url(#soft)"/>'
    for x, y, r in ((44, 38, -8), (62, 45, 12), (76, 37, 4)):  # 豆腐
        c += (f'<g transform="translate({x} {y}) rotate({r})"><rect x="-4.5" y="-2.5" width="9" height="6.5" rx="1" fill="#e9e3d6" stroke="#c9c0ae" stroke-width="0.5"/>'
              '<rect x="-4.5" y="-3.5" width="9" height="5" rx="1" fill="#fffdf6" stroke="#c9c0ae" stroke-width="0.5"/></g>')
    for x, y in ((52, 47), (70, 41), (38, 44)):  # 海带
        c += (f'<path d="M{x - 5} {y} C{x - 3} {y - 4} {x + 3} {y - 4} {x + 6} {y - 1} C{x + 2} {y + 2} {x - 2} {y + 3} {x - 5} {y} Z" fill="#2f5a2a"/>'
              f'<path d="M{x - 3} {y - 1} C{x} {y - 3} {x + 3} {y - 2} {x + 4} {y - 1}" fill="none" stroke="#4f7d45" stroke-width="0.8"/>')
    c += scallions([(56, 36), (66, 34), (48, 42), (82, 43), (60, 40)], r=1.9)
    c += glints_at([(30, 36, 5, 1.2), (84, 36, 4, 1)])
    defs = ('    <linearGradient id="lacq" x1="0" y1="0" x2="1" y2="0.4"><stop offset="0" stop-color="#3a3436"/><stop offset="1" stop-color="#141012"/></linearGradient>\n'
            '    <radialGradient id="miso" cx="0.45" cy="0.4" r="0.65"><stop offset="0" stop-color="#d9a56a"/><stop offset="1" stop-color="#a96f3a"/></radialGradient>\n')
    return bowl(defs, "url(#lacq)", "#8f2a1e", "url(#miso)", c)


def udon(name, item):
    rnd = random.Random("udon")
    c = ""
    for d in ("M24 40 C36 32 50 50 64 40 C76 32 86 46 98 40", "M28 46 C40 38 54 54 70 44 C80 38 88 48 94 45",
              "M30 35 C42 30 54 42 66 35 C76 30 84 38 92 34", "M36 50 C48 44 60 54 74 49"):
        c += f'<path d="{d}" fill="none" stroke="#d8c59a" stroke-width="5.4" stroke-linecap="round"/>'
        c += f'<path d="{d}" fill="none" stroke="#fdf8ea" stroke-width="3.8" stroke-linecap="round"/>'
    c += ('<g transform="translate(78 38) rotate(-10)"><path d="M-8 2 C-8 -5 8 -5 8 2 Z" fill="#fffaf2" stroke="#d9cfc0" stroke-width="0.5"/>'
          '<path d="M-8 2 C-8 -5 8 -5 8 2" fill="none" stroke="#f07d9a" stroke-width="1.6"/>'
          '<path d="M-4 1 C-4 -2 4 -2 4 1" fill="none" stroke="#f7b4c5" stroke-width="0.9"/></g>')
    c += scallions([(46, 38), (54, 34), (60, 44), (40, 45), (68, 36)], r=1.9)
    c += "".join(f'<circle cx="{f(rnd.uniform(40, 70))}" cy="{f(rnd.uniform(34, 46))}" r="{f(rnd.uniform(0.4, 0.7))}" fill="#c8402a"/>' for _ in range(8))
    band = '<path d="M17 50 C26 62 44 70 60 70 C76 70 94 62 103 50" fill="none" stroke="#2e5f9e" stroke-width="3"/>'
    defs = '    <linearGradient id="ub" x1="0" y1="0" x2="1" y2="0.3"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#dfe5ec"/></linearGradient>\n'
    return bowl(defs, "url(#ub)", "#f4f6f8", "#e7c27c", c, band=band).replace('stroke="#1c1416"', 'stroke="#9aa8b6"')


def chawanmushi(name, item):
    body = """  <g transform="translate(0 4)">
  <ellipse cx="60" cy="86" rx="42" ry="4" fill="#1c2b36" opacity="0.12"/>
  <ellipse cx="60" cy="74" rx="44" ry="12" fill="#cfd6dc" stroke="#bcc5cd" stroke-width="0.6"/>
  <ellipse cx="60" cy="72" rx="44" ry="12" fill="#f6f8fa" stroke="#c9d0d7" stroke-width="0.6"/>
  <path d="M30 36 C31 60 44 74 60 74 C76 74 89 60 90 36 Z" fill="url(#cup)" stroke="#9aa8b6" stroke-width="0.7"/>
  <path d="M33 50 C40 60 50 64 60 64 C70 64 80 60 87 50" fill="none" stroke="#b5303a" stroke-width="2"/>
  <path d="M38 58 l4 -3 l4 3 l4 -3 l4 3 l4 -3 l4 3 l4 -3 l4 3 l4 -3 l4 3" fill="none" stroke="#b5303a" stroke-width="1"/>
  <ellipse cx="60" cy="36" rx="30" ry="11" fill="#fbfcfd" stroke="#9aa8b6" stroke-width="0.7"/>
  <ellipse cx="60" cy="37" rx="26.5" ry="9" fill="url(#custard)"/>
  <path d="M42 34 C50 30 62 30 72 32" fill="none" stroke="#fff" stroke-width="2.4" opacity="0.6" stroke-linecap="round"/>
  <g transform="translate(66 38)"><path d="M-6 1 C-6 -4 2 -6 6 -2 C3 -1 1 2 -2 3 C-4 3.5 -6 3 -6 1 Z" fill="#f58a6a" stroke="#c9563a" stroke-width="0.5"/>
    <path d="M-4 0 C-2 -3 2 -3.5 4 -2" fill="none" stroke="#fff" stroke-width="1" opacity="0.8"/></g>
  <g transform="translate(70 35)"><ellipse rx="3.4" ry="2" fill="#8a6a4a" stroke="#5e4428" stroke-width="0.5"/><ellipse cx="-0.6" cy="-0.6" rx="1.4" ry="0.6" fill="#b89a74"/></g>
  <g transform="translate(51 36)"><ellipse cx="-3" cy="0" rx="3.2" ry="2" fill="#5ea34a" stroke="#3f7a2c" stroke-width="0.5"/><ellipse cx="3" cy="0" rx="3.2" ry="2" fill="#5ea34a" stroke="#3f7a2c" stroke-width="0.5"/>
    <ellipse cx="0" cy="-2.6" rx="2" ry="3" fill="#6fb655" stroke="#3f7a2c" stroke-width="0.5"/><path d="M0 0 L0 4" stroke="#3f7a2c" stroke-width="0.9"/></g>
  </g>
"""
    defs = ('    <linearGradient id="cup" x1="0" y1="0" x2="1" y2="0.3"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#dde4eb"/></linearGradient>\n'
            '    <linearGradient id="custard" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fdf0c2"/><stop offset="1" stop-color="#f0d27c"/></linearGradient>\n')
    return svg(body, defs, plate=False)


def wasabi(name, item):
    rnd = random.Random("wasabi")
    c = ('  <g transform="translate(60 60) scale(1.5) translate(-60 -56)">\n'
         '  <ellipse cx="60" cy="62" rx="16" ry="4" fill="#1c2b36" opacity="0.12"/>\n'
         '  <path d="M44 60 C42 52 50 46 56 44 C60 40 62 34 66 33 C66 38 64 42 68 45 C76 48 78 56 74 60 C68 65 50 65 44 60 Z" fill="url(#w)" stroke="#3f7a22" stroke-width="0.5"/>\n'
         '  <path d="M50 52 C54 48 60 47 64 48 M48 58 C56 56 66 57 72 55" fill="none" stroke="#b9dc84" stroke-width="1.4" opacity="0.8" stroke-linecap="round"/>\n'
         + "".join(f'  <circle cx="{f(rnd.uniform(46, 74))}" cy="{f(rnd.uniform(46, 62))}" r="{f(rnd.uniform(0.4, 0.8))}" fill="#4f8a2a" opacity="0.6"/>\n' for _ in range(26))
         + glints_at([(52, 49, 4, 1.1), (62, 38, 2.5, 1)]) + "\n  </g>\n")
    return svg(c, '    <linearGradient id="w" x1="0" y1="0" x2="0.3" y2="1"><stop offset="0" stop-color="#a8d266"/><stop offset="1" stop-color="#5f9a35"/></linearGradient>\n')


def gari(name, item):
    rnd = random.Random(name)
    c = '  <g transform="translate(60 61) scale(1.4) translate(-60 -56)">\n  <ellipse cx="60" cy="64" rx="20" ry="5" fill="#1c2b36" opacity="0.10"/>\n'
    for _ in range(9):
        x, y = 60 + rnd.uniform(-12, 12), 55 + rnd.uniform(-5, 5)
        rot, rx = rnd.randint(-40, 40), rnd.uniform(8, 11)
        c += (f'  <g transform="translate({f(x)} {f(y)}) rotate({rot})">'
              f'<ellipse rx="{f(rx)}" ry="{f(rx * 0.55)}" fill="#f9d8d2" opacity="0.92" stroke="#e8a8a0" stroke-width="0.7"/>'
              f'<path d="M{f(-rx * 0.6)} 0 C0 -1.5 {f(rx * 0.3)} 1 {f(rx * 0.6)} 0" fill="none" stroke="#f3c2bb" stroke-width="0.6"/></g>\n')
    c += f'  {glints_at([(54, 49, 4, 1.1), (66, 53, 3, 1)])}\n  </g>\n'
    return svg(c)


# ---------- 各种寿司 ----------

def nig(light, base, shadow, side, line, **kw):
    return dict(kind=nigiri, light=light, base=base, shadow=shadow, side=side, line=line, **kw)


ITEMS = {
    # 赤身：厚实饱满的叶片
    "maguro": nig("#e54a5c", "#c9243a", "#8c1325", "#9b1a2d", "#6e0d1c", sheen=0.35, shape=dict(W=26, T=3),
                  pattern=combine(lambda s: f'<path d="{s.line(-0.15, 0.25, 0.75)}" fill="none" stroke="#f06a78" stroke-width="3" opacity="0.5" filter="url(#soft)"/>',
                                  gl((0.3, -0.55, 0.12, 1.8), (0.47, -0.65, 0.08, 1.5), (0.6, -0.5, 0.1, 1.6)))),
    "chutoro": nig("#f3909c", "#e0596c", "#b03548", "#c0485a", "#8a2234", sheen=0.4, shape=dict(W=26, T=3),
                   pattern=combine(lines_across([0.2 + 0.075 * k for k in range(9)], "#ffe2e6", 1.1, 0.7, slant=0.04), STD_GL)),
    "otoro": nig("#ffe0df", "#f3a9b1", "#d4808b", "#e39aa3", "#b06470", sheen=0.5, shape=dict(W=26, T=3),
                 pattern=combine(marble("otoro", "#fff7f5", 55, 1.3), STD_GL)),
    "katsuo": nig("#d24f60", "#b02a3d", "#761526", "#5f666e", "#5e0f1c", shape=dict(W=26, T=3.2),
                  pattern=combine(hard_band(0.45, 1.05, "#7b838b"), soft_band(0.35, 0.55, "#3a3a3a", 0.5),
                                  blotches("katsuo", "#2b2b2b", 12, (0.5, 1), (1.5, 3.2), 0.6), STD_GL),
                  over=over_at(0.5, -0.4, ginger_scallion)),
    "bincho": nig("#fde6e1", "#f1c6be", "#d29a90", "#dcaba2", "#a9766c", sheen=0.5, shape=dict(W=25, T=2.2, droop=0.28),
                  pattern=combine(blotches("bincho", "#b9784a", 8, (-0.9, 0.2), (2, 4), 0.35), STD_GL),
                  over=over_at(0.5, -0.35, onion_slivers)),
    "salmon": nig("#ffaa70", "#f6823e", "#cf5d25", "#d96a2e", "#a84716", sheen=0.35, shape=dict(W=26, T=3),
                  pattern=combine(lines_across([0.16 + 0.085 * k for k in range(9)], "#fff1e4", 1.6, 0.9, slant=0.05),
                                  lines_across([0.2 + 0.085 * k for k in range(8)], "#ffcfae", 0.6, 0.7, slant=0.05), STD_GL)),
    # 白身：薄而通透，靠皮边色带和配料区分
    "tai": nig("#ffffff", "#f6ecea", "#dcc3c0", "#e9d2cf", "#b58e8a", sheen=0.45, shape=dict(T=2),
               pattern=combine(soft_band(0.5, 1.05, "#ee8f98", 0.9), blotches("tai", "#d9505f", 12, (0.55, 1), (1, 2.6), 0.6),
                               lines_along([0.42], "#ffffff", 1.2, 0.9), STD_GL)),
    "hirame": nig("#ffffff", "#f1f1ee", "#cdd2d6", "#dde1e4", "#a9b0b7", sheen=0.5, shape=dict(W=24, T=1.8, taper=0.3, wp=0.5),
                  pattern=combine(soft_band(-0.3, 0.6, "#dfe4ea", 0.6, 0.15, 0.85),
                                  lines_across([0.3, 0.42, 0.54, 0.66], "#ffffff", 0.8, 0.8), gl((0.3, -0.6, 0.1, 1.2))),
                  under=shiso, over=over_at(0.5, -0.3, momiji)),
    "engawa": nig("#ffffff", "#f6f3ec", "#d1ccc0", "#e1dcd0", "#a39d8e", sheen=0.55, shape=dict(W=22, T=2.4),
                  pattern=combine(lines_across([0.1 + 0.034 * k for k in range(24)], "#d4cbb8", 1.3, 0.9),
                                  lines_across([0.115 + 0.034 * k for k in range(24)], "#ffffff", 0.8, 0.9), STD_GL)),
    "hamachi": nig("#fff3ec", "#f4d5c6", "#d6a796", "#5c686e", "#a77f72", shape=dict(T=2.6),
                   pattern=combine(soft_band(0.3, 0.72, "#c4505a"), hard_band(0.7, 1.05, "#6c7980"),
                                   lines_along([0.76], "#c7d2d8", 0.9, 0.9), gl((0.3, -0.6, 0.1, 1.3), (0.5, -0.7, 0.08, 1.1)))),
    "buri": nig("#fff6f0", "#f3d8cb", "#d4a594", "#505c63", "#a07868", shape=dict(T=2.8),
                pattern=combine(soft_band(0.15, 0.7, "#a3323d", 0.9), hard_band(0.68, 1.05, "#5d6870"),
                                lines_across([0.18 + 0.1 * k for k in range(7)], "#ffffff", 0.9, 0.6, -1, 0.1), STD_GL)),
    "kanpachi": nig("#ffffff", "#f8e6df", "#dab7aa", "#e4c7bc", "#b08a7e", sheen=0.45, shape=dict(T=2.4),
                    pattern=combine(lines_along([0.55], "#e3838c", 1.8, 0.85), STD_GL)),
    # 光物：银色的皮
    "aji": nig("#ffffff", "#dfe5e8", "#a9b8bf", "#e6b9b2", "#7d8e96", sheen=0.5, shape=dict(T=2.4),
               pattern=combine(hard_band(-1.05, 0.3, "#7f9aa0"), blotches("aji", "#33454b", 22, (-0.6, 0.3), (1.4, 3.2), 0.7),
                               lines_along([0.38], "#d8c56a", 1.1, 0.95), STD_GL),
               over=over_at(0.5, -0.35, ginger_scallion)),
    "saba": nig("#ffffff", "#e3ebf0", "#a9bac6", "#efd6cf", "#5e7686", sheen=0.5, shape=dict(T=3),
                pattern=combine(hard_band(-1.05, 0.45, "#5d8797"), mackerel_stripes,
                                lines_along([0.5], "#d8e4ea", 1.2, 0.9), STD_GL)),
    "iwashi": nig("#ffffff", "#e6ecef", "#aab8c2", "#e4b0a6", "#6c7f8c", sheen=0.55, shape=dict(L=70, W=19, T=2.2),
                  pattern=combine(hard_band(-1.05, 0.15, "#34587a"), dots_along(0.35, [0.18 + 0.08 * k for k in range(9)], "#16222c", 1.2),
                                  gl((0.3, -0.5, 0.1, 1.2), (0.55, -0.6, 0.08, 1.1))),
                  over=over_at(0.5, -0.3, ginger_dot)),
    "kohada": nig("#ffffff", "#e6e9e2", "#aeb6ae", "#efd2c8", "#7c877f", sheen=0.5, shape=dict(L=62, W=24, T=2.2),
                  pattern=combine(hard_band(-1.05, 0.15, "#8c9a92"),
                                  *[dots_along(v, [0.1 + 0.035 * k for k in range(24)], "#2e3a38", 0.6) for v in (-0.15, 0.1, 0.35, 0.6)],
                                  lines_across([0.42, 0.56], "#ffffff", 0.9, 0.9, -0.9, 0.6), STD_GL)),
    "sanma": nig("#ffffff", "#dfe5ea", "#a6b3bd", "#e3b1a8", "#56657a", sheen=0.5, shape=dict(L=80, W=17, T=2.2, endh=0.4),
                 pattern=combine(hard_band(-1.05, 0.35, "#2f3d5a"), lines_along([0.45], "#ffffff", 1.4, 1),
                                 gl((0.3, -0.4, 0.1, 1.2), (0.55, -0.5, 0.08, 1.1))),
                 over=lambda s: scallions([s.P(u, -0.3) for u in (0.42, 0.5, 0.58)], r=1.8)),
    # 贝类
    "hotate": nig("#fff7ef", "#f6e3d0", "#d6b597", "#e3c6aa", "#b08e70", sheen=0.6,
                  shape=dict(L=46, W=27, T=3.5, taper=0, wp=0.22, droop=0.35, crown=3, endh=7),
                  pattern=combine(lines_across([0.2 + 0.075 * k for k in range(9)], "#ead6bd", 0.7, 0.4),
                                  gl((0.3, -0.5, 0.12, 1.6), (0.5, -0.65, 0.1, 1.4)))),
    "akagai": nig("#ff9a6e", "#ef653d", "#c03a22", "#b2341f", "#8f2614", sheen=0.4,
                  shape=dict(L=58, W=27, T=2.6, ripple=0.14, rf=15, wp=0.5),
                  pattern=combine(inner_rim("#ffc3a3", 2.4, 0.9), slit(0.25, 0.75), STD_GL)),
    "tsubugai": nig("#fffdf8", "#f4ecdd", "#cfc0a6", "#d9c9ae", "#9a8a72", sheen=0.5,
                    shape=dict(L=58, T=3, ripple=0.07, rf=9),
                    pattern=combine(inner_rim("#8d7b66", 4, 0.4), STD_GL)),
    "hokkigai": nig("#ffffff", "#f6f0f2", "#d6c6ca", "#e3d3d7", "#a48f95", sheen=0.5, shape=dict(L=60, taper=0.6, wp=0.5),
                    pattern=combine(soft_band(-1, 1, "#e86a7c", 0.75, 0.6, 1), soft_band(-1, 1, "#d8394f", 0.6, 0.8, 1),
                                    slit(0.5, 0.95), STD_GL)),
    "awabi": nig("#ece2bb", "#cfc398", "#9a8d5e", "#8f8456", "#5f5a34", sheen=0.4, shape=dict(L=54, W=26, T=3.6, wp=0.3),
                 pattern=combine(lines_across([0.08 + 0.06 * k for k in range(15)], "#a99c6a", 0.7, 0.8, slant=0.08),
                                 lines_across([0.08 + 0.06 * k for k in range(15)], "#a99c6a", 0.7, 0.8, slant=-0.08),
                                 inner_rim("#5e5a30", 4, 0.55), STD_GL)),
    # 虾蟹乌贼章鱼
    "ebi": nig("#ffffff", "#fbeee8", "#e8c2b3", "#efc5b7", "#c96a52", shape=dict(L=58, taper=0.45, wp=0.4),
               pattern=combine(*[hard_band(-1.05, 1.05, "#f2683f", 0.95, 0.1 + 0.13 * k, 0.17 + 0.13 * k) for k in range(6)],
                               *[lines_across([0.17 + 0.13 * k], "#ffffff", 0.9, 0.7) for k in range(6)], STD_GL),
               under=lambda s: tail(s)),
    "amaebi": nig("#ffd5ca", "#ffae9b", "#e5806d", "#f0947f", "#c85c48", sheen=0.55,
                  strips=[-6, 6], shape=dict(L=56, W=12, T=2, taper=0.5, wp=0.45, droop=0.3),
                  pattern=combine(lines_across([0.2 + 0.1 * k for k in range(7)], "#ffcabd", 0.8, 0.8),
                                  gl((0.3, -0.4, 0.12, 1.1), (0.55, -0.5, 0.08, 1))),
                  under=lambda s: tail(s, "#ff6b4a", "#b23a24", 0.6)),
    "botanebi": nig("#ffd0c4", "#f79080", "#d65a4e", "#e98374", "#a8443a", sheen=0.5, shape=dict(L=60, W=24, taper=0.45, T=2.6),
                    pattern=combine(blotches("botan", "#c92f28", 40, (-0.95, 0.95), (0.4, 0.9), 0.75),
                                    lines_across([0.2 + 0.11 * k for k in range(6)], "#ffbcae", 0.9, 0.8), STD_GL),
                    under=lambda s: tail(s, "#e2452f", "#8f1f14", 1.25)),
    "kani": nig("#ffffff", "#faf6f1", "#dccfc3", "#e9ded3", "#b0907e", sheen=0.5,
                strips=[-6, 6], shape=dict(L=58, W=12, T=2.4, taper=0.05, wp=0.18, droop=0.18, crown=1.6),
                pattern=combine(hard_band(-1.05, 0.55, "#e23b25"), soft_band(-0.4, 0.15, "#ff8a66", 0.7),
                                lines_along([0.25, 0.5, 0.75], "#e6dbd0", 0.7, 0.9), gl((0.3, -0.5, 0.12, 1.2), (0.55, -0.6, 0.1, 1.1)))),
    "ika": nig("#ffffff", "#fafbfc", "#cbd4de", "#e0e6ed", "#97a6b6", sheen=0.6, shape=dict(W=26, T=2.6, taper=0.1, wp=0.25),
               pattern=combine(lines_across([0.12 + 0.045 * k for k in range(17)], "#d3dbe4", 0.6, 1),
                               gl((0.25, -0.6, 0.14, 1.5), (0.55, -0.7, 0.1, 1.3))),
               over=over_at(0.5, -0.25, ginger_dot)),
    "tako": nig("#ffffff", "#f7f0f2", "#dcc6cc", "#7e2240", "#6e1f39", sheen=0.5, shape=dict(T=2.6, ripple=0.06, rf=18),
                pattern=combine(hard_band(0.6, 1.05, "#8e2a4a"), soft_band(0.45, 0.65, "#c45a7a", 0.6), suckers, STD_GL)),
    # 其他
    "tamago": dict(kind=tamago),
    "inari": dict(kind=inari),
    "anago": nig("#f1cc93", "#d6a063", "#a26a35", "#94602e", "#7d4e22", sheen=0.4,
                 shape=dict(L=68, W=26, T=1.8, taper=0.15, wp=0.3, endh=0.4, droop=0.2, ripple=0.06),
                 pattern=combine(lines_along((-0.65, -0.35, -0.05, 0.25, 0.55), "#f5d6a8", 0.9, 0.75),
                                 soft_band(-0.6, 0.3, "#8a4f20", 0.18, 0.2, 0.8), gl((0.3, -0.55, 0.1, 1.3), (0.55, -0.6, 0.08, 1.1)))),
    "unagi": nig("#a86533", "#73401d", "#3d1d0b", "#211006", "#1e0d04", sheen=0.25,
                 shape=dict(L=66, W=26, T=2.6, taper=0.15, wp=0.32, ripple=0.05), pattern=unagi_pattern, seeded=True),
    # 军舰
    "ikura": dict(kind=gunkan, base="#a52e10", filling=ikura_fill, behind=cucumbers),
    "uni": dict(kind=gunkan, base="#c9781e", filling=uni_fill,
                defs='    <radialGradient id="uni" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stop-color="#ffd877"/><stop offset="0.6" stop-color="#f0a232"/><stop offset="1" stop-color="#c97418"/></radialGradient>\n'),
    "tobikko": dict(kind=gunkan, base="#e0661a", filling=tobikko_fill),
    "kanimiso": dict(kind=gunkan, base="#6e6a3c", filling=kanimiso_fill, behind=cucumbers),
    "shirasu": dict(kind=gunkan, base="#ece8dc", filling=shirasu_fill),
    "negitoro": dict(kind=gunkan, base="#e07a88", filling=negitoro_fill),
    # 卷物
    "kappamaki": dict(kind=maki, core=core_cucumber),
    "tekkamaki": dict(kind=maki, core=core_rect(3.6, 3, "#c8323a", "#8c1325", "#e5606c")),
    "kanpyomaki": dict(kind=maki, core=core_kanpyo),
    "nattomaki": dict(kind=maki, core=core_natto),
    "shinkomaki": dict(kind=maki, core=core_rect(3.6, 3, "#ecc832", "#b8941a", "#f8e47a")),
    # 副菜
    "misoshiru": dict(kind=misoshiru),
    "chawanmushi": dict(kind=chawanmushi),
    "wasabi": dict(kind=wasabi),
    "gari": dict(kind=gari),
    "udon": dict(kind=udon),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, item in ITEMS.items():
        (OUT / f"{name}.svg").write_text(item["kind"](name, item), encoding="utf-8")
    words = json.loads((ROOT / "data" / "words.json").read_text(encoding="utf-8"))["words"]
    ids = {w["id"] for w in words}
    print(f"wrote {len(ITEMS)} svg")
    missing, extra = ids - ITEMS.keys(), ITEMS.keys() - ids
    if missing:
        print("题库里有、但还没画的：", sorted(missing))
    if extra:
        print("画了、但题库里没有的：", sorted(extra))


if __name__ == "__main__":
    main()
