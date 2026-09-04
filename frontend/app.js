const API = "/api";

async function api(path, method = "GET", body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(API + path, opts);
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json() : null;
  if (!res.ok) {
    const msg = (data && data.detail) || res.statusText;
    throw new Error(msg);
  }
  return data;
}

function esc(s) {
  return (s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function checkHealth() {
  const el = document.getElementById("health");
  try {
    await api("/health");
    el.textContent = "online";
    el.className = "pill ok";
  } catch (e) {
    el.textContent = "offline";
    el.className = "pill err";
  }
}

async function loadMemories() {
  const activeOnly = document.getElementById("active-only").checked;
  const rows = await api(`/memories?active_only=${activeOnly}`);
  const tbody = document.querySelector("#memory-table tbody");
  tbody.innerHTML = "";
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:#999;">No memories yet - teach Kivi something above.</td></tr>`;
    return;
  }
  for (const m of rows) {
    const tr = document.createElement("tr");
    const statusClass = m.active ? "status-active" : "status-candidate";
    const statusText = m.active ? "active" : "candidate";
    tr.innerHTML = `
      <td>${esc(m.observed_form)}</td>
      <td><b>${esc(m.canonical_form)}</b></td>
      <td>${esc(m.entity_type)}</td>
      <td class="${statusClass}">${statusText}</td>
      <td>${m.evidence_count}</td>
      <td>${m.confidence.toFixed(2)}</td>
      <td class="row-actions"><button class="secondary" data-del="${m.id}">Delete</button></td>
    `;
    tbody.appendChild(tr);
  }
  tbody.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/memories/${btn.dataset.del}`, "DELETE");
      loadMemories();
    });
  });
}

async function submitObservation() {
  const asr = document.getElementById("obs-asr").value.trim();
  const corrected = document.getElementById("obs-corrected").value.trim();
  const resultEl = document.getElementById("learn-result");
  if (!asr || !corrected) {
    resultEl.innerHTML = `<div class="row-result skipped">Enter both ASR output and corrected output.</div>`;
    return;
  }
  try {
    const data = await api("/observe", "POST", { asr, corrected });
    let html = `<div style="font-size:12px;color:#888;margin-bottom:6px;">formatted baseline: "${esc(data.formatted_baseline)}"</div>`;
    if (data.learned.length === 0) {
      html += `<div class="row-result skipped">Nothing new learned - corrected text matched the formatted baseline.</div>`;
    }
    for (const l of data.learned) {
      html += `<div class="row-result learned">learned: <b>${esc(l.observed_form)}</b> &rarr; <b>${esc(l.canonical_form)}</b> &mdash; ${l.status} (${l.evidence_count} obs, confidence ${l.confidence.toFixed(2)}, ${l.active ? "active" : "not yet active"})</div>`;
    }
    resultEl.innerHTML = html;
    loadMemories();
  } catch (e) {
    resultEl.innerHTML = `<div class="row-result skipped">Error: ${esc(e.message)}</div>`;
  }
}

function renderRunResult(data) {
  const el = document.getElementById("run-result");
  let html = `<div class="out-line">Formatted: ${esc(data.formatted)}</div>`;

  let awareHtml = esc(data.memory_aware);
  for (const iv of data.interventions) {
    const re = new RegExp(esc(iv.applied).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    awareHtml = awareHtml.replace(re, `<mark title="${esc(iv.explanation)}">${esc(iv.applied)}</mark>`);
  }
  html += `<div class="out-line">Memory-aware: <b>${awareHtml}</b></div>`;

  html += `<div style="margin-top:10px;font-size:12px;color:#888;">latency: ${data.latency_ms.toFixed(2)}ms</div>`;

  html += `<div style="margin-top:8px;"><b style="font-size:13px;">Explanation</b>`;
  if (data.interventions.length === 0 && data.non_interventions.length === 0) {
    html += `<div class="explain no_intervene">No memory matched anything in this transcript.</div>`;
  }
  for (const iv of data.interventions) {
    html += `<div class="explain intervene">&#10003; ${esc(iv.explanation)}</div>`;
  }
  for (const ni of data.non_interventions) {
    html += `<div class="explain no_intervene">&mdash; ${esc(ni.explanation)}</div>`;
  }
  html += `</div>`;

  el.innerHTML = html;
}

async function runTranscript() {
  const asr = document.getElementById("run-asr").value.trim();
  const el = document.getElementById("run-result");
  if (!asr) {
    el.innerHTML = `<div class="explain no_intervene">Enter an ASR transcript to run.</div>`;
    return;
  }
  try {
    const data = await api("/run", "POST", { asr });
    renderRunResult(data);
  } catch (e) {
    el.innerHTML = `<div class="explain no_intervene">Error: ${esc(e.message)}</div>`;
  }
}

function getBulkMode() {
  return document.getElementById("bulk-mode-conversations").checked ? "conversations" : "pairs";
}

function updateBulkModePanels() {
  const mode = getBulkMode();
  document.getElementById("bulk-mode-pairs-panel").hidden = mode !== "pairs";
  document.getElementById("bulk-mode-conversations-panel").hidden = mode !== "conversations";
}

async function submitBulkPairsMode(resultEl) {
  const raw = document.getElementById("bulk-pairs").value.trim();
  if (!raw) {
    resultEl.innerHTML = `<div class="row-result skipped">Paste one JSON pair per line.</div>`;
    return;
  }

  const lines = raw.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
  const observations = [];
  const parseErrors = [];
  for (let i = 0; i < lines.length; i++) {
    try {
      const obj = JSON.parse(lines[i]);
      observations.push({ asr: obj.asr ?? "", corrected: obj.corrected ?? "" });
    } catch (e) {
      parseErrors.push(`Line ${i + 1}: invalid JSON - ${e.message}`);
    }
  }

  if (observations.length === 0) {
    resultEl.innerHTML = parseErrors.map((m) => `<div class="row-result skipped">${esc(m)}</div>`).join("");
    return;
  }

  try {
    const data = await api("/observe/bulk", "POST", { observations });
    let html = parseErrors.map((m) => `<div class="row-result skipped">${esc(m)}</div>`).join("");
    for (const r of data.results) {
      if (r.error) {
        html += `<div class="row-result skipped">pair ${r.pair_index + 1}: ${esc(r.error)}</div>`;
        continue;
      }
      if (r.learned.length === 0) {
        html += `<div class="row-result skipped">pair ${r.pair_index + 1}: nothing new learned - corrected text matched the formatted baseline.</div>`;
      }
      for (const l of r.learned) {
        html += `<div class="row-result learned">pair ${r.pair_index + 1}: <b>${esc(l.observed_form)}</b> &rarr; <b>${esc(l.canonical_form)}</b> &mdash; ${l.status} (${l.evidence_count} obs, confidence ${l.confidence.toFixed(2)}, ${l.active ? "active" : "not yet active"})</div>`;
      }
    }
    resultEl.innerHTML = html;
    loadMemories();
  } catch (e) {
    resultEl.innerHTML = `<div class="row-result skipped">Error: ${esc(e.message)}</div>`;
  }
}

async function submitBulkConversationsMode(resultEl) {
  const raw = document.getElementById("bulk-conversations").value.trim();
  if (!raw) {
    resultEl.innerHTML = `<div class="row-result skipped">Paste one or more corrected conversation transcripts.</div>`;
    return;
  }

  const conversations = raw.split(/\n\s*\n/).map((c) => c.trim()).filter((c) => c.length > 0);

  try {
    const data = await api("/learn-from-conversations", "POST", { conversations });
    let html = "";
    for (const r of data.results) {
      if (r.error) {
        html += `<div class="row-result skipped">conversation ${r.conversation_index + 1}: ${esc(r.error)}</div>`;
        continue;
      }
      if (r.learned.length === 0) {
        html += `<div class="row-result skipped">conversation ${r.conversation_index + 1}: no personal entities found.</div>`;
      }
      for (const l of r.learned) {
        html += `<div class="row-result learned">conversation ${r.conversation_index + 1}: <b>${esc(l.observed_form)}</b> &rarr; <b>${esc(l.canonical_form)}</b> (${esc(l.entity_type)}, via ${esc(l.sources.join("+"))}) &mdash; ${l.status} (${l.evidence_count} obs, confidence ${l.confidence.toFixed(2)}, ${l.active ? "active" : "not yet active"})</div>`;
      }
    }
    resultEl.innerHTML = html;
    loadMemories();
  } catch (e) {
    resultEl.innerHTML = `<div class="row-result skipped">${esc(e.message)}</div>`;
  }
}

async function submitBulk() {
  const resultEl = document.getElementById("bulk-learn-result");
  if (getBulkMode() === "conversations") {
    await submitBulkConversationsMode(resultEl);
  } else {
    await submitBulkPairsMode(resultEl);
  }
}

async function resetSystem() {
  if (!confirm("Reset all memory? This cannot be undone.")) return;
  const data = await api("/reset", "POST");
  document.getElementById("learn-result").innerHTML = "";
  document.getElementById("run-result").innerHTML = "";
  alert(`Reset complete: ${data.memories_deleted} memories, ${data.evidence_deleted} evidence rows deleted.`);
  loadMemories();
}

document.getElementById("btn-learn").addEventListener("click", submitObservation);
document.getElementById("btn-bulk-learn").addEventListener("click", submitBulk);
document.getElementById("bulk-mode-pairs").addEventListener("change", updateBulkModePanels);
document.getElementById("bulk-mode-conversations").addEventListener("change", updateBulkModePanels);
document.getElementById("btn-run").addEventListener("click", runTranscript);
document.getElementById("btn-reset").addEventListener("click", resetSystem);
document.getElementById("active-only").addEventListener("change", loadMemories);

checkHealth();
loadMemories();
