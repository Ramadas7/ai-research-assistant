const state = {
  documents: [],
  selectedDocIds: [],
  compareModeActive: false,
  currentSessionId: null,
};

const el = (id) => document.getElementById(id);

// ---------- View switching ----------

function switchView(view) {
  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  document.querySelectorAll(".nav-item[data-view]").forEach((n) => n.classList.remove("active"));

  el(`view-${view}`).classList.remove("hidden");
  const navBtn = document.querySelector(`.nav-item[data-view="${view}"]`);
  if (navBtn) navBtn.classList.add("active");

  if (view === "history") loadHistory();
}

document.querySelectorAll(".nav-item[data-view]").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

// ---------- Documents ----------

async function fetchDocuments() {
  const res = await fetch("/api/documents");
  state.documents = await res.json();
  renderDocList();
}

function renderDocList() {
  const container = el("doc-list");
  if (state.documents.length === 0) {
    container.innerHTML = `<p class="doc-empty">No documents yet — upload one to get started.</p>`;
    el("mode-hint").classList.add("hidden");
    return;
  }

  container.innerHTML = state.documents.map((doc) => {
    const checked = state.selectedDocIds.includes(doc.id) ? "checked" : "";
    const tags = [];
    if (doc.has_tables) tags.push("tables");
    if (doc.has_images) tags.push("figures");
    const tagStr = tags.length ? ` · ${tags.join(", ")}` : "";
    return `
      <div class="doc-item">
        <input type="checkbox" data-doc-id="${doc.id}" ${checked}>
        <div>
          <div class="doc-item-name">${doc.filename}</div>
          <div class="doc-item-meta">${doc.size_mb} MB · ${doc.num_chunks} chunks${tagStr}</div>
        </div>
        <button class="doc-item-delete" data-delete-doc="${doc.id}" title="Remove document">✕</button>
      </div>`;
  }).join("");

  container.querySelectorAll("input[type=checkbox]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const id = cb.dataset.docId;
      if (cb.checked) state.selectedDocIds.push(id);
      else state.selectedDocIds = state.selectedDocIds.filter((d) => d !== id);
      updateModeHint();
    });
  });

  container.querySelectorAll("[data-delete-doc]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = btn.dataset.deleteDoc;
      await fetch(`/api/documents/${id}`, { method: "DELETE" });
      state.selectedDocIds = state.selectedDocIds.filter((d) => d !== id);
      await fetchDocuments();
    });
  });

  updateModeHint();
}

function updateModeHint() {
  const hint = el("mode-hint");
  const compareBtn = el("btn-compare");
  if (state.selectedDocIds.length >= 2) {
    hint.textContent = state.compareModeActive
      ? "Compare mode ON — your next question will be answered per-document, then contrasted."
      : "2+ documents selected. Ask normally to search across both, or click \"Compare selected\".";
    hint.classList.remove("hidden");
    compareBtn.classList.remove("hidden");
  } else {
    hint.classList.add("hidden");
    compareBtn.classList.add("hidden");
    state.compareModeActive = false;
    compareBtn.textContent = "Compare selected";
  }
}

async function handleUpload(file) {
  const statusEl = el("upload-status");
  statusEl.classList.remove("hidden", "error", "success");
  statusEl.textContent = `Processing ${file.name}... this can take a minute for scanned pages or figures.`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/documents/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");

    statusEl.classList.add("success");
    statusEl.textContent = `✓ ${data.filename} processed — ${data.num_pages} pages, ${data.num_chunks} chunks indexed.`;

    await fetchDocuments();
    state.selectedDocIds = [data.id];
    renderDocList();
    startNewChat();
    switchView("chat");
  } catch (err) {
    statusEl.classList.add("error");
    statusEl.textContent = `✕ ${err.message}`;
  }
}

el("file-input").addEventListener("change", (e) => {
  if (e.target.files[0]) handleUpload(e.target.files[0]);
});

const dropzone = el("dropzone");
["dragover", "dragenter"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("drag-over"); })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("drag-over"); })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file && file.type === "application/pdf") handleUpload(file);
});

// ---------- Chat ----------

function renderMessage(role, content, sources = [], timestamp = null) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const time = timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                          : new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const sourcesHtml = sources.length
    ? `<div class="sources">${sources.map(s =>
        `<div class="source-chip">${s.doc} · page ${s.page} · ${s.type}</div>`).join("")}</div>`
    : "";

  wrap.innerHTML = `
    <div class="msg-avatar">${role === "user" ? "🧑" : "🤖"}</div>
    <div>
      <div class="msg-bubble">${
        role === "assistant" ? renderMarkdown(content) : escapeHtml(content).replace(/\n/g, "<br>")
      }${sourcesHtml}</div>
      <div class="msg-time">${time}</div>
    </div>`;
  el("messages").appendChild(wrap);
  el("messages").scrollTop = el("messages").scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function inlineFormat(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

// Small dependency-free Markdown renderer - handles what LLM answers actually
// use in practice: headers, bold/italic/inline code, fenced code blocks, and
// bullet/numbered lists. Input is escaped first, so this is injection-safe.
function renderMarkdown(raw) {
  const lines = escapeHtml(raw).split("\n");
  let html = "";
  let inCode = false;
  let codeBuffer = [];
  let listType = null;
  let paragraphBuffer = [];

  const flushParagraph = () => {
    if (paragraphBuffer.length) {
      html += `<p>${inlineFormat(paragraphBuffer.join(" "))}</p>`;
      paragraphBuffer = [];
    }
  };
  const closeList = () => {
    if (listType) { html += `</${listType}>`; listType = null; }
  };

  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (!inCode) { flushParagraph(); closeList(); inCode = true; codeBuffer = []; }
      else { html += `<pre><code>${codeBuffer.join("\n")}</code></pre>`; inCode = false; }
      continue;
    }
    if (inCode) { codeBuffer.push(line); continue; }

    const headerMatch = line.match(/^(#{1,6})\s+(.*)/);
    if (headerMatch) {
      flushParagraph(); closeList();
      const level = headerMatch[1].length;
      html += `<h${level}>${inlineFormat(headerMatch[2])}</h${level}>`;
      continue;
    }

    const ulMatch = line.match(/^[-*]\s+(.*)/);
    const olMatch = line.match(/^\d+\.\s+(.*)/);
    if (ulMatch) {
      flushParagraph();
      if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
      html += `<li>${inlineFormat(ulMatch[1])}</li>`;
      continue;
    }
    if (olMatch) {
      flushParagraph();
      if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
      html += `<li>${inlineFormat(olMatch[1])}</li>`;
      continue;
    }

    if (line.trim() === "") { flushParagraph(); closeList(); continue; }
    paragraphBuffer.push(line.trim());
  }
  flushParagraph();
  closeList();
  if (inCode) html += `<pre><code>${codeBuffer.join("\n")}</code></pre>`;
  return html;
}

function startNewChat() {
  state.currentSessionId = null;
  el("messages").innerHTML = "";
  el("chat-title").textContent = state.selectedDocIds.length > 1 ? "Chat with Documents" : "Chat with Document";
  el("chat-subtitle").textContent = "Ask anything about your document(s)";
}

el("btn-new-chat").addEventListener("click", startNewChat);

el("btn-compare").addEventListener("click", () => {
  state.compareModeActive = !state.compareModeActive;
  el("btn-compare").textContent = state.compareModeActive ? "✓ Compare mode on" : "Compare selected";
  updateModeHint();
  el("chat-input").focus();
});

el("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = el("chat-input");
  const question = input.value.trim();
  if (!question) return;
  if (state.selectedDocIds.length === 0) {
    alert("Select at least one document in the sidebar first.");
    return;
  }

  renderMessage("user", question);
  input.value = "";

  const useCompare = state.compareModeActive && state.selectedDocIds.length >= 2;
  if (useCompare) {
    await sendNonStreaming("/api/compare", question);
  } else {
    await sendStreaming("/api/chat/stream", question);
  }
});

function addThinkingBubble() {
  const thinking = document.createElement("div");
  thinking.className = "msg assistant";
  thinking.innerHTML = `<div class="msg-avatar">🤖</div><div class="msg-bubble">Thinking...</div>`;
  el("messages").appendChild(thinking);
  el("messages").scrollTop = el("messages").scrollHeight;
  return thinking;
}

async function sendNonStreaming(endpoint, question) {
  const thinking = addThinkingBubble();
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        doc_ids: state.selectedDocIds,
        session_id: state.currentSessionId,
      }),
    });
    const data = await res.json();
    thinking.remove();
    if (!res.ok) { renderMessage("assistant", `⚠️ ${data.error}`); return; }
    state.currentSessionId = data.session_id || state.currentSessionId;
    renderMessage("assistant", data.answer, data.sources || []);
  } catch (err) {
    thinking.remove();
    renderMessage("assistant", `⚠️ Something went wrong: ${err.message}`);
  }
}

async function sendStreaming(endpoint, question) {
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  wrap.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div>
      <div class="msg-bubble"><span class="stream-text">▍</span></div>
      <div class="msg-time"></div>
    </div>`;
  el("messages").appendChild(wrap);
  el("messages").scrollTop = el("messages").scrollHeight;

  const bubble = wrap.querySelector(".msg-bubble");
  const streamSpan = wrap.querySelector(".stream-text");
  const timeEl = wrap.querySelector(".msg-time");

  let fullText = "";
  let sources = [];

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        doc_ids: state.selectedDocIds,
        session_id: state.currentSessionId,
      }),
    });

    if (!res.ok) {
      const data = await res.json();
      bubble.textContent = `⚠️ ${data.error}`;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);

        if (event.type === "session") {
          state.currentSessionId = event.session_id;
        } else if (event.type === "progress") {
          streamSpan.textContent = event.message + " ▍";
          el("messages").scrollTop = el("messages").scrollHeight;
        } else if (event.type === "token") {
          fullText += event.content;
          streamSpan.textContent = fullText + " ▍";
          el("messages").scrollTop = el("messages").scrollHeight;
        } else if (event.type === "done") {
          sources = event.sources || [];
        }
      }
    }

    const sourcesHtml = sources.length
      ? `<div class="sources">${sources.map(s =>
          `<div class="source-chip">${s.doc} · page ${s.page} · ${s.type}</div>`).join("")}</div>`
      : "";
    bubble.innerHTML = renderMarkdown(fullText) + sourcesHtml;
    timeEl.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch (err) {
    bubble.textContent = `⚠️ Something went wrong: ${err.message}`;
  }
}

el("btn-summarize").addEventListener("click", async () => {
  if (state.selectedDocIds.length === 0) {
    alert("Select a document in the sidebar first.");
    return;
  }
  renderMessage("user", `Summarize "${docNameById(state.selectedDocIds[0])}"`);
  const thinking = document.createElement("div");
  thinking.id = "thinking-indicator";
  thinking.className = "msg assistant";
  thinking.innerHTML = `<div class="msg-avatar">🤖</div><div class="msg-bubble">Reading the full document...</div>`;
  el("messages").appendChild(thinking);

  try {
    const res = await fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: state.selectedDocIds[0] }),
    });
    const data = await res.json();
    document.getElementById("thinking-indicator")?.remove();
    renderMessage("assistant", data.summary || data.error);
  } catch (err) {
    document.getElementById("thinking-indicator")?.remove();
    renderMessage("assistant", `⚠️ ${err.message}`);
  }
});

function docNameById(id) {
  const doc = state.documents.find((d) => d.id === id);
  return doc ? doc.filename : "document";
}

// ---------- History ----------

async function loadHistory() {
  const res = await fetch("/api/sessions");
  const sessions = await res.json();
  const container = el("history-list");

  if (sessions.length === 0) {
    container.innerHTML = `<p class="doc-empty">No conversations yet.</p>`;
    return;
  }

  container.innerHTML = sessions.map((s) => `
    <div class="history-item" data-session-id="${s.id}">
      <div>
        <div class="history-item-title">${s.title}</div>
        <div class="history-item-meta">${s.mode} · ${new Date(s.updated_at).toLocaleString()}</div>
      </div>
      <button class="history-item-delete" data-delete-session="${s.id}">✕</button>
    </div>`).join("");

  container.querySelectorAll(".history-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      if (e.target.closest("[data-delete-session]")) return;
      openSession(item.dataset.sessionId);
    });
  });

  container.querySelectorAll("[data-delete-session]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      await fetch(`/api/sessions/${btn.dataset.deleteSession}`, { method: "DELETE" });
      loadHistory();
    });
  });
}

async function openSession(sessionId) {
  const res = await fetch(`/api/sessions/${sessionId}`);
  const session = await res.json();

  state.currentSessionId = session.id;
  state.selectedDocIds = session.doc_ids;
  renderDocList();

  el("messages").innerHTML = "";
  session.messages.forEach((m) => renderMessage(m.role, m.content, m.sources, m.created_at));

  switchView("chat");
}

// ---------- Init ----------

(async function init() {
  await fetchDocuments();
  if (state.documents.length > 0) {
    state.selectedDocIds = [state.documents[0].id];
    renderDocList();
    startNewChat();
    switchView("chat");
  } else {
    switchView("upload");
  }
})();
