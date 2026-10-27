const ROUND_SIZE = 5;
const REVIEW_PER_ROUND = 2;  // 每轮最多转回来几盘答错过的
const STACK_SHOWN = 9;       // 托盘上最多画几个盘子

// 盘子颜色 = 价格，和店里一样。价格是大概的
const TIERS = [
  { price: 0,   zh: "白盘（免费）", en: "White (free)" },
  { price: 120, zh: "蓝盘",       en: "Blue" },
  { price: 180, zh: "红盘",       en: "Red" },
  { price: 260, zh: "紫盘",       en: "Purple" },
  { price: 360, zh: "金盘",       en: "Gold" },
];

const STRINGS = {
  zh: {
    title: "回转寿司连线",
    answer: "右边显示",
    pic: "图",
    romaji: "罗马字",
    all: "全部",
    round: "第 {n} 轮",
    tapHint: "先点盘子再点意思。一次连对，盘子就归你；连错的盘子会转回来再考一次。",
    tooFew: "选中的分类不够 {n} 个词，再多选一个分类。",
    doneTitle: "这一轮吃完了",
    doneScore: "一次就连对 {ok} 个，共 {total} 个。",
    next: "下一轮",
    again: "转回来的",
    free: "免费",
    plates: "{n} 盘",
    checkout: "おあいそ",
    checkoutHint: "结账",
    billTitle: "お会計",
    billSub: "这一餐一共叠了 {n} 盘。",
    billTotal: "合计",
    billNote: "价格是大概的，每家店都不一样。",
    billReview: "还有 {n} 盘答错的在传送带上转，之后会转回来。",
    newMeal: "再来一餐",
    keepEating: "继续吃",
    loadError: "题库加载失败。请用本地服务器打开，比如在项目文件夹里运行 python -m http.server。",
  },
  en: {
    title: "Kaiten Sushi Match",
    answer: "Answers in",
    pic: "Picture",
    romaji: "Romaji",
    all: "All",
    round: "Round {n}",
    tapHint: "Tap a plate, then its meaning. Match it on the first try and the plate is yours; misses come back around later.",
    tooFew: "These categories have fewer than {n} words. Pick one more.",
    doneTitle: "Round cleared",
    doneScore: "{ok} of {total} matched on the first try.",
    next: "Next round",
    again: "Back again",
    free: "Free",
    plates: "{n} plates",
    checkout: "Oaiso",
    checkoutHint: "Check, please",
    billTitle: "Okaikei",
    billSub: "You stacked {n} plates this meal.",
    billTotal: "Total",
    billNote: "Prices are rough. Every shop is different.",
    billReview: "{n} missed plates are still on the belt. They'll come back around.",
    newMeal: "Start a new meal",
    keepEating: "Keep eating",
    loadError: "Couldn't load the word list. Open the page from a local server, e.g. run python -m http.server in the project folder.",
  },
};

const $ = (sel) => document.querySelector(sel);

const state = {
  categories: [],
  words: [],
  settings: load("sushi-match", { ui: "zh", answer: "pic", romaji: false, cats: [] }),
  // plates：这一餐吃到的盘子；review：答错过、还在传送带上转的词
  progress: load("sushi-match-progress", { plates: [], review: [] }),
  bag: [],
  roundNo: 0,
  round: [],
  matched: new Set(),
  missed: new Set(),
  selected: null,     // { side: "plate" | "tag", id }
};

function load(key, defaults) {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(key) || "{}") };
  } catch {
    return defaults;
  }
}

function save(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

const saveSettings = () => save("sushi-match", state.settings);
const saveProgress = () => save("sushi-match-progress", state.progress);

function t(key, vars = {}) {
  return STRINGS[state.settings.ui][key].replace(/\{(\w+)\}/g, (_, k) => vars[k]);
}

const word = (id) => state.words.find((w) => w.id === id);
// 插图更新时改这个版本号，让手机重新下载，不用缓存里的旧图（和 index.html 里 css/js 的版本号一起改）
const ASSET_VERSION = "0.8";
const picture = (id) => `img/sushi/${id}.svg?v=${ASSET_VERSION}`;

// 右边小票的内容：图片模式放插图（alt 用当前界面语言的意思），否则放文字
function fillTag(tag, w) {
  const pic = state.settings.answer === "pic";
  tag.classList.toggle("pic", pic);
  tag.textContent = "";
  if (pic) {
    const img = document.createElement("img");
    img.src = picture(w.id);
    img.alt = w[state.settings.ui];
    tag.append(img);
  } else {
    tag.textContent = w[state.settings.answer];
  }
  // 标上语言，浏览器才会用对字体（中文不用日文字形）
  if (pic) tag.removeAttribute("lang");
  else tag.lang = state.settings.answer === "zh" ? "zh-CN" : "en";
}
const rim = (id) => `var(--tier-${word(id).tier})`;
const rimColor = (id) =>
  getComputedStyle(document.documentElement).getPropertyValue(`--tier-${word(id).tier}`).trim();

function price(tier) {
  return tier === 0 ? t("free") : `¥${TIERS[tier].price}`;
}

function shuffle(list) {
  const a = [...list];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function pool() {
  const cats = state.settings.cats;
  return state.words.filter((w) => cats.length === 0 || cats.includes(w.cat));
}

// 抽词：先放几个转回来的错题，剩下的从洗好的「袋子」里抽，抽完一遍再重新洗。
// 同一「相似组」（group，比如油甘鱼 / 鰤鱼 / 红甘）的词尽量不放在同一轮：
// 实物本来就难分，放在一起考的是眼力而不是认词
function drawRound() {
  const ids = pool().map((w) => w.id);
  const again = shuffle(state.progress.review.filter((id) => ids.includes(id))).slice(0, REVIEW_PER_ROUND);
  state.bag = state.bag.filter((id) => ids.includes(id) && !again.includes(id));
  if (state.bag.length < ROUND_SIZE * 2) {
    state.bag.push(...shuffle(ids.filter((id) => !state.bag.includes(id) && !again.includes(id))));
  }

  const picked = [];
  const groups = new Set();
  const clash = (id) => word(id).group && groups.has(word(id).group);
  const take = (id) => {
    picked.push(id);
    if (word(id).group) groups.add(word(id).group);
  };
  for (const id of again) if (!clash(id)) take(id);
  for (let i = 0; i < state.bag.length && picked.length < ROUND_SIZE; ) {
    if (clash(state.bag[i])) i++;
    else take(state.bag.splice(i, 1)[0]);
  }
  // 选的分类里不同组的词不够一轮（比如只选了虾蟹乌贼），才允许同组的一起出
  while (picked.length < ROUND_SIZE && state.bag.length) take(state.bag.shift());
  return shuffle(picked).map(word);
}

/* ---------- 渲染 ---------- */

function renderStatic() {
  const s = state.settings;
  document.documentElement.lang = s.ui === "zh" ? "zh-CN" : "en";
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-ui]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.ui === s.ui));
  document.querySelectorAll("[data-answer]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.answer === s.answer));
  $("#romaji").checked = s.romaji;
  document.body.classList.toggle("show-romaji", s.romaji);
  renderChips();
  renderTray();
  $("#round-title").textContent = t("round", { n: state.roundNo });
}

function renderChips() {
  const chips = $("#chips");
  chips.innerHTML = "";
  const cats = state.settings.cats;
  const all = document.createElement("button");
  all.type = "button";
  all.textContent = t("all");
  all.setAttribute("aria-pressed", cats.length === 0);
  all.addEventListener("click", () => setCats([]));
  chips.append(all);
  for (const c of state.categories) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = c[state.settings.ui];
    b.setAttribute("aria-pressed", cats.includes(c.id));
    b.addEventListener("click", () => {
      setCats(cats.includes(c.id) ? cats.filter((x) => x !== c.id) : [...cats, c.id]);
    });
    chips.append(b);
  }
}

function setCats(cats) {
  state.settings.cats = cats;
  saveSettings();
  renderChips();
  newRound();
}

function newRound() {
  $("#summary").hidden = true;
  $("#fact").textContent = "";
  $("#fact").style.removeProperty("--rim");

  if (pool().length < ROUND_SIZE) {
    state.round = [];
    $("#plates").innerHTML = "";
    $("#tags").innerHTML = "";
    $("#lines").innerHTML = "";
    $("#dots").innerHTML = "";
    $("#fact").innerHTML = `<span class="empty">${t("tooFew", { n: ROUND_SIZE })}</span>`;
    return;
  }

  state.roundNo += 1;
  state.round = drawRound();
  state.matched = new Set();
  state.missed = new Set();
  state.selected = null;
  $("#round-title").textContent = t("round", { n: state.roundNo });
  renderBoard(true);
}

function renderBoard(enter = false) {
  const plates = $("#plates");
  const tags = $("#tags");
  plates.innerHTML = "";
  tags.innerHTML = "";

  for (const w of state.round) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.className = "plate";
    b.dataset.id = w.id;
    b.style.setProperty("--rim", rim(w.id));
    b.innerHTML = `<span class="kana" lang="ja"></span><span class="romaji"></span>`;
    b.querySelector(".kana").textContent = w.kana;
    b.querySelector(".kana").classList.toggle("long", w.kana.length > 5);
    b.querySelector(".romaji").textContent = w.romaji;
    if (state.progress.review.includes(w.id)) {
      const badge = document.createElement("span");
      badge.className = "again";
      badge.textContent = t("again");
      b.append(badge);
    }
    b.addEventListener("click", () => pick("plate", w.id));
    li.append(b);
    plates.append(li);
  }

  // 右边的意思顺序单独打乱
  for (const w of shuffle(state.round)) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tag";
    b.dataset.id = w.id;
    fillTag(b, w);
    b.addEventListener("click", () => pick("tag", w.id));
    li.append(b);
    tags.append(li);
  }

  const board = $("#board");
  board.classList.toggle("pic", state.settings.answer === "pic");
  board.classList.toggle("enter", enter);
  if (enter) setTimeout(() => board.classList.remove("enter"), 800);

  for (const id of state.matched) markDone(id);
  renderDots();
  drawLines(false);
}

function renderDots() {
  const dots = $("#dots");
  dots.innerHTML = "";
  const done = [...state.matched];
  state.round.forEach((_, i) => {
    const li = document.createElement("li");
    if (i < done.length) {
      li.className = "on";
      li.style.setProperty("--rim", rim(done[i]));
    }
    dots.append(li);
  });
}

function el(side, id) {
  return document.querySelector(`.${side}[data-id="${id}"]`);
}

function markDone(id) {
  for (const side of ["plate", "tag"]) {
    const node = el(side, id);
    node.classList.add("done");
    node.setAttribute("aria-disabled", "true");
    node.style.setProperty("--rim", rim(id));
  }
}

// 连线：从盘子右边缘连到小票左边缘
function drawLines(animateLast = true) {
  const svg = $("#lines");
  const box = $("#board").getBoundingClientRect();
  svg.innerHTML = "";
  const ids = [...state.matched];
  ids.forEach((id, i) => {
    const p = el("plate", id).getBoundingClientRect();
    const g = el("tag", id).getBoundingClientRect();
    const x1 = p.right - box.left - 2;
    const y1 = p.top + p.height / 2 - box.top;
    const x2 = g.left - box.left + 2;
    const y2 = g.top + g.height / 2 - box.top;
    const color = rimColor(id);
    const len = Math.hypot(x2 - x1, y2 - y1);
    const fresh = animateLast && i === ids.length - 1;
    svg.insertAdjacentHTML(
      "beforeend",
      `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}"
         style="${fresh ? `stroke-dasharray:${len};--len:${len}` : "animation:none"}"/>
       <circle cx="${x1}" cy="${y1}" r="5" fill="${color}" style="${fresh ? "" : "animation:none"}"/>
       <circle cx="${x2}" cy="${y2}" r="5" fill="${color}" style="${fresh ? "" : "animation:none"}"/>`
    );
  });
}

function setSelected(sel) {
  document.querySelectorAll('[aria-pressed="true"].plate, [aria-pressed="true"].tag')
    .forEach((n) => n.setAttribute("aria-pressed", "false"));
  state.selected = sel;
  if (sel) el(sel.side, sel.id).setAttribute("aria-pressed", "true");
}

function pick(side, id) {
  if (state.matched.has(id)) return;
  const sel = state.selected;
  if (!sel || sel.side === side) {
    setSelected(sel && sel.id === id ? null : { side, id });
    return;
  }
  const plateId = side === "plate" ? id : sel.id;
  const tagId = side === "tag" ? id : sel.id;
  setSelected(null);
  if (plateId === tagId) {
    match(plateId);
  } else {
    miss(plateId, tagId);
  }
}

function miss(plateId, tagId) {
  state.missed.add(plateId);
  if (!state.progress.review.includes(plateId)) {
    state.progress.review.push(plateId);
    saveProgress();
  }
  for (const node of [el("plate", plateId), el("tag", tagId)]) {
    node.classList.remove("wrong");
    void node.offsetWidth; // 重新触发动画
    node.classList.add("wrong");
  }
}

function match(id) {
  state.matched.add(id);
  // 一次就连对：盘子叠到托盘上，也从错题里拿掉
  if (!state.missed.has(id)) {
    state.progress.plates.push(id);
    state.progress.review = state.progress.review.filter((x) => x !== id);
    saveProgress();
    renderTray(true);
  }
  markDone(id);
  drawLines(true);
  renderDots();
  showFact(id);
  if (state.matched.size === state.round.length) {
    setTimeout(showSummary, 700);
  }
}

function showFact(id) {
  const w = word(id);
  const fact = $("#fact");
  fact.style.setProperty("--rim", rim(id));
  fact.innerHTML = `<b lang="ja"></b><span class="price"></span><span></span>`;
  fact.querySelector("b").textContent = w.kanji && w.kanji !== w.kana ? `${w.kana}（${w.kanji}）` : w.kana;
  fact.querySelector(".price").textContent = price(w.tier);
  fact.querySelector("span:last-child").textContent = w.fact[state.settings.ui];
}

function showSummary() {
  const total = state.round.length;
  const ok = total - state.missed.size;
  const box = $("#summary");
  box.innerHTML = `
    <h3>${t("doneTitle")}</h3>
    <p>${t("doneScore", { ok, total })}</p>
    <ul></ul>
    <button type="button" class="primary">${t("next")}</button>`;
  const ul = box.querySelector("ul");
  for (const w of state.round) {
    const missed = state.missed.has(w.id);
    const li = document.createElement("li");
    li.innerHTML = `<span class="mark"></span><img class="thumb" alt=""><div><span class="word" lang="ja"></span> <span class="meta"></span><div></div></div>`;
    li.querySelector(".thumb").src = picture(w.id);
    li.querySelector(".mark").textContent = missed ? "✗" : "✓";
    li.querySelector(".mark").classList.add(missed ? "miss" : "ok");
    li.querySelector(".word").textContent = w.kana;
    // 汉字是日文写法，单独标成日文；中英意思也各自标上语言，字体才不会混
    const meta = li.querySelector(".meta");
    const sep = state.settings.ui === "zh" ? "，" : ", ";
    if (w.kanji) {
      const kanji = document.createElement("span");
      kanji.lang = "ja";
      kanji.textContent = w.kanji;
      meta.append(kanji, sep);
    }
    meta.append([w.romaji, price(w.tier)].join(sep));
    const zh = document.createElement("span");
    zh.lang = "zh-CN";
    zh.textContent = w.zh;
    const en = document.createElement("span");
    en.lang = "en";
    en.textContent = w.en;
    li.querySelector("div > div").append(zh, " / ", en);
    ul.append(li);
  }
  box.querySelector(".primary").addEventListener("click", () => {
    newRound();
    window.scrollTo({ top: $(".round").offsetTop - 8, behavior: "smooth" });
  });
  box.hidden = false;
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ---------- 托盘和结账 ---------- */

function mealTotal() {
  return state.progress.plates.reduce((sum, id) => sum + TIERS[word(id).tier].price, 0);
}

function renderTray(dropLast = false) {
  const plates = state.progress.plates.filter(word);
  const stack = $("#stack");
  stack.innerHTML = "";
  plates.slice(-STACK_SHOWN).forEach((id, i, shown) => {
    const p = document.createElement("span");
    p.style.setProperty("--rim", rim(id));
    p.style.bottom = `${i * 5}px`;
    if (dropLast && i === shown.length - 1) p.className = "drop";
    stack.append(p);
  });
  $("#plate-count").textContent = t("plates", { n: plates.length });
  $("#plate-total").textContent = `¥${mealTotal().toLocaleString()}`;
  $("#checkout").disabled = plates.length === 0;
}

function showBill() {
  const plates = state.progress.plates.filter(word);
  const counts = TIERS.map(() => 0);
  for (const id of plates) counts[word(id).tier] += 1;

  const bill = $("#bill");
  bill.innerHTML = `
    <h2 lang="ja">${t("billTitle")}</h2>
    <p class="sub">${t("billSub", { n: plates.length })}</p>
    <table><tbody></tbody>
      <tfoot><tr><th colspan="2">${t("billTotal")}</th><td>¥${mealTotal().toLocaleString()}</td></tr></tfoot>
    </table>
    <p class="note">${t("billNote")}</p>
    <p class="note" id="bill-review"></p>
    <div class="actions">
      <button type="button" class="primary" data-act="new">${t("newMeal")}</button>
      <button type="button" class="ghost" data-act="close">${t("keepEating")}</button>
    </div>`;
  const tbody = bill.querySelector("tbody");
  TIERS.forEach((tier, i) => {
    if (!counts[i]) return;
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><span class="swatch" style="--rim: var(--tier-${i})"></span>${tier[state.settings.ui]}</td>
      <td>${price(i)} × ${counts[i]}</td><td>¥${(tier.price * counts[i]).toLocaleString()}</td>`;
    tbody.append(tr);
  });
  const review = state.progress.review.length;
  bill.querySelector("#bill-review").textContent = review ? t("billReview", { n: review }) : "";

  bill.querySelector('[data-act="new"]').addEventListener("click", () => {
    state.progress.plates = [];
    state.roundNo = 0;
    saveProgress();
    renderTray();
    bill.close();
    newRound();
  });
  bill.querySelector('[data-act="close"]').addEventListener("click", () => bill.close());
  bill.showModal();
}

/* ---------- 设置 ---------- */

function bindControls() {
  document.querySelectorAll("[data-ui]").forEach((b) =>
    b.addEventListener("click", () => {
      state.settings.ui = b.dataset.ui;
      saveSettings();
      renderStatic();
      if (state.selected) setSelected(null);
      document.querySelectorAll(".plate .again").forEach((n) => (n.textContent = t("again")));
      document.querySelectorAll(".tag.pic img").forEach((img) => (img.alt = word(img.parentNode.dataset.id)[state.settings.ui]));
      if (!$("#summary").hidden) showSummary();
      const last = [...state.matched].pop();
      if (last && $("#summary").hidden) showFact(last);
      // 换语言后文字长短变了，版面可能挪动，连线要跟着重画
      requestAnimationFrame(() => drawLines(false));
    })
  );
  document.querySelectorAll("[data-answer]").forEach((b) =>
    b.addEventListener("click", () => {
      state.settings.answer = b.dataset.answer;
      saveSettings();
      renderStatic();
      // 只换右边的内容，不打乱当前进度
      document.querySelectorAll(".tag").forEach((tag) => fillTag(tag, word(tag.dataset.id)));
      $("#board").classList.toggle("pic", state.settings.answer === "pic");
      requestAnimationFrame(() => drawLines(false));
    })
  );
  $("#romaji").addEventListener("change", (e) => {
    state.settings.romaji = e.target.checked;
    saveSettings();
    document.body.classList.toggle("show-romaji", state.settings.romaji);
    requestAnimationFrame(() => drawLines(false));
  });
  $("#checkout").addEventListener("click", showBill);
  window.addEventListener("resize", () => drawLines(false));
}

async function init() {
  bindControls();
  try {
    const res = await fetch("data/words.json");
    const data = await res.json();
    state.categories = data.categories;
    state.words = data.words;
  } catch {
    renderStatic();
    $("#fact").textContent = t("loadError");
    return;
  }
  // 题库更新后，清掉已经不存在的分类和词
  state.settings.cats = state.settings.cats.filter((c) => state.categories.some((x) => x.id === c));
  state.progress.plates = state.progress.plates.filter(word);
  state.progress.review = state.progress.review.filter(word);
  renderStatic();
  newRound();
}

init();
