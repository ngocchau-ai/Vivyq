/**
 * app.js — Cautreo Desktop Studio Client Application
 * Handles SSE Chat Streaming, Thought Stream Accordion, Vitals Polling, and Sockets.
 * 
 * Author: Antigravity IDE (Sprint D1/D2/D3)
 */

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

// Global state
let currentModel = "gemma4-e4b";
let vitalsTimer = null;
let isGenerating = false;

function initApp() {
  setupTabs();
  setupInputHandlers();
  setupModelSelector();
  setupDreamButton();
  setupGoalToggle();

  // Load initial data
  fetchVitals();
  fetchSockets();

  // Polling vitals every 2.5s
  vitalsTimer = setInterval(fetchVitals, 2500);
}

/* -------------------------------------------------------------------------
 * 1. Tabs Switching (Left Pane)
 * ------------------------------------------------------------------------- */
function setupTabs() {
  const tabs = document.querySelectorAll(".socket-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".socket-tab-content").forEach((c) => c.classList.remove("active"));

      tab.classList.add("active");
      const targetId = `tab-${tab.dataset.tab}`;
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });
}

/* -------------------------------------------------------------------------
 * 2. Model Selector & Actions
 * ------------------------------------------------------------------------- */
function setupModelSelector() {
  const select = document.getElementById("model-select");
  if (select) {
    select.addEventListener("change", (e) => {
      currentModel = e.target.value;
      console.log(`Switched reasoning model to: ${currentModel}`);
    });
  }
}

function setupDreamButton() {
  const btn = document.getElementById("btn-trigger-dream");
  if (btn) {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.innerHTML = `<span class="dream-star">✨</span> Consolidating...`;
      try {
        const resp = await fetch("/api/dream", { method: "POST" });
        const data = await resp.json();
        if (data.success) {
          document.getElementById("dream-latency-val").textContent = `${data.latency_ms}ms`;
          document.getElementById("dream-nodes-val").textContent = `${data.consolidated_nodes} nodes`;
          showNotification(`🌙 Dream cycle completed in ${data.latency_ms}ms`);
        }
      } catch (err) {
        console.error("Dream cycle failed:", err);
      } finally {
        setTimeout(() => {
          btn.disabled = false;
          btn.innerHTML = `<span class="dream-star">🌙</span> Dream Cycle`;
        }, 1000);
      }
    });
  }
}

function setupGoalToggle() {
  const toggle = document.getElementById("toggle-goal-mode");
  if (toggle) {
    toggle.addEventListener("change", async (e) => {
      try {
        const resp = await fetch("/api/sockets/harness/toggle_goal", { method: "POST" });
        const data = await resp.json();
        showNotification(data.goal_mode ? "🎯 /goal mode ACTIVATED (Autonomous)" : "⏸️ /goal mode PAUSED");
      } catch (err) {
        console.error("Failed to toggle goal mode:", err);
      }
    });
  }
}

/* -------------------------------------------------------------------------
 * 3. Vitals & Sockets Data Fetching
 * ------------------------------------------------------------------------- */
async function fetchVitals() {
  try {
    const resp = await fetch("/api/vitals");
    if (!resp.ok) return;
    const vitals = await resp.json();

    // Update Score Graph Gauges
    if (vitals.scores) {
      document.getElementById("score-task-val").textContent = `${vitals.scores.task_progress}%`;
      document.getElementById("score-task-bar").style.width = `${vitals.scores.task_progress}%`;

      document.getElementById("score-ctx-val").textContent = `${vitals.scores.context_efficiency}%`;
      document.getElementById("score-ctx-bar").style.width = `${vitals.scores.context_efficiency}%`;

      document.getElementById("score-mem-val").textContent = `${vitals.scores.memory_quality}%`;
      document.getElementById("score-mem-bar").style.width = `${vitals.scores.memory_quality}%`;
    }

    // Update RAM Context Memory
    if (vitals.context_memory) {
      const { used_slots, total_slots, percent } = vitals.context_memory;
      document.getElementById("mem-used-badge").textContent = `${used_slots} / ${total_slots} (${percent}%)`;
      document.getElementById("ram-meter-fill").style.width = `${percent}%`;
    }

    // Update Dream State
    if (vitals.dream_state) {
      document.getElementById("vivy-dream-status-text").textContent = vitals.dream_state;
      document.getElementById("dream-badge").textContent = vitals.dream_state;
      document.getElementById("dream-latency-val").textContent = `${vitals.last_dream_ms}ms`;
      document.getElementById("dream-nodes-val").textContent = `${vitals.consolidated_nodes} nodes`;
    }
  } catch (err) {
    console.debug("Error fetching vitals:", err);
  }
}

async function fetchSockets() {
  try {
    const resp = await fetch("/api/sockets");
    if (!resp.ok) return;
    const data = await resp.json();

    // Render Harness Workers
    if (data.harness && data.harness.workers) {
      const list = document.getElementById("workers-list");
      list.innerHTML = data.harness.workers
        .map(
          (w) => `
        <div class="worker-item">
          <div class="item-row">
            <span class="item-name">${w.name}</span>
            <span class="item-badge ${w.status === "ACTIVE" ? "active" : ""}">${w.status}</span>
          </div>
          <div class="item-sub">${w.role} • ${w.latency_ms}ms</div>
        </div>
      `
        )
        .join("");
    }

    // Render 7 Gates
    if (data.harness && data.harness.completion_gates) {
      const list = document.getElementById("gates-list");
      list.innerHTML = data.harness.completion_gates
        .map(
          (g) => `
        <div class="gate-item">
          <div class="item-row">
            <span class="item-name">${g.name}</span>
            <span class="item-badge passed">${g.status}</span>
          </div>
          <div class="item-sub">${g.detail}</div>
        </div>
      `
        )
        .join("");
    }

    // Render Tools
    if (data.tools && data.tools.plugins) {
      const list = document.getElementById("plugins-list");
      list.innerHTML = data.tools.plugins
        .map(
          (p) => `
        <div class="plugin-item">
          <div class="item-row">
            <span class="item-name">${p.name}</span>
            <span class="item-badge ${p.enabled ? "active" : ""}">${p.sandbox_level}</span>
          </div>
          <div class="item-sub">${p.description}</div>
        </div>
      `
        )
        .join("");
    }

    // Render Skills
    if (data.skills && data.skills.skills) {
      const list = document.getElementById("skills-list");
      list.innerHTML = data.skills.skills
        .map(
          (s) => `
        <div class="skill-item" onclick="insertSkill('${s.id}', '${s.name}')" style="cursor: pointer;">
          <div class="item-row">
            <span class="item-name">${s.name}</span>
            <span class="item-badge passed">${s.badge}</span>
          </div>
          <div class="item-sub">${s.description}</div>
        </div>
      `
        )
        .join("");
    }
  } catch (err) {
    console.debug("Error fetching sockets:", err);
  }
}

/* -------------------------------------------------------------------------
 * 4. Chat & SSE Streaming Interaction
 * ------------------------------------------------------------------------- */
function setupInputHandlers() {
  const textarea = document.getElementById("user-input");
  const sendBtn = document.getElementById("btn-send");

  // Auto-resize textarea
  textarea.addEventListener("input", () => {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + "px";
  });

  // Enter to send, Shift+Enter for new line
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener("click", () => {
    sendMessage();
  });
}

async function sendMessage() {
  if (isGenerating) return;
  const textarea = document.getElementById("user-input");
  const text = textarea.value.trim();
  if (!text) return;

  textarea.value = "";
  textarea.style.height = "auto";
  isGenerating = true;

  // Append user message to chat
  appendUserMessage(text);

  // Prepare assistant message container
  const { msgElement, thoughtPre, bodyDiv, timeBadge } = createAssistantMessagePlaceholder();

  const chatContainer = document.getElementById("chat-stream");
  chatContainer.scrollTop = chatContainer.scrollHeight;

  const velIndicator = document.getElementById("velocity-indicator");
  velIndicator.textContent = "⚡ ViVy đang suy luận...";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, model: currentModel, stream: true }),
    });

    if (!response.body) {
      throw new Error("ReadableStream not supported");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const block of lines) {
        if (!block.trim()) continue;
        const eventMatch = block.match(/event:\s*(\w+)/);
        const dataMatch = block.match(/data:\s*(.+)/s);

        const event = eventMatch ? eventMatch[1] : "message";
        const rawData = dataMatch ? dataMatch[1] : "";

        if (event === "thought") {
          try {
            const parsed = JSON.parse(rawData);
            thoughtPre.textContent = parsed.content || "";
            timeBadge.textContent = `Tư duy: ${parsed.ms}ms`;
          } catch (e) {
            thoughtPre.textContent = rawData;
          }
        } else if (event === "token") {
          try {
            const parsed = JSON.parse(rawData);
            bodyDiv.innerHTML += formatMarkdown(parsed.token || "");
          } catch (e) {
            bodyDiv.innerHTML += formatMarkdown(rawData);
          }
          chatContainer.scrollTop = chatContainer.scrollHeight;
        } else if (event === "done") {
          try {
            const parsed = JSON.parse(rawData);
            velIndicator.textContent = `⚡ ${parsed.velocity} tok/s (${parsed.elapsed_s}s)`;
          } catch (e) {}
        }
      }
    }
  } catch (err) {
    console.error("Chat streaming failed:", err);
    bodyDiv.innerHTML += `<div style="color: var(--accent-rose);">[Lỗi kết nối tới ViVy Core]</div>`;
  } finally {
    isGenerating = false;
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
}

function appendUserMessage(text) {
  const chatContainer = document.getElementById("chat-stream");
  const msg = document.createElement("div");
  msg.className = "chat-message user-message";
  msg.innerHTML = `
    <div class="message-meta">
      <span class="sender-tag">User</span>
      <span class="time-tag">Bây giờ</span>
    </div>
    <div class="message-body">${escapeHtml(text)}</div>
  `;
  chatContainer.appendChild(msg);
}

function createAssistantMessagePlaceholder() {
  const chatContainer = document.getElementById("chat-stream");
  const msg = document.createElement("div");
  msg.className = "chat-message assistant-message";

  const accordionId = `thought-${Date.now()}`;
  msg.innerHTML = `
    <div class="message-meta">
      <span class="sender-tag">ViVy Core</span>
      <span class="time-tag">Bây giờ</span>
    </div>
    <div class="thought-accordion">
      <button class="thought-toggle" onclick="toggleThought(this)">
        <span>▾ <strong style="color: var(--accent-cyan);">Dòng Tư Duy Nhận Thức (&lt;vivy_thought&gt;)</strong></span>
        <span class="thought-time">Đang tư duy...</span>
      </button>
      <div class="thought-body" style="display: none;">
        <pre><code></code></pre>
      </div>
    </div>
    <div class="message-body markdown-content"></div>
  `;
  chatContainer.appendChild(msg);

  const thoughtPre = msg.querySelector(".thought-body pre code");
  const bodyDiv = msg.querySelector(".message-body");
  const timeBadge = msg.querySelector(".thought-time");

  return { msgElement: msg, thoughtPre, bodyDiv, timeBadge };
}

/* -------------------------------------------------------------------------
 * 5. Helpers & Interactivity
 * ------------------------------------------------------------------------- */
window.toggleThought = function (btn) {
  const body = btn.parentElement.querySelector(".thought-body");
  if (body) {
    const isHidden = body.style.display === "none";
    body.style.display = isHidden ? "block" : "none";
    btn.querySelector("span:first-child").innerHTML = isHidden
      ? `▾ <strong style="color: var(--accent-cyan);">Dòng Tư Duy Nhận Thức (&lt;vivy_thought&gt;)</strong>`
      : `▸ <strong style="color: var(--accent-cyan);">Dòng Tư Duy Nhận Thức (&lt;vivy_thought&gt;)</strong>`;
  }
};

window.insertCommand = function (cmd) {
  const textarea = document.getElementById("user-input");
  textarea.value = cmd;
  textarea.focus();
};

window.insertSkill = function (skillId, skillName) {
  const textarea = document.getElementById("user-input");
  textarea.value = `[Skill: ${skillName}] ` + textarea.value;
  textarea.focus();
};

function showNotification(msg) {
  const toast = document.createElement("div");
  toast.textContent = msg;
  toast.style.position = "fixed";
  toast.style.bottom = "80px";
  toast.style.right = "24px";
  toast.style.background = "rgba(18, 26, 41, 0.95)";
  toast.style.color = "#38BDF8";
  toast.style.border = "1px solid rgba(56, 189, 248, 0.3)";
  toast.style.padding = "10px 16px";
  toast.style.borderRadius = "8px";
  toast.style.boxShadow = "0 8px 30px rgba(0,0,0,0.5)";
  toast.style.fontSize = "12px";
  toast.style.zIndex = "9999";
  toast.style.animation = "fadeIn 0.2s ease";

  document.body.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 2800);
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatMarkdown(text) {
  // Lightweight markdown formatting
  let html = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code style='background: rgba(255,255,255,0.08); padding: 1px 5px; border-radius: 4px; font-family: var(--font-code); font-size: 11.5px;'>$1</code>")
    .replace(/\n/g, "<br>");
  return html;
}
