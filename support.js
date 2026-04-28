const SUPPORT_API_BASE = "";

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("supportToggle");
  const close = document.getElementById("supportClose");
  const send = document.getElementById("supportSend");

  if (!toggle || !close || !send) return;

  toggle.addEventListener("click", () => {
    document.getElementById("supportPanel").hidden = false;
    loadSupportMessages();
  });
  close.addEventListener("click", () => {
    document.getElementById("supportPanel").hidden = true;
  });
  send.addEventListener("click", sendSupportMessage);

  loadSupportMessages();
});

async function loadSupportMessages() {
  const email = localStorage.getItem("email");
  const container = document.getElementById("supportMessages");
  const indicator = document.getElementById("supportIndicator");

  if (!email || !container) return;

  try {
    const res = await fetch(`${SUPPORT_API_BASE}/get_customer_care`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    const messages = data.messages || [];
    const hasOpen = messages.some(item => item.status === "open");
    const hasReply = messages.some(item => item.admin_reply);

    if (indicator) {
      indicator.classList.toggle("active", hasOpen || hasReply);
      indicator.title = hasOpen ? "Support request open" : hasReply ? "Admin has replied" : "Customer care";
    }

    if (messages.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <strong>No support messages yet</strong>
          <p>Your conversation with admin will appear here.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = messages.map(item => `
      <article class="support-message">
        <span>${escapeSupportHTML(item.status)}</span>
        <p>${escapeSupportHTML(item.message)}</p>
        ${item.admin_reply ? `<div class="support-reply"><strong>Admin reply</strong><p>${escapeSupportHTML(item.admin_reply)}</p></div>` : ""}
      </article>
    `).join("");
  } catch (error) {
    console.error("Support messages failed:", error);
  }
}

async function sendSupportMessage() {
  const input = document.getElementById("supportMessage");
  const message = input.value.trim();

  if (!message) return;

  const res = await fetch(`${SUPPORT_API_BASE}/customer_care`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: localStorage.getItem("email"),
      role: localStorage.getItem("userRole") || "user",
      message
    })
  });
  const data = await res.json();

  if (!res.ok) {
    alert(data.message || "Unable to send support message.");
    return;
  }

  input.value = "";
  await loadSupportMessages();
}

function escapeSupportHTML(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
