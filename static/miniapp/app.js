/**
 * Code Quest Mini App — MCQ: грейд, 10 вариантов, ответ, лидерборд.
 */

const tg = window.Telegram?.WebApp;

let currentQuestionId = null;
let submitting = false;

function applyTheme() {
  if (!tg) return;
  tg.ready();
  tg.expand();
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
  const { headers: userHeaders, ...rest } = options;
  const hasBody = rest.body != null && String(rest.method || "GET").toUpperCase() !== "GET";
  const res = await fetch(path, {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...userHeaders,
    },
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
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
    return "Нет связи с сервером. Проверьте интернет и попробуйте снова.";
  }
  return msg;
}

function getTelegramUser() {
  return tg?.initDataUnsafe?.user ?? null;
}

function getTelegramId() {
  const u = getTelegramUser();
  return u?.id ?? null;
}

function getSelectedGrade() {
  const active = document.querySelector('.grade-chip[aria-checked="true"]');
  return active?.dataset.grade ?? "middle";
}

function setupGradeChips() {
  const group = document.getElementById("grade-group");
  if (!group) return;
  group.querySelectorAll(".grade-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      group.querySelectorAll(".grade-chip").forEach((c) => {
        c.setAttribute("aria-checked", c === chip ? "true" : "false");
      });
    });
  });
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
      opts.appendChild(btn);
    });
  }
}

function setOptionsDisabled(disabled) {
  document.querySelectorAll(".option-btn").forEach((b) => {
    b.disabled = disabled;
  });
}

async function submitAnswer(chosenIndex) {
  const telegramId = getTelegramId();
  if (telegramId == null || currentQuestionId == null || submitting) return;
  submitting = true;
  setOptionsDisabled(true);
  const resultEl = document.getElementById("quiz-result");
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
      const titleClass = data.is_correct ? "ok" : "warn";
      const titleText = data.is_correct ? "Отлично, верно!" : "Почти — неверно";
      resultEl.innerHTML = `
        <p class="quiz-result__title ${titleClass}">${titleText}</p>
        <p class="muted" style="margin:0 0 8px">+${escapeHtml(String(data.score))} очков</p>
        <p class="feedback">${escapeHtml(data.feedback)}</p>
      `;
    }
    if (tg?.HapticFeedback) {
      tg.HapticFeedback.notificationOccurred(data.is_correct ? "success" : "warning");
    }
  } catch (e) {
    if (resultEl) {
      resultEl.hidden = false;
      resultEl.innerHTML = `<p class="err">${escapeHtml(friendlyError(e))}</p>`;
    }
    if (tg?.HapticFeedback) {
      tg.HapticFeedback.notificationOccurred("error");
    }
  } finally {
    submitting = false;
  }
}

async function loadNextQuestion() {
  const telegramId = getTelegramId();
  if (telegramId == null) {
    const body = document.getElementById("quiz-body");
    if (body) {
      body.classList.remove("quiz-body--empty");
      body.innerHTML =
        '<span class="err">Нужен Telegram WebApp</span> — откройте приложение из бота.';
    }
    return;
  }
  const grade = getSelectedGrade();
  const user = getTelegramUser();
  const btn = document.getElementById("btn-next");
  setButtonLoading(btn, true);
  try {
    const data = await fetchJson("/api/quiz/next", {
      method: "POST",
      body: JSON.stringify({
        telegram_id: telegramId,
        username: user?.username ?? null,
        grade,
        topic: null,
      }),
    });
    renderQuestion(data);
  } catch (e) {
    currentQuestionId = null;
    const opts = document.getElementById("quiz-options");
    if (opts) {
      opts.hidden = true;
      opts.innerHTML = "";
    }
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

  const hint = document.getElementById("hint");
  if (hint) {
    hint.textContent = tg
      ? "Вы в Telegram — жми «Новый вопрос», когда будешь готов."
      : "Откройте страницу по кнопке Web App в боте (нужен HTTPS).";
  }

  const user = getTelegramUser();
  if (user) {
    const uname = user.username ? `@${user.username}` : "без username";
    const name = [user.first_name, user.last_name].filter(Boolean).join(" ") || "Игрок";
    setText("user-line", `${escapeHtml(name)} · ${escapeHtml(uname)}`);
  } else {
    setText("user-line", "Профиль Telegram недоступен — откройте в приложении Telegram.");
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
