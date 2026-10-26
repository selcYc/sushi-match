# 回转寿司连线 sushi-match

把回转寿司店里写成平假名的菜名，连到对应的意思上。手机网页，中英双语。

**在线玩：https://selcyc.github.io/sushi-match/**（GitHub Pages，推送到 `main` 后一两分钟自动更新）

想法和后续计划见 [IDEA.md](IDEA.md)。

## 本地运行

纯 HTML/CSS/JS，不用安装依赖，但题库是用 `fetch` 读取的，所以要从本地服务器打开（直接双击 `index.html` 会读不到题库）：

```bash
python -m http.server 8790
```

在项目文件夹里运行，然后打开 http://localhost:8790 。

想在自己手机上试：电脑和手机连同一个 Wi-Fi，手机浏览器打开 `http://<电脑的局域网 IP>:8790`。

## 文件

| 文件 | 内容 |
|---|---|
| `index.html` | 页面结构 |
| `style.css` | 样式（盘子、小票、传送带） |
| `app.js` | 出题、连线、判定、设置 |
| `data/words.json` | 题库：分类 + 词条 |
| `img/sushi/<id>.svg` | 每个词的插图（「图」模式和本轮总结里用），由脚本生成，不要手改 |
| `tools/draw_sushi.py` | 生成插图的脚本 |
| `samples.html` | 插图一览，按分类列出全部插图 |
| `docs/illustration-research.md` | 插图画法的调研笔记 |

## 插图

```bash
python tools/draw_sushi.py
```

在项目文件夹里运行，重新生成 `img/sushi/` 下的全部 SVG。脚本最后会检查题库，列出「题库里有、但还没画的」词。
加新词时：先在 `words.json` 里加词条，再在脚本的 `ITEMS` 里加同名 `id` 的画法。

## 发布新版本时

`index.html` 里引用 `style.css` 和 `app.js` 时带着版本号（`?v=0.3.1`）。改了这两个文件后记得改版本号，
否则手机浏览器可能还在用缓存里的旧文件。

## 题库格式

```json
{
  "id": "engawa",
  "kana": "えんがわ",
  "romaji": "engawa",
  "kanji": "縁側",
  "cat": "shiromi",
  "tier": 2,
  "zh": "鳍边肉",
  "en": "Flounder fin muscle",
  "fact": { "zh": "……", "en": "……" }
}
```

- `tier` 是价格档位，决定盘子颜色：0 白盘免费，1 蓝 ¥120，2 红 ¥180，3 紫 ¥260，4 金 ¥360（价格在 `app.js` 的 `TIERS` 里）
- `kanji` 没有汉字写法时填 `null`（v0.3 的汉字陷阱关会用到）
- 每个分类至少要有 5 个词，否则单选这个分类时凑不够一轮
