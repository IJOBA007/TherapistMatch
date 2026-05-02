const CHAT_API_BASE = "";

let activeThread = null;
let threads = [];
let sessionTimerInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  const email = localStorage.getItem("email");
  const role = localStorage.getItem("userRole");

  if (!email || !["user", "therapist"].includes(role)) {
    window.location.href = "index.html";
    return;
  }

  renderSidebar(role);
  document.getElementById("chatForm").addEventListener("submit", sendMsg);
  loadThreads();
});

function renderSidebar(role) {
  const sidebar = document.getElementById("chatSidebar");

  if (role === "therapist") {
    sidebar.innerHTML = `
      <h2>TherapistMatch</h2>
      <a href="therapist.html">Portal <span class="nav-badge" data-badge="profile"></span></a>
      <a href="chat.html" class="active">Chat <span class="nav-badge" data-badge="chat"></span></a>
      <a href="#" class="logout-link" id="logoutLink">Logout</a>
    `;
  } else {
    sidebar.innerHTML = `
      <h2>TherapistMatch</h2>
      <a href="dashboard.html">Dashboard <span class="nav-badge" data-badge="dashboard"></span></a>
      <a href="match.html">Find Therapist <span class="nav-badge" data-badge="find"></span></a>
      <a href="chat.html" class="active">Chat <span class="nav-badge" data-badge="chat"></span></a>
      <a href="settings.html">Settings <span class="nav-badge" data-badge="settings"></span></a>
      <a href="#" class="logout-link" id="logoutLink">Logout</a>
    `;
  }

  document.getElementById("logoutLink").addEventListener("click", event => {
    event.preventDefault();
    localStorage.clear();
    window.location.href = "index.html";
  });
}

async function loadThreads() {
  const threadList = document.getElementById("threadList");
  threadList.innerHTML = `<div class="empty-state"><strong>Loading sessions</strong><p>Please wait.</p></div>`;

  try {
    const res = await fetch(`${CHAT_API_BASE}/chat_threads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: localStorage.getItem("email"),
        role: localStorage.getItem("userRole")
      })
    });
    const data = await res.json();
    threads = data.threads || [];

    if (!threads.length) {
      threadList.innerHTML = `
        <div class="empty-state">
          <strong>No chat sessions yet</strong>
          <p>Chats appear after a therapist accepts a booking.</p>
        </div>
      `;
      return;
    }

    threadList.innerHTML = threads.map(renderThreadButton).join("");
    threadList.querySelectorAll("[data-thread-index]").forEach(button => {
      button.addEventListener("click", () => selectThread(Number(button.dataset.threadIndex)));
    });

    selectThread(0);
  } catch (error) {
    console.error("Chat threads failed:", error);
    threadList.innerHTML = `
      <div class="empty-state">
        <strong>Unable to load chats</strong>
        <p>Please refresh the page.</p>
      </div>
    `;
  }
}

function renderThreadButton(thread, index) {
  const status = thread.can_chat ? "Paid" : "Payment needed";

  return `
    <button type="button" class="thread-button" data-thread-index="${index}">
      <span>
        <strong>${escapeHTML(thread.display_name || thread.receiver_email)}</strong>
        <small>${escapeHTML(thread.subtitle || formatDateTime(thread.date))}</small>
      </span>
      <em class="${thread.can_chat ? "thread-ready" : "thread-locked"}">${escapeHTML(status)}</em>
    </button>
  `;
}

async function selectThread(index) {
  activeThread = threads[index];
  if (!activeThread) return;

  document.querySelectorAll(".thread-button").forEach((button, buttonIndex) => {
    button.classList.toggle("active", buttonIndex === index);
  });

  document.getElementById("chatEmpty").hidden = true;
  document.getElementById("chatRoom").hidden = false;
  document.getElementById("chatTitle").textContent = activeThread.display_name || activeThread.receiver_email;
  document.getElementById("chatSubtitle").textContent = formatDateTime(activeThread.date);

  const status = document.getElementById("chatStatus");
  const input = document.getElementById("msg");
  const sendButton = document.querySelector("#chatForm button");
  const chatMessage = document.getElementById("chatMessage");
  const meetLink = document.getElementById("meetLink");
  const shortage = Number(activeThread.shortage || 0);

  status.textContent = activeThread.can_chat ? "Paid session" : "Session payment required";
  renderSessionTimer(activeThread.timer);
  input.disabled = !activeThread.can_chat;
  sendButton.disabled = !activeThread.can_chat;
  chatMessage.textContent = activeThread.can_chat
    ? ""
    : shortage > 0
      ? `Account needs ${formatNaira(shortage)} more before chat or Google Meet can start.`
      : "Pay for this session before chat or Google Meet can start.";

  meetLink.href = activeThread.meet_link || "https://meet.google.com/new";
  meetLink.classList.toggle("disabled", !activeThread.can_chat);
  meetLink.setAttribute("aria-disabled", activeThread.can_chat ? "false" : "true");

  await loadMessages();
}

async function sendMsg(event) {
  event.preventDefault();

  if (!activeThread || !activeThread.can_chat) return;

  const input = document.getElementById("msg");
  const message = input.value.trim();
  if (!message) return;

  const res = await fetch(`${CHAT_API_BASE}/send_message`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      sender: localStorage.getItem("email"),
      receiver: activeThread.receiver_email,
      booking_id: activeThread.booking_id,
      message
    })
  });
  const data = await res.json();

  if (!res.ok) {
    document.getElementById("chatMessage").textContent = data.message || "Message could not be sent.";
    return;
  }

  if (data.timer) {
    activeThread.timer = data.timer;
    renderSessionTimer(activeThread.timer);
  }
  input.value = "";
  await loadMessages();
}

async function loadMessages() {
  const chatBox = document.getElementById("chatBox");

  if (!activeThread) {
    chatBox.innerHTML = "";
    return;
  }

  if (!activeThread.can_chat) {
    chatBox.innerHTML = `
      <div class="empty-state">
        <strong>Chat locked</strong>
        <p>Payment is required before this conversation opens.</p>
      </div>
    `;
    return;
  }

  const res = await fetch(`${CHAT_API_BASE}/get_messages`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      user1: localStorage.getItem("email"),
      user2: activeThread.receiver_email,
      booking_id: activeThread.booking_id
    })
  });
  const data = await res.json();

  if (!res.ok) {
    chatBox.innerHTML = `
      <div class="empty-state">
        <strong>Chat unavailable</strong>
        <p>${escapeHTML(data.message || "Please try again.")}</p>
      </div>
    `;
    return;
  }

  if (data.timer) {
    activeThread.timer = data.timer;
    renderSessionTimer(activeThread.timer);
  }
  const messages = data.messages || [];
  chatBox.innerHTML = messages.length
    ? messages.map(renderMessage).join("")
    : `<div class="empty-state"><strong>No messages yet</strong><p>Start the conversation when you are ready.</p></div>`;
  chatBox.scrollTop = chatBox.scrollHeight;
}

function renderSessionTimer(timer) {
  const timerElement = document.getElementById("sessionTimer");
  if (!timerElement) return;

  if (sessionTimerInterval) {
    clearInterval(sessionTimerInterval);
    sessionTimerInterval = null;
  }

  if (!activeThread?.can_chat) {
    timerElement.textContent = "Payment pending";
    timerElement.className = "session-timer locked";
    return;
  }

  if (!timer || !timer.paid) {
    timerElement.textContent = "Payment pending";
    timerElement.className = "session-timer locked";
    return;
  }

  if (!timer.started || !timer.ends_at) {
    timerElement.textContent = "Timer starts after both sides message.";
    timerElement.className = "session-timer waiting";
    return;
  }

  const updateTimer = () => {
    const remaining = new Date(timer.ends_at).getTime() - Date.now();

    if (remaining <= 0) {
      timerElement.textContent = "Session time ended";
      timerElement.className = "session-timer ended";
      clearInterval(sessionTimerInterval);
      sessionTimerInterval = null;
      return;
    }

    timerElement.textContent = `Session time ${formatDuration(remaining)}`;
    timerElement.className = "session-timer running";
  };

  updateTimer();
  sessionTimerInterval = setInterval(updateTimer, 1000);
}

function formatDuration(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function renderMessage(message) {
  const isMine = message.sender === localStorage.getItem("email");

  return `
    <div class="chat-bubble ${isMine ? "mine" : "theirs"}">
      <span>${escapeHTML(isMine ? "You" : message.sender)}</span>
      <p>${escapeHTML(message.message)}</p>
    </div>
  `;
}

function formatDateTime(value) {
  if (!value) return "Date not set";
  return new Date(value).toLocaleString();
}

function formatNaira(amountKobo) {
  const amount = Number(amountKobo || 0) / 100;
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0
  }).format(amount);
}

function escapeHTML(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
