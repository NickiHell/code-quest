const KEY_STORAGE = "codequest_admin_key";

function $(id) {
  return document.getElementById(id);
}

function setHint(text, isError = false) {
  const el = $("auth-hint");
  if (!el) return;
  el.textContent = text;
  el.style.color = isError ? "#b91c1c" : "#64748b";
}

function setAiHint(text, isError = false) {
  const el = $("ai-hint");
  if (!el) return;
  el.textContent = text;
  el.style.color = isError ? "#b91c1c" : "#64748b";
}

function getAdminKey() {
  return (localStorage.getItem(KEY_STORAGE) || ($("admin-key") && $("admin-key").value) || "").trim();
}

async function loadAiBackend() {
  const key = getAdminKey();
  if (!key) {
    setAiHint("Сначала введите и сохраните ключ доступа.", true);
    return;
  }
  setAiHint("Загрузка…");
  try {
    const res = await fetch("/api/admin/ai-backend", {
      headers: {
        Accept: "application/json",
        "X-Admin-Key": key,
      },
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`${res.status} ${t}`);
    }
    const data = await res.json();
    const sel = $("ai-select");
    const status = $("ai-status");
    if (sel) {
      sel.innerHTML = "";
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "— выберите бэкенд —";
      sel.appendChild(placeholder);
      for (const name of data.available || []) {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        if (name === data.effective) opt.selected = true;
        sel.appendChild(opt);
      }
    }
    if (status) {
      status.hidden = false;
      status.innerHTML = `
        <div><strong>Из .env:</strong> <code>${escapeHtml(data.env_default)}</code></div>
        <div><strong>Override (Redis):</strong> ${data.override ? `<code>${escapeHtml(data.override)}</code>` : "—"}</div>
        <div><strong>Сейчас:</strong> <code>${escapeHtml(data.effective || "—")}</code> ${data.ready ? "✓" : "✗"}</div>
      `;
    }
    setAiHint("Готово.");
  } catch (e) {
    console.error(e);
    setAiHint(String(e), true);
  }
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function applyAiBackend() {
  const key = getAdminKey();
  if (!key) {
    setAiHint("Сначала введите и сохраните ключ.", true);
    return;
  }
  const sel = $("ai-select");
  const v = sel && sel.value;
  if (!v) {
    setAiHint("Выберите бэкенд в списке.", true);
    return;
  }
  setAiHint("Применение…");
  try {
    const res = await fetch("/api/admin/ai-backend", {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Admin-Key": key,
      },
      body: JSON.stringify({ backend: v }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`${res.status} ${t}`);
    }
    await loadAiBackend();
    setAiHint("Переключение сохранено в Redis.");
  } catch (e) {
    console.error(e);
    setAiHint(String(e), true);
  }
}

async function clearAiOverride() {
  const key = getAdminKey();
  if (!key) {
    setAiHint("Сначала введите и сохраните ключ.", true);
    return;
  }
  setAiHint("Сброс…");
  try {
    const res = await fetch("/api/admin/ai-backend", {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Admin-Key": key,
      },
      body: JSON.stringify({ clear: true }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`${res.status} ${t}`);
    }
    await loadAiBackend();
    setAiHint("Override сброшен, используется AI_BACKEND из env.");
  } catch (e) {
    console.error(e);
    setAiHint(String(e), true);
  }
}

async function loadStats() {
  const key = getAdminKey();
  if (!key) {
    setHint("Сначала введите и сохраните ключ.", true);
    return;
  }
  setHint("Загрузка…");
  try {
    const res = await fetch("/api/admin/stats", {
      headers: {
        Accept: "application/json",
        "X-Admin-Key": key,
      },
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`${res.status} ${t}`);
    }
    const data = await res.json();
    const list = $("stats-list");
    list.innerHTML = "";
    const rows = [
      ["Пользователи", data.users],
      ["Задачи", data.tasks],
      ["Отправки", data.submissions],
    ];
    for (const [k, v] of rows) {
      const li = document.createElement("li");
      li.textContent = `${k}: ${v}`;
      list.appendChild(li);
    }
    $("leaderboard").textContent = JSON.stringify(data.leaderboard_top, null, 2);
    $("stats-card").hidden = false;
    setHint("Готово.");
  } catch (e) {
    console.error(e);
    setHint(String(e), true);
  }
}

function init() {
  const saved = localStorage.getItem(KEY_STORAGE);
  if (saved && $("admin-key")) {
    $("admin-key").value = saved;
  }
  $("save-key")?.addEventListener("click", () => {
    const v = $("admin-key")?.value?.trim() || "";
    if (!v) {
      localStorage.removeItem(KEY_STORAGE);
      setHint("Ключ очищен.", true);
      return;
    }
    localStorage.setItem(KEY_STORAGE, v);
    setHint("Ключ сохранён локально в браузере.");
  });
  $("load-stats")?.addEventListener("click", loadStats);
  $("load-ai")?.addEventListener("click", loadAiBackend);
  $("apply-ai")?.addEventListener("click", applyAiBackend);
  $("clear-ai")?.addEventListener("click", clearAiOverride);
}

init();
