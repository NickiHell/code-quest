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

async function loadStats() {
  const key = localStorage.getItem(KEY_STORAGE) || ($("admin-key") && $("admin-key").value);
  if (!key || !key.trim()) {
    setHint("Сначала введите и сохраните ключ.", true);
    return;
  }
  setHint("Загрузка…");
  try {
    const res = await fetch("/api/admin/stats", {
      headers: {
        Accept: "application/json",
        "X-Admin-Key": key.trim(),
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
}

init();
