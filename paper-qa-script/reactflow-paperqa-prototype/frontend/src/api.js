export async function runStep(apiBase, payload) {
  const res = await fetch(`${apiBase}/api/run_step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function newSession(apiBase) {
  const res = await fetch(`${apiBase}/api/new_session`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function resetSession(apiBase, sessionId) {
  const res = await fetch(`${apiBase}/api/reset_session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function translatePreview(apiBase, payload) {
  const res = await fetch(`${apiBase}/api/translate_preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}
