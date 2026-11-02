# 用 Gemini（Nano Banana）生成寿司插图的提示词

目标：48 张风格统一的插图，替换现在 `img/sushi/` 里代码画的 SVG。
每种寿司的辨认特征来自第二轮调研（回转寿司店实物照片），见 [illustration-plan.md](illustration-plan.md)。

## 用脚本批量生成（推荐）

`tools/gen_images.py` 直接读这个文件里的提示词，调用 Gemini API 批量生成，再自动去白底、压成 WebP 换进游戏。

```bash
# 准备：在 Google AI Studio 申请 API key，自己设成环境变量（脚本只从环境变量读）
setx GEMINI_API_KEY "你的 key"
```

设完要重新打开终端才生效。然后在项目文件夹里：

```bash
python tools/gen_images.py generate salmon hamachi hirame ika --n 2
```

先试几种，确认风格和金枪鱼一致。开始前脚本会显示要生成几张、大约多少钱，输入 y 才会开始。

```bash
python tools/gen_images.py generate --n 3
```

全部生成，每种 3 张候选。已经有的候选会保留，只补不够的部分，中途断了重新运行就能接着来。

```bash
python tools/gen_images.py sheet
```

生成候选一览 `img/raw/index.html`。在项目文件夹运行 `python -m http.server 8790`，打开 http://localhost:8790/img/raw/ 挑图。

```bash
python tools/gen_images.py pick hamachi=2 ika=3
```

记下挑中的候选，没挑的默认用第 1 张。

```bash
python tools/gen_images.py process
```

去白底、裁剪、缩到 480px 宽、压成 WebP，放进 `img/sushi/`，并更新清单 `data/images.json`。清单里有的词游戏用 WebP，没有的继续用旧的 SVG，所以可以分批换。

- 参考图在 `img/raw/_reference.png`（你生成的那张金枪鱼），它本身直接当作金枪鱼的第 1 张候选，不会重复生成。
- 默认模型是 `gemini-nano-banana-2.1`，可以用 `--model gemini-3-pro-image` 等换成别的。
- 候选图很大，不进 git（`.gitignore` 里排除了 `img/raw/`，只保留参考图和挑选结果）。

## 在 Gemini 网页版里手动生成

1. **先生成一张「标准图」**：用下面「第一张」的完整提示词生成金枪鱼，多试几次，挑一张最满意的。
2. **后面每一张都带上这张标准图**：在 Gemini 里先上传标准图，再贴「之后每一张」的提示词，只把最后的 `{寿司描述}` 换成下表里对应的那一行。这样角度、盘子、画风、光线都能保持一致。
3. **背景用纯白**：Nano Banana 一般给不出透明背景。生成纯白背景的图就行，去背景、裁剪、压缩交给我。
4. **文件名用表里的 id**（如 `maguro.png`），全部放进一个文件夹给我。

## 第一张（金枪鱼，用来定风格）

```
Flat vector illustration of Japanese kaiten (conveyor-belt) sushi, for a mobile quiz game.
Style: clean shapes, soft cel shading with 2-3 tones per surface, thin outlines in a slightly darker shade of each object's own color (no black outlines), a few small white highlight strokes so the fish looks fresh and glossy. Friendly and appetizing, but accurate enough that a Japanese person recognizes the exact type of sushi.
Composition: exactly two pieces of the same nigiri side by side, the back piece slightly to the left and the front piece slightly to the right, slightly overlapping, on a small round plain white ceramic plate.
Camera: three-quarter front view from about 30 degrees above the table, so you can see each fish slice draped over the rice ball, both ends of the slice hanging down toward the plate, and the white rice grains visible underneath.
Background: plain solid pure white, nothing else in the frame. No text, no chopsticks, no soy sauce, no logo, no conveyor belt.
Wide 16:9 image, the plate fills about 90% of the width.
Sushi: Maguro (lean tuna) nigiri — a thick, deep crimson-red slice, smooth and glossy, no white fat lines.
```

## 之后每一张（先上传标准图）

```
Use the attached image as the style reference. Keep exactly the same plate, camera angle, lighting, outline style, shading style, background and composition. Only change the sushi to the following:
{寿司描述}
Plain solid pure white background, no text. Wide 16:9.
```

军舰、卷物、副菜不是「两贯握寿司」，表里已经写明构图，照着替换就行。

## 48 个词的寿司描述

### 赤身

| id | 寿司描述（替换 `{寿司描述}`） | 要点 |
|---|---|---|
| maguro | Maguro (lean tuna) nigiri — a thick, deep crimson-red slice, smooth and glossy, no white fat lines. | 深红、光滑 |
| chutoro | Chutoro (medium-fatty tuna) nigiri — a rosy pink-red slice with a few thin white fat lines running diagonally across it. | 粉红，几道白纹 |
| otoro | Otoro (fatty tuna belly) nigiri — a pale pink slice covered with a dense network of white marbled fat. | 浅粉，大理石纹 |
| katsuo | Katsuo tataki (seared bonito) nigiri — a dark red slice whose skin edge is seared silver-grey with charred marks, topped with a small mound of grated ginger and chopped green onion. | 炙烤皮边 + 姜葱 |
| bincho | Binchō (albacore tuna) nigiri — a very soft, pale pink-beige slice, lightly torched with light brown spots, topped with thin white onion slivers and a little green onion. | 米粉色 + 洋葱丝 |

### 白身

| id | 寿司描述 | 要点 |
|---|---|---|
| tai | Madai (red sea bream) nigiri — a thin translucent white slice with a mottled pinkish-red skin edge along one side. | 白 + 红皮边 |
| hirame | Hirame (flounder) nigiri — a thin translucent white slice sitting on a green shiso leaf whose serrated edge peeks out from behind, topped with a small dab of orange momiji-oroshi (grated daikon with chili) and a few chopped chives. | 紫苏叶 + 红叶萝卜泥 |
| engawa | Engawa (flounder fin muscle) nigiri — a glossy white slice with many fine parallel ridges running across its width, like a ribbed surface. | 白 + 横棱 |
| hamachi | Hamachi (young yellowtail) nigiri — a creamy pale pink slice; along the front edge a dark silver-grey skin strip, with a dark red blood-line band just above it. | 银灰皮 + 血合 |
| buri | Buri (adult yellowtail) nigiri — a paler, fattier slice with faint white fat lines, a wider dark red blood-line, and a dark grey skin strip along one edge. | 更白更肥、血合更宽 |
| kanpachi | Kanpachi (greater amberjack) nigiri — a pinkish-white slice with one thin pink line along its length and no dark skin. | 粉白 + 一道细粉线 |

### 光物

| id | 寿司描述 | 要点 |
|---|---|---|
| aji | Aji (horse mackerel) nigiri — skin side up: silver skin with a blue-grey back and a dark blotchy pattern, a thin golden line along the side, topped with grated ginger and chopped green onion. | 银皮斑驳 + 姜葱 |
| saba | Shime-saba (vinegar-cured mackerel) nigiri — a thick slice, silver skin with bold dark blue-black wavy zebra stripes; pinkish-white flesh visible at the cut edge. | 斑马纹 |
| iwashi | Iwashi (sardine) nigiri — a long, slender slice, bright silver skin with a dark navy back stripe and a row of black dots along the side, a small dab of grated ginger on top. | 细长 + 一排黑点 |
| kohada | Kohada (gizzard shad) nigiri — a small silver-grey fillet with rows of tiny black dots running lengthwise, and two shallow criss-cross knife cuts on the skin. | 纵向点列 + 刀口 |
| sanma | Sanma (Pacific saury) nigiri — a very long, thin slice hanging well over both ends of the rice, dark steel-blue back and a bright silver line, topped with chopped green onion. | 最长最细 |

### 贝类

| id | 寿司描述 | 要点 |
|---|---|---|
| hotate | Hotate (scallop) nigiri — on each piece one thick, round, plump scallop, cream-peach colored, glossy and slightly translucent. | 圆鼓鼓 |
| akagai | Akagai (ark clam) nigiri — bright orange-red butterflied shellfish with frilly, curled edges, very glossy. | 橙红褶边 |
| tsubugai | Tsubugai (white whelk) nigiri — on each piece, a thin, glossy, slightly translucent cream-white slice of whelk, butterflied: one straight slit runs down the middle so the slice opens into two smooth lobes draped over the rice. The outer edges and the tip have a soft pale apricot-yellow tint, with a few faint curved lines on the surface. Not grey, not puffy, no knife scoring. | 奶白厚片 |
| hokkigai | Hokkigai (surf clam) nigiri — white shellfish with a pointed, beak-like tip that turns pinkish-red, with a slit down the middle. | 红尖鸟嘴 |
| awabi | Awabi (abalone) nigiri — a thick oval olive-beige slice with criss-cross knife scoring and a darker rim. | 橄榄色厚片 |

### 虾蟹乌贼章鱼

| id | 寿司描述 | 要点 |
|---|---|---|
| ebi | Ebi (boiled shrimp) nigiri — a butterflied shrimp with orange-red and white stripes and a red fan-shaped tail sticking out at one end. | 红白条 + 虾尾 |
| amaebi | Amaebi (sweet shrimp) nigiri — on each piece, exactly three small, thin, raw translucent pink shrimp lying side by side across the rice (clearly three separate shrimp, much thinner than one big shrimp), so three small red tails stick out together at one end. | 两三只小虾 |
| botanebi | Botan-ebi nigiri — on each piece, one large raw translucent pink shrimp with red speckles and a big red tail. | 一只大虾带红点 |
| kani | Kani (crab) nigiri — two sticks of crab leg meat lying side by side on the rice, red on top and white underneath, with fibrous texture. | 两根蟹腿 |
| ika | Ika (squid) nigiri — an opaque, pure white, glossy slice with very fine parallel knife cuts, a tiny yellow dab of grated ginger on top. | 纯白 + 姜泥 |
| tako | Tako (boiled octopus) nigiri — a white flesh slice with purple-red skin along one edge and a row of round suckers that make that edge bumpy. | 紫皮 + 吸盘 |

### 军舰卷（构图：两个军舰）

| id | 寿司描述 | 要点 |
|---|---|---|
| ikura | Two gunkan-maki side by side: rice wrapped in a tall band of dark green nori, topped with glossy orange salmon roe spheres, two thin cucumber slices standing at the back. | 鲑鱼子 + 黄瓜 |
| uni | Two gunkan-maki side by side: nori-wrapped rice topped with orange-yellow sea urchin lobes with a grainy texture. | 海胆 |
| tobikko | Two gunkan-maki side by side: nori-wrapped rice topped with a mound of tiny bright orange flying fish roe. | 细小橙色鱼籽 |
| kanimiso | Two gunkan-maki side by side: nori-wrapped rice topped with smooth greyish olive-brown crab tomalley paste, two cucumber slices standing at the back. | 灰绿褐色的膏 |
| shirasu | Two gunkan-maki side by side: nori-wrapped rice topped with a pile of tiny white whitebait fish (each with tiny black eyes) and a dab of grated ginger. | 小白鱼 + 姜 |
| negitoro | Two gunkan-maki side by side: nori-wrapped rice topped with pink minced fatty tuna and chopped green onion. | 粉色泥 + 葱 |

### 卷物（构图：三块细卷竖着放）

| id | 寿司描述 | 要点 |
|---|---|---|
| kappamaki | Instead of nigiri: three pieces of thin nori roll standing upright in a diagonal row; the cut face shows white rice with green cucumber sticks in the center. | 绿芯 |
| tekkamaki | Instead of nigiri: three pieces of thin nori roll standing upright in a diagonal row; the cut face shows white rice with a red square of tuna in the center. | 红芯 |
| kanpyomaki | Instead of nigiri: three pieces of thin nori roll standing upright in a diagonal row; the cut face shows white rice with dark brown simmered gourd strips in the center. | 深褐长条 |
| nattomaki | Instead of nigiri: three pieces of thin nori roll standing upright in a diagonal row; the cut face shows white rice with sticky light-brown fermented soybeans in the center. | 一粒粒豆 |
| shinkomaki | Instead of nigiri: three pieces of thin nori roll standing upright in a diagonal row; the cut face shows white rice with yellow pickled daikon in the center. | 黄芯 |

### 其他

| id | 寿司描述 | 要点 |
|---|---|---|
| tamago | Tamago nigiri — a thick rectangular block of sweet yellow rolled omelette with visible layers on its side, tied to the rice with a thin band of nori. | 方块 + 海苔带 |
| inari | Instead of nigiri: two golden-brown, pillow-shaped fried tofu pouches stuffed with rice, a few sesame seeds on top. | 金褐色小包 |
| anago | Anago (simmered sea eel) nigiri — a long, soft, wide light amber-brown fillet draping over the rice, with fine lengthwise lines and a thin glossy sweet sauce. | 浅琥珀色 |
| unagi | Unagi (grilled freshwater eel) nigiri — a dark brown grilled fillet with irregular charred spots and shiny caramel-colored sauce, fluffy edges. Not a steak, not a rectangle. | 深褐焦斑 + 酱汁光 |
| salmon | Salmon nigiri — a bright orange slice with white fat lines curving diagonally across it. | 橙 + 白斜纹 |

### 副菜（构图：一个容器，不放寿司）

| id | 寿司描述 | 要点 |
|---|---|---|
| misoshiru | Instead of sushi and plate: one black lacquer bowl with a red inside, filled with cloudy miso soup with small tofu cubes, wakame seaweed and green onion. | 漆碗味噌汤 |
| chawanmushi | Instead of sushi and plate: one small white ceramic cup (no lid) on a saucer, filled with smooth pale yellow steamed egg custard, a shrimp, a shiitake slice and a mitsuba leaf on top. | 开口杯 + 蒸蛋 |
| wasabi | No sushi: just a small mound of bright green grated wasabi on the white plate. | 一小堆芥末 |
| gari | No sushi: just a small pile of thin, pale pink pickled ginger slices on the white plate. | 一小堆姜片 |
| udon | Instead of sushi and plate: one white ceramic bowl with a blue stripe near the rim, thick white udon noodles in light broth, a slice of kamaboko with a pink swirl and chopped green onion. | 乌冬碗 |

## 生成后检查

- **两贯是不是同一种**：模型偶尔会把两贯画成不同的鱼。
- **特征有没有画对**：比如油甘鱼的银灰皮边、比目鱼的紫苏叶、章鱼的吸盘。不对就在同一个对话里追加一句，例如「Make the skin edge darker silver-grey」。
- **有没有多出东西**：筷子、酱油碟、文字之类。
- 军舰、卷物、副菜的构图和握寿司不同，如果模型被参考图带偏，可以单独为它们各做一张标准图。
