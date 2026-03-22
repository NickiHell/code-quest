/**
 * Code Quest Mini App — MCQ: грейд, 10 вариантов, ответ, лидерборд.
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

async function fetchJson(path, options = {}) {
  const { headers: userHeaders, timeoutMs, ...rest } = options;
  const hasBody = rest.body != null && String(rest.method || "GET").toUpperCase() !== "GET";
  const ctrl = new AbortController();
  const t =
    typeof timeoutMs === "number" && timeoutMs > 0
      ? setTimeout(() => ctrl.abort(), timeoutMs)
      : null;
  const res = await fetch(path, {
    ...rest,
    signal: ctrl.signal,
    headers: {
      Accept: "application/json",
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...userHeaders,
    },
  }).finally(() => {
    if (t) clearTimeout(t);
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
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
    return "Долгий ответ сервера (таймаут). Подождите или проверьте Ollama на машине.";
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
function parseUserFromInitData(raw) {
  if (!raw || typeof raw !== "string") return null;
  try {
    const params = new URLSearchParams(raw);
    const userJson = params.get("user");
    if (!userJson) return null;
    return JSON.parse(userJson);
  } catch {
    return null;
  }
}

/**
 * Иногда initData приходит в URL (query / hash), а не в WebApp.initData.
 */
function collectRawInitData() {
  if (tg?.initData) return tg.initData;
  try {
    const sp = window.location.search.slice(1);
    if (sp && (sp.startsWith("query_id=") || sp.startsWith("user="))) {
      return sp;
    }
    const q = new URLSearchParams(window.location.search);
    const embedded = q.get("tgWebAppData");
    if (embedded) {
      return decodeURIComponent(embedded);
    }
  } catch (_) {
    /* ignore */
  }
  try {
    const h = window.location.hash.slice(1);
    if (!h) return "";
    if (h.includes("user=") || h.includes("query_id=")) {
      const q = new URLSearchParams(h);
      const embedded = q.get("tgWebAppData");
      if (embedded) return decodeURIComponent(embedded);
      return h;
    }
  } catch (_) {
    /* ignore */
  }
  return "";
}

/**
 * Разбирает initData один раз и кеширует результат в _cachedUser.
 * Повторные вызовы просто возвращают кеш — без URLSearchParams/JSON.parse.
 */
function getTelegramUser() {
  if (!tg) return null;
  if (_cachedUser) return _cachedUser;

  const fromUnsafe = tg.initDataUnsafe?.user;
  if (fromUnsafe?.id != null) {
    _cachedUser = fromUnsafe;
    persistTelegramId(fromUnsafe.id);
    return _cachedUser;
  }

  const raw = collectRawInitData();
  const parsed = parseUserFromInitData(raw) ?? parseUserFromInitData(tg.initData);
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
async function ensureTelegramUser(maxMs = 3500) {
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

function getSelectedGrade() {
  const active = document.querySelector('.grade-chip[aria-checked="true"]');
  return active?.dataset.grade ?? "middle";
}

function getSelectedTopic() {
  const active = document.querySelector('.topic-chip[aria-checked="true"]');
  return active?.dataset.topic ?? "python";
}

function setupRadioGroup(groupId, chipSelector) {
  const group = document.getElementById(groupId);
  if (!group) return;
  // Кешируем NodeList один раз — querySelectorAll при каждом клике не нужен
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
      <div class="badge"><span class="dot"></span>${escapeHtml(data.grade)}</div>
      <div class="task-title">Вопрос №${data.id}</div>
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
    opts.appendChild(frag); // единый reflow вместо 10 отдельных
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
    const data = await fetchJson("/api/quiz/answer", {
      method: "POST",
      body: JSON.stringify({
        telegram_id: telegramId,
        question_id: currentQuestionId,
        chosen_index: chosenIndex,
      }),
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

const TOPIC_LABELS = {
  python: "Python",
  algorithms: "Алгоритмы",
  data_structures: "Структуры данных",
};

function showGenerating(topic, grade) {
  const body = document.getElementById("quiz-body");
  const opts = document.getElementById("quiz-options");
  const result = document.getElementById("quiz-result");
  if (result) { result.hidden = true; result.innerHTML = ""; }
  if (opts) { opts.hidden = true; opts.innerHTML = ""; }
  if (!body) return;
  const topicLabel = TOPIC_LABELS[topic] ?? topic;
  body.classList.remove("quiz-body--empty", "muted");
  body.innerHTML = `
    <div class="generating">
      <div class="generating__dots" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
      <p class="generating__text">
        ИИ генерирует вопрос<br>
        <span class="muted" style="font-size:13px">${escapeHtml(topicLabel)} · ${escapeHtml(grade)}</span>
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
    const user = await ensureTelegramUser();
    const telegramId = user?.id ?? null;
    if (telegramId == null) {
      const body = document.getElementById("quiz-body");
      if (body) {
        body.classList.remove("quiz-body--empty");
        body.innerHTML =
          '<span class="err">Не удалось получить ваш Telegram ID</span>. Откройте Mini App кнопкой «Открыть приложение» / Web App в чате с ботом.';
      }
      return;
    }
    const data = await fetchJson("/api/quiz/next", {
      method: "POST",
      timeoutMs: 120000,
      body: JSON.stringify({
        telegram_id: telegramId,
        username: user?.username ?? null,
        grade,
        topic,
      }),
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

  /** На части Android initData появляется после первого кадра — ждём до 500 мс. */
  let user = getTelegramUser();
  if (!user && tg) {
    user = await ensureTelegramUser(500);
  }

  const hint = document.getElementById("hint");
  if (hint) {
    hint.textContent = tg
      ? "Вы в Telegram — жми «Новый вопрос», когда будешь готов."
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
    setText(
      "health-line",
      `<span class="ok">OK</span> · v${escapeHtml(health.version)}`,
    );
    healthDot?.classList.add("is-ok");
    healthDot?.classList.remove("is-err");
  } catch (e) {
    setText("health-line", `<span class="err">Нет связи</span> · ${escapeHtml(friendlyError(e))}`);
    healthDot?.classList.add("is-err");
    healthDot?.classList.remove("is-ok");
  }

  document.getElementById("btn-next")?.addEventListener("click", () => loadNextQuestion());
  document.getElementById("btn-leaderboard")?.addEventListener("click", () => loadLeaderboard());

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
