/**
 * Code Quest Mini App — MCQ: тема, грейд, варианты ответа, очки по сложности, лидерборд.
 */

const tg = window.Telegram?.WebApp;

const SS_TID = "codequest_tg_id";

/** Кеш пользователя — парсим initData ровно один раз. */
let _cachedUser = null;

/** Ранний сигнал Telegram — иначе на части клиентов initData подставляется с задержкой. */
if (tg) {
  tg.ready();
  tg.expand();
}

/** Высота окна Mini App — без растягивания вручную контент подстраивается под viewport. */
function syncTelegramViewport() {
  if (!tg) return;
  const h = tg.viewportStableHeight;
  if (typeof h === "number" && h > 0) {
    document.documentElement.style.setProperty("--tg-viewport-stable-height", `${h}px`);
  }
}
syncTelegramViewport();
requestAnimationFrame(syncTelegramViewport);
if (tg && typeof tg.onEvent === "function") {
  tg.onEvent("viewportChanged", syncTelegramViewport);
}

let currentQuestionId = null;
let submitting = false;

function persistTelegramId(id) {
  if (id == null || !tg) return;
  try {
    sessionStorage.setItem(SS_TID, String(id));
  } catch (_) {
    /* private mode / quota */
  }
}

function readCachedTelegramId() {
  if (!tg) return null;
  try {
    const raw = sessionStorage.getItem(SS_TID);
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : null;
  } catch (_) {
    return null;
  }
}

function applyTheme() {
  if (!tg) return;
  const p = tg.themeParams;
  const root = document.documentElement;
  if (p?.bg_color) root.style.setProperty("--bg", p.bg_color);
  if (p?.text_color) root.style.setProperty("--text", p.text_color);
  if (p?.hint_color) root.style.setProperty("--muted", p.hint_color);
  if (p?.secondary_bg_color) root.style.setProperty("--surface", p.secondary_bg_color);
  if (p?.section_bg_color) root.style.setProperty("--bg-elevated", p.section_bg_color);
  if (p?.link_color) root.style.setProperty("--accent", p.link_color);
  if (tg.colorScheme === "light") {
    root.style.colorScheme = "light";
  }
}

/** Сырая initData для проверки на сервере (Mini App). */
function telegramAuthHeaders() {
  const raw = collectRawInitData();
  if (!raw) return {};
  return { "X-Telegram-Init-Data": raw };
}

async function fetchJson(path, options = {}) {
  const { headers: userHeaders, timeoutMs, requireTelegramAuth, ...rest } = options;
  const hasBody = rest.body != null && String(rest.method || "GET").toUpperCase() !== "GET";
  const ctrl = new AbortController();
  const t =
    typeof timeoutMs === "number" && timeoutMs > 0
      ? setTimeout(() => ctrl.abort(), timeoutMs)
      : null;
  const tgH = requireTelegramAuth ? telegramAuthHeaders() : {};
  const res = await fetch(path, {
    ...rest,
    signal: ctrl.signal,
    headers: {
      Accept: "application/json",
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...tgH,
      ...userHeaders,
    },
  }).finally(() => {
    if (t) clearTimeout(t);
  });
  if (!res.ok) {
    const text = await res.text();
    if (res.status === 401) {
      throw new Error(
        "Сессия Telegram недействительна или устарела. Закройте Mini App и откройте снова из бота.",
      );
    }
    if (res.status === 429) {
      throw new Error("Слишком много запросов. Подождите около минуты.");
    }
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
}

function absoluteUrl(statusPath) {
  if (!statusPath) return statusPath;
  if (statusPath.startsWith("http://") || statusPath.startsWith("https://")) return statusPath;
  const base = window.location.origin || "";
  const p = statusPath.startsWith("/") ? statusPath : `/${statusPath}`;
  return `${base}${p}`;
}

/**
 * POST с телом JSON; при 202 опрашивает GET status_url до succeeded/failed.
 * Возвращает payload из result.data (формат фоновых задач API).
 */
async function postJsonThenPollJob(path, options = {}) {
  const {
    headers: userHeaders,
    timeoutMs,
    requireTelegramAuth,
    pollTimeoutMs,
    body,
    ...rest
  } = options;
  const ctrl = new AbortController();
  const t =
    typeof timeoutMs === "number" && timeoutMs > 0
      ? setTimeout(() => ctrl.abort(), timeoutMs)
      : null;
  const tgH = requireTelegramAuth ? telegramAuthHeaders() : {};
  const res = await fetch(path, {
    method: "POST",
    ...rest,
    body,
    signal: ctrl.signal,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...tgH,
      ...userHeaders,
    },
  }).finally(() => {
    if (t) clearTimeout(t);
  });
  if (res.status === 401) {
    throw new Error(
      "Сессия Telegram недействительна или устарела. Закройте Mini App и откройте снова из бота.",
    );
  }
  if (res.status === 429) {
    const text = await res.text();
    throw new Error(text || "Слишком много запросов. Подождите около минуты.");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${text}`);
  }
  if (res.status !== 202) {
    return res.json();
  }
  const accepted = await res.json();
  const statusUrl = absoluteUrl(accepted.status_url);
  const maxWait = typeof pollTimeoutMs === "number" && pollTimeoutMs > 0 ? pollTimeoutMs : 120000;
  const start = Date.now();
  let interval = 400;
  while (Date.now() - start < maxWait) {
    const c2 = new AbortController();
    const t2 = setTimeout(() => c2.abort(), 30000);
    try {
      const r2 = await fetch(statusUrl, {
        method: "GET",
        signal: c2.signal,
        headers: {
          Accept: "application/json",
          ...tgH,
        },
      });
      if (r2.status === 401) {
        throw new Error(
          "Сессия Telegram недействительна или устарела. Закройте Mini App и откройте снова из бота.",
        );
      }
      if (r2.ok) {
        const st = await r2.json();
        if (st.status === "succeeded") {
          const inner = st.result;
          if (inner && typeof inner === "object" && inner.data != null) return inner.data;
          return inner;
        }
        if (st.status === "failed") {
          throw new Error(st.error || "Задача не выполнена");
        }
      }
    } finally {
      clearTimeout(t2);
    }
    await new Promise((r) => setTimeout(r, interval));
    interval = Math.min(interval + 200, 2000);
  }
  throw new Error("Превышено время ожидания ответа сервера");
}

function setText(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function friendlyError(err) {
  const msg = String(err);
  if (err?.name === "AbortError" || msg.includes("aborted")) {
    return "Долгий ответ сервера (таймаут). Подождите или проверьте доступность Yandex Cloud API.";
  }
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
    return "Нет связи с сервером. Проверьте интернет и попробуйте снова.";
  }
  return msg;
}

/**
 * В части клиентов `initDataUnsafe.user` пуст, хотя Mini App открыт из бота;
 * тогда пользователь всё ещё в сырой строке `Telegram.WebApp.initData`.
 */
function _tryParseUserQueryString(s) {
  try {
    const params = new URLSearchParams(s);
    const userJson = params.get("user");
    if (!userJson) return null;
    return JSON.parse(userJson);
  } catch {
    return null;
  }
}

function parseUserFromInitData(raw) {
  if (!raw || typeof raw !== "string") return null;
  const trimmed = raw.trim();
  let u = _tryParseUserQueryString(trimmed);
  if (u?.id != null) return u;
  if (trimmed.includes("%")) {
    try {
      const decoded = decodeURIComponent(trimmed.replace(/\+/g, " "));
      u = _tryParseUserQueryString(decoded);
      if (u?.id != null) return u;
    } catch {
      /* ignore */
    }
  }
  return null;
}

/** Как в telegram-web-app.js: initParams из sessionStorage после первого захода с hash. */
function readInitDataFromTelegramSessionStorage() {
  try {
    const raw = window.sessionStorage.getItem("__telegram__initParams");
    if (!raw) return "";
    const p = JSON.parse(raw);
    const d = p?.tgWebAppData;
    return typeof d === "string" && d.length > 0 ? d : "";
  } catch {
    return "";
  }
}

/**
 * Сырая строка initData: WebApp.initData, WebView.initParams, hash (#tgWebAppData=…), query.
 * Раньше hash парсился только если в нём был «user=» — у Telegram обычно только tgWebAppData=…
 */
function collectRawInitData() {
  if (tg?.initData && String(tg.initData).length > 0) {
    return String(tg.initData);
  }
  try {
    const wp = window.Telegram?.WebView?.initParams?.tgWebAppData;
    if (wp && String(wp).length > 0) {
      return String(wp);
    }
  } catch (_) {
    /* ignore */
  }
  const stored = readInitDataFromTelegramSessionStorage();
  if (stored) return stored;

  try {
    const sp = window.location.search.slice(1);
    if (sp) {
      const q = new URLSearchParams(sp);
      const embedded = q.get("tgWebAppData");
      if (embedded) return embedded;
      if (sp.startsWith("query_id=") || sp.startsWith("user=")) return sp;
    }
  } catch (_) {
    /* ignore */
  }
  try {
    const h = window.location.hash.replace(/^#/, "");
    if (!h) return "";
    const q = new URLSearchParams(h);
    const embedded = q.get("tgWebAppData");
    if (embedded) return embedded;
    if (h.startsWith("query_id=") || h.startsWith("user=")) return h;
  } catch (_) {
    /* ignore */
  }
  return "";
}

/**
 * Разбирает initData один раз и кеширует результат в _cachedUser.
 * Повторные вызовы просто возвращают кеш — без URLSearchParams/JSON.parse.
 */
function normalizeUnsafeUser(user) {
  if (user == null) return null;
  if (typeof user === "object" && user.id != null) return user;
  if (typeof user === "string") {
    try {
      const o = JSON.parse(user);
      return o?.id != null ? o : null;
    } catch {
      return null;
    }
  }
  return null;
}

function getTelegramUser() {
  if (!tg) return null;
  if (_cachedUser) return _cachedUser;

  const fromUnsafe = normalizeUnsafeUser(tg.initDataUnsafe?.user);
  if (fromUnsafe) {
    _cachedUser = fromUnsafe;
    persistTelegramId(fromUnsafe.id);
    return _cachedUser;
  }

  const raw = collectRawInitData();
  const parsed =
    parseUserFromInitData(raw) ??
    parseUserFromInitData(tg.initData ? String(tg.initData) : "");
  if (parsed?.id != null) {
    _cachedUser = parsed;
    persistTelegramId(parsed.id);
    return _cachedUser;
  }
  return null;
}

function getTelegramId() {
  const u = getTelegramUser();
  if (u?.id != null) return u.id;
  return readCachedTelegramId();
}

/**
 * Ждём появления initData (Android / меню), но не дольше maxMs.
 * Используем _cachedUser — повторный парсинг исключён.
 */
async function ensureTelegramUser(maxMs = 10000) {
  const step = 100;
  const deadline = Date.now() + maxMs;
  while (Date.now() < deadline) {
    const u = getTelegramUser(); // вернёт кеш если уже есть
    if (u?.id != null) return u;
    const cid = readCachedTelegramId();
    if (cid != null) return { id: cid };
    await new Promise((r) => setTimeout(r, step));
  }
  const cid = readCachedTelegramId();
  return cid != null ? { id: cid } : null;
}

/** Дольше ждём initData на ngrok/localhost — после «Visit» данные могут прийти с задержкой. */
function telegramIdWaitBudgetMs() {
  const h = String(window.location.hostname || "").toLowerCase();
  if (h.includes("ngrok") || h === "localhost" || h.endsWith(".local")) {
    return 28000;
  }
  return 12000;
}

function renderTelegramIdError() {
  const body = document.getElementById("quiz-body");
  if (!body) return;
  body.classList.remove("quiz-body--empty");
  const noWebApp = !window.Telegram?.WebApp;
  const line1 = noWebApp
    ? "Откройте квиз только из приложения Telegram (кнопка Mini App у бота). В обычном браузере профиль недоступен."
    : '<span class="err">Не удалось получить ваш Telegram ID</span>.';
  body.innerHTML = `
    <p class="muted" style="margin:0 0 12px">${line1}</p>
    <p class="muted" style="margin:0 0 12px">
      Закройте Mini App полностью и откройте снова кнопкой <b>Mini App</b> внизу чата или через <b>/app</b>.
      Если используете <b>ngrok</b>: на предупреждающей странице один раз нажмите <b>Visit</b>, затем снова откройте квиз из бота.
    </p>
    <button type="button" class="btn btn--ghost" id="btn-retry-telegram">Повторить попытку</button>
  `;
  document.getElementById("btn-retry-telegram")?.addEventListener("click", () => loadNextQuestion(), {
    once: true,
  });
}

function getSelectedGrade() {
  const active = document.querySelector('.grade-chip[aria-checked="true"]');
  return active?.dataset.grade ?? "medium";
}

function getSelectedTopic() {
  const active = document.querySelector('.topic-chip[aria-checked="true"]');
  return active?.dataset.topic ?? "python";
}

function setupRadioGroup(groupId, chipSelector) {
  const group = document.getElementById(groupId);
  if (!group) return;
  // Один querySelectorAll при инициализации; по клику O(n) по числу чипов в группе (n≈12) — дешево.
  const chips = Array.from(group.querySelectorAll(chipSelector));
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.setAttribute("aria-checked", c === chip ? "true" : "false"));
    });
  });
}

function setupGradeChips() {
  setupRadioGroup("grade-group", ".grade-chip");
}

function setupTopicChips() {
  setupRadioGroup("topic-group", ".topic-chip");
}

function setButtonLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  btn.classList.toggle("is-loading", loading);
  const sp = btn.querySelector(".btn__spinner");
  if (sp) sp.hidden = !loading;
}

function renderQuestion(data) {
  currentQuestionId = data.id;
  const body = document.getElementById("quiz-body");
  const opts = document.getElementById("quiz-options");
  const result = document.getElementById("quiz-result");
  if (result) {
    result.hidden = true;
    result.innerHTML = "";
  }
  if (body) {
    body.classList.remove("quiz-body--empty", "muted");
    body.innerHTML = `
      <div class="badge"><span class="dot"></span>${escapeHtml(GRADE_LABELS[data.grade] ?? data.grade)}</div>
      <div class="task-title">Вопрос №${data.question_number ?? data.id}</div>
      <div>${escapeHtml(data.question_text)}</div>
    `;
  }
  if (opts) {
    opts.hidden = false;
    opts.innerHTML = "";
    _optionBtns = [];
    const frag = document.createDocumentFragment();
    (data.options || []).forEach((text, index) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "option-btn";
      const num = document.createElement("span");
      num.className = "option-btn__num";
      num.textContent = String(index + 1);
      const label = document.createElement("span");
      label.textContent = text;
      btn.appendChild(num);
      btn.appendChild(label);
      btn.dataset.index = String(index);
      btn.addEventListener("click", () => submitAnswer(index));
      _optionBtns.push(btn);
      frag.appendChild(btn);
    });
    opts.appendChild(frag); // единый reflow вместо отдельных вставок по кнопке
  }
}

/** Кешируем кнопки вариантов после рендера — querySelectorAll только один раз за вопрос. */
let _optionBtns = [];

function setOptionsDisabled(disabled) {
  _optionBtns.forEach((b) => { b.disabled = disabled; });
}

function showThinking(resultEl) {
  if (!resultEl) return;
  resultEl.hidden = false;
  resultEl.className = "quiz-result";
  resultEl.innerHTML = `
    <div class="thinking">
      <div class="thinking__dots" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
      <p class="thinking__text">Нейросеть проверяет ответ…</p>
    </div>
  `;
}

async function submitAnswer(chosenIndex) {
  const telegramId = getTelegramId();
  if (telegramId == null || currentQuestionId == null || submitting) return;
  submitting = true;
  setOptionsDisabled(true);

  // Подсветить выбранную кнопку без повторного querySelectorAll
  if (_optionBtns[chosenIndex]) _optionBtns[chosenIndex].classList.add("is-chosen");

  const resultEl = document.getElementById("quiz-result");
  showThinking(resultEl);

  try {
    const data = await postJsonThenPollJob("/api/quiz/answer", {
      requireTelegramAuth: true,
      body: JSON.stringify({
        question_id: currentQuestionId,
        chosen_index: chosenIndex,
      }),
      pollTimeoutMs: 120000,
    });
    if (resultEl) {
      resultEl.hidden = false;
      const isOk = data.is_correct;
      const titleClass = isOk ? "ok" : "warn";
      const titleText = isOk ? "Верно!" : "Неверно";
      const scoreStr = data.score > 0 ? `+${data.score} очков` : `${data.score} очков`;
      resultEl.className = `quiz-result quiz-result--${isOk ? "ok" : "warn"}`;
      resultEl.innerHTML = `
        <p class="quiz-result__title ${titleClass}">${titleText}</p>
        <p class="muted" style="margin:0 0 8px">${escapeHtml(scoreStr)}</p>
        <p class="feedback">${escapeHtml(data.feedback)}</p>
      `;
    }
    if (tg?.HapticFeedback) {
      tg.HapticFeedback.notificationOccurred(data.is_correct ? "success" : "warning");
    }
  } catch (e) {
    if (resultEl) {
      resultEl.hidden = false;
      resultEl.className = "quiz-result";
      resultEl.innerHTML = `<p class="err">${escapeHtml(friendlyError(e))}</p>`;
    }
    if (tg?.HapticFeedback) {
      tg.HapticFeedback.notificationOccurred("error");
    }
  } finally {
    submitting = false;
  }
}

const GRADE_LABELS = {
  easy: "Лёгкий",
  medium: "Средний",
  expert: "Эксперт",
};

const TOPIC_LABELS = {
  python: "Python",
  data_structures: "Структуры данных",
  algorithms: "Алгоритмы",
};

function showGenerating(topic, grade) {
  const body = document.getElementById("quiz-body");
  const opts = document.getElementById("quiz-options");
  const result = document.getElementById("quiz-result");
  if (result) { result.hidden = true; result.innerHTML = ""; }
  if (opts) { opts.hidden = true; opts.innerHTML = ""; }
  if (!body) return;
  const topicLabel = TOPIC_LABELS[topic] ?? topic;
  const gradeLabel = GRADE_LABELS[grade] ?? grade;
  body.classList.remove("quiz-body--empty", "muted");
  body.innerHTML = `
    <div class="generating">
      <div class="generating__dots" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
      <p class="generating__text">
        ИИ генерирует вопрос<br>
        <span class="muted" style="font-size:13px">${escapeHtml(topicLabel)} · ${escapeHtml(gradeLabel)}</span>
      </p>
      <p class="generating__hint muted">Первый запрос может занять 10–30 секунд — модель прогревается</p>
    </div>
  `;
}

async function loadNextQuestion() {
  const btn = document.getElementById("btn-next");
  setButtonLoading(btn, true);
  const grade = getSelectedGrade();
  const topic = getSelectedTopic();
  showGenerating(topic, grade);
  try {
    const user = await ensureTelegramUser(telegramIdWaitBudgetMs());
    const telegramId = user?.id ?? null;
    if (telegramId == null) {
      renderTelegramIdError();
      return;
    }
    const data = await postJsonThenPollJob("/api/quiz/next", {
      timeoutMs: 120000,
      requireTelegramAuth: true,
      body: JSON.stringify({
        grade,
        topic,
      }),
      pollTimeoutMs: 120000,
    });
    renderQuestion(data);
  } catch (e) {
    currentQuestionId = null;
    const opts = document.getElementById("quiz-options");
    if (opts) { opts.hidden = true; opts.innerHTML = ""; }
    const body = document.getElementById("quiz-body");
    if (body) {
      body.classList.remove("quiz-body--empty");
      body.innerHTML = `<span class="err">${escapeHtml(friendlyError(e))}</span>`;
    }
  } finally {
    setButtonLoading(btn, false);
  }
}

let currentDailyTaskId = null;

async function loadDailyTask() {
  const btn = document.getElementById("btn-task-load");
  const body = document.getElementById("task-body");
  const editor = document.getElementById("task-editor");
  const result = document.getElementById("task-result");
  if (!body || !editor) return;
  setButtonLoading(btn, true);
  if (result) {
    result.hidden = true;
    result.innerHTML = "";
  }
  if (!collectRawInitData()) {
    body.classList.remove("muted");
    body.innerHTML = "<p>Нет данных Telegram. Откройте Mini App из бота.</p>";
    editor.hidden = true;
    currentDailyTaskId = null;
    setButtonLoading(btn, false);
    return;
  }
  try {
    const t = await fetchJson("/api/tasks/daily", { requireTelegramAuth: true });
    currentDailyTaskId = t.id;
    body.classList.remove("muted");
    body.innerHTML = `<p class="task-daily-meta">${escapeHtml(t.title)} · <span class="muted">${escapeHtml(
      String(t.difficulty || ""),
    )}</span></p><div class="task-desc">${escapeHtml(t.description)}</div>`;
    editor.hidden = false;
  } catch (e) {
    currentDailyTaskId = null;
    editor.hidden = true;
    const s = String(e);
    const msg = friendlyError(e);
    if (s.includes("404")) {
      body.innerHTML =
        "<p>Сегодня задача не назначена. Загляните позже или обратитесь к администратору.</p>";
    } else {
      body.innerHTML = `<p class="err">${escapeHtml(msg)}</p>`;
    }
  } finally {
    setButtonLoading(btn, false);
  }
}

async function submitDailyTask() {
  const btn = document.getElementById("btn-task-submit");
  const ta = document.getElementById("task-code");
  const result = document.getElementById("task-result");
  if (currentDailyTaskId == null || !ta) return;
  const code = ta.value || "";
  if (!code.trim()) return;
  setButtonLoading(btn, true);
  try {
    const data = await postJsonThenPollJob("/api/submissions/", {
      requireTelegramAuth: true,
      timeoutMs: 120000,
      body: JSON.stringify({
        task_id: currentDailyTaskId,
        code,
      }),
      pollTimeoutMs: 120000,
    });
    if (result) {
      result.hidden = false;
      result.className = "quiz-result";
      result.innerHTML = `<p class="muted">Оценка: <strong>${escapeHtml(String(data.score))}</strong></p><p class="feedback">${escapeHtml(data.feedback)}</p>`;
    }
  } catch (e) {
    if (result) {
      result.hidden = false;
      result.className = "quiz-result";
      result.innerHTML = `<p class="err">${escapeHtml(friendlyError(e))}</p>`;
    }
  } finally {
    setButtonLoading(btn, false);
  }
}

function setLeaderboardEmptyVisible(visible) {
  const el = document.getElementById("leaderboard-empty");
  const list = document.getElementById("leaderboard-list");
  if (el) el.hidden = !visible;
  if (list) {
    list.classList.toggle("leaderboard-list--empty", visible);
  }
}

async function loadLeaderboard() {
  const list = document.getElementById("leaderboard-list");
  const btn = document.getElementById("btn-leaderboard");
  if (!list) return;
  setButtonLoading(btn, true);
  try {
    const rows = await fetchJson("/api/leaderboard?limit=10");
    if (!rows.length) {
      list.innerHTML = "";
      setLeaderboardEmptyVisible(true);
      return;
    }
    setLeaderboardEmptyVisible(false);
    list.innerHTML = rows
      .map(
        (r) =>
          `<li><span class="lb-rank">#${r.rank}</span> <span class="lb-name">${escapeHtml(
            r.username || `id ${r.telegram_id}`,
          )}</span> <span class="lb-score">${r.score}</span></li>`,
      )
      .join("");
  } catch (e) {
    setLeaderboardEmptyVisible(false);
    list.innerHTML = `<li class="err">${escapeHtml(friendlyError(e))}</li>`;
  } finally {
    setButtonLoading(btn, false);
  }
}

async function main() {
  applyTheme();
  setupGradeChips();
  setupTopicChips();

  /** На части клиентов initData дозаполняется после первого кадра. */
  let user = getTelegramUser();
  if (!user && tg) {
    user = await ensureTelegramUser(2500);
  }

  const hint = document.getElementById("hint");
  if (hint) {
    hint.textContent = tg
      ? "Квиз и задача дня — кнопки ниже. Нужен вход через Telegram."
      : "Откройте страницу по кнопке Web App в боте (нужен HTTPS).";
  }

  if (user) {
    const uname = user.username ? `@${user.username}` : "без username";
    const name = [user.first_name, user.last_name].filter(Boolean).join(" ") || "Игрок";
    setText("user-line", `${escapeHtml(name)} · ${escapeHtml(uname)}`);
  } else {
    const cid = readCachedTelegramId();
    if (cid != null && tg) {
      setText("user-line", `Игрок · id ${escapeHtml(String(cid))}`);
    } else {
      setText(
        "user-line",
        tg
          ? "Профиль не подхватился — смахните Mini App вниз и откройте снова из бота."
          : "Профиль Telegram недоступен — откройте в приложении Telegram.",
      );
    }
  }

  const healthDot = document.getElementById("health-dot");
  try {
    const health = await fetchJson("/api/health");
    const ok = health.status === "ok";
    const pg = health.postgres === "ok";
    const rd = health.redis === "ok";
    setText(
      "health-line",
      `${ok ? '<span class="ok">OK</span>' : '<span class="warn">Degraded</span>'} · v${escapeHtml(
        health.version,
      )} · PG ${pg ? "✓" : "✗"} · Redis ${rd ? "✓" : "✗"}`,
    );
    healthDot?.classList.toggle("is-ok", ok);
    healthDot?.classList.toggle("is-err", !ok);
  } catch (e) {
    setText("health-line", `<span class="err">Нет связи</span> · ${escapeHtml(friendlyError(e))}`);
    healthDot?.classList.add("is-err");
    healthDot?.classList.remove("is-ok");
  }

  document.getElementById("btn-next")?.addEventListener("click", () => loadNextQuestion());
  document.getElementById("btn-leaderboard")?.addEventListener("click", () => loadLeaderboard());
  document.getElementById("btn-task-load")?.addEventListener("click", () => loadDailyTask());
  document.getElementById("btn-task-submit")?.addEventListener("click", () => submitDailyTask());

  await loadLeaderboard();
}

main().catch((e) => {
  console.error(e);
  const body = document.getElementById("quiz-body");
  if (body) {
    body.classList.remove("quiz-body--empty");
    body.innerHTML = `<span class="err">${escapeHtml(friendlyError(e))}</span>`;
  }
});
