const API_BASE = "";

document.addEventListener("DOMContentLoaded", () => {
  if (localStorage.getItem("userRole") !== "admin") {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("therapists").addEventListener("click", handleReviewAction);
  document.getElementById("supportInbox").addEventListener("click", handleSupportAction);
  loadTherapists();
  loadPayments();
  loadSupportInbox();
});

async function loadTherapists() {
  const container = document.getElementById("therapists");
  const pendingCount = document.getElementById("pendingCount");

  try {
    const res = await fetch(`${API_BASE}/get_unverified_therapists`);
    const data = await res.json();
    const therapists = data.therapists || [];

    pendingCount.textContent = `${therapists.length} pending`;

    if (therapists.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <strong>No pending therapist applications</strong>
          <p>Submitted applications will appear here for review.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = therapists.map(renderTherapistCard).join("");
  } catch (error) {
    console.error(error);
    container.innerHTML = `
      <div class="notice notice-error">
        <strong>Unable to load applications</strong>
        <p>Please check that the server is running.</p>
      </div>
    `;
  }
}

function renderTherapistCard(therapist) {
  const formats = therapist.session_formats && therapist.session_formats.length
    ? therapist.session_formats.join(", ")
    : "Not set";
  const languages = [therapist.primary_language, therapist.secondary_language].filter(Boolean).join(", ") || "Not set";

  return `
    <article class="admin-application">
      <div class="admin-application-header">
        <div>
          <p class="eyebrow">Pending review</p>
          <h3>${escapeHTML(therapist.name || "Unnamed therapist")}</h3>
          <p>${escapeHTML(therapist.email)}</p>
        </div>
        ${therapist.profile_photo ? `<img class="profile-photo" src="${therapist.profile_photo}" alt="">` : ""}
      </div>

      <div class="admin-detail-grid">
        <div><span>License</span><strong>${escapeHTML(therapist.license_number || "N/A")}</strong></div>
        <div><span>Board or state</span><strong>${escapeHTML(therapist.license_state || "N/A")}</strong></div>
        <div><span>Expiry</span><strong>${escapeHTML(therapist.license_expiry || "N/A")}</strong></div>
        <div><span>Specialization</span><strong>${escapeHTML(therapist.specialization || "N/A")}</strong></div>
        <div><span>Experience</span><strong>${escapeHTML(therapist.experience_years || "0")} years</strong></div>
        <div><span>Languages</span><strong>${escapeHTML(languages)}</strong></div>
        <div><span>Location</span><strong>${escapeHTML(therapist.location || "N/A")}</strong></div>
        <div><span>Rate</span><strong>${escapeHTML(formatRate(therapist.hourly_rate))}</strong></div>
        <div><span>Session formats</span><strong>${escapeHTML(formats)}</strong></div>
      </div>

      <div class="admin-copy">
        <h4>Bio</h4>
        <p>${escapeHTML(therapist.bio || "No bio provided.")}</p>
        <h4>Education</h4>
        <p>${escapeHTML(therapist.education || "No education provided.")}</p>
        <h4>Certifications</h4>
        <p>${escapeHTML(therapist.certifications || "No certifications provided.")}</p>
        <h4>Availability</h4>
        <p>${escapeHTML(formatAvailability(therapist.availability))}</p>
        ${therapist.credential_document ? `<a class="document-link" href="${therapist.credential_document}" target="_blank" rel="noopener">Open credential document</a>` : ""}
      </div>

      <div class="admin-actions">
        <button type="button" class="verify-btn" data-action="verify" data-email="${escapeAttribute(therapist.email)}">Verify</button>
        <button type="button" class="reject-btn" data-action="reject" data-email="${escapeAttribute(therapist.email)}">Request Changes</button>
      </div>
    </article>
  `;
}

function handleReviewAction(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;

  if (button.dataset.action === "verify") {
    verifyTherapist(button.dataset.email, 1);
  }

  if (button.dataset.action === "reject") {
    requestChanges(button.dataset.email);
  }
}

async function requestChanges(email) {
  const reason = prompt("What should this therapist update before approval?");
  if (reason === null) return;

  await verifyTherapist(email, 0, reason.trim() || "Application needs more information.");
}

async function verifyTherapist(email, verify, rejectionReason = "") {
  const res = await fetch(`${API_BASE}/verify_therapist`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      email,
      verify,
      rejection_reason: rejectionReason
    })
  });

  const data = await res.json();
  alert(data.message);
  loadTherapists();
}

async function loadPayments() {
  const container = document.getElementById("payments");
  const paymentCount = document.getElementById("paymentCount");

  try {
    const res = await fetch(`${API_BASE}/get_payments`);
    const data = await res.json();
    const payments = data.payments || [];
    const userPayments = payments.filter(payment => payment.payer_role !== "therapist");
    const therapistPayments = payments.filter(payment => payment.payer_role === "therapist");

    paymentCount.textContent = `${userPayments.length} user / ${therapistPayments.length} therapist`;

    container.innerHTML = `
      ${renderPaymentGroup("Users Transactions", "Payments made by client accounts.", userPayments)}
      ${renderPaymentGroup("Therapists Transactions", "Payments made by therapist accounts.", therapistPayments)}
    `;
  } catch (error) {
    console.error(error);
    container.innerHTML = `
      <div class="notice notice-error">
        <strong>Unable to load payments</strong>
        <p>Please check that the server is running.</p>
      </div>
    `;
  }
}

function renderPaymentGroup(title, description, payments) {
  const content = payments.length
    ? payments.map(renderPaymentCard).join("")
    : `
      <div class="empty-state">
        <strong>No ${escapeHTML(title.toLowerCase())}</strong>
        <p>Matching transactions will appear here.</p>
      </div>
    `;

  return `
    <section class="admin-subgroup">
      <div class="admin-subgroup-title">
        <div>
          <h3>${escapeHTML(title)}</h3>
          <p>${escapeHTML(description)}</p>
        </div>
        <span>${payments.length}</span>
      </div>
      <div class="admin-group-list">
        ${content}
      </div>
    </section>
  `;
}

function renderPaymentCard(payment) {
  return `
    <article class="admin-application compact-card">
      <div class="admin-application-header">
        <div>
          <p class="eyebrow">${escapeHTML(payment.status || "recorded")}</p>
          <h3>${escapeHTML(payment.user_email || "Unknown payer")}</h3>
          <p>${escapeHTML(payment.reference || "No reference")}</p>
        </div>
        <strong>${formatAmount(payment.amount, payment.currency)}</strong>
      </div>
      <div class="admin-detail-grid">
        <div><span>Account type</span><strong>${escapeHTML(payment.payer_role || "user")}</strong></div>
        <div><span>Provider</span><strong>${escapeHTML(payment.provider || "N/A")}</strong></div>
        <div><span>Status</span><strong>${escapeHTML(payment.status || "N/A")}</strong></div>
        <div><span>Created</span><strong>${escapeHTML(formatDate(payment.created_at))}</strong></div>
      </div>
    </article>
  `;
}

async function loadSupportInbox() {
  const container = document.getElementById("supportInbox");
  const supportCount = document.getElementById("supportCount");

  try {
    const res = await fetch(`${API_BASE}/get_customer_care`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    const messages = data.messages || [];
    const userMessages = messages.filter(item => item.sender_role !== "therapist");
    const therapistMessages = messages.filter(item => item.sender_role === "therapist");
    const userOpenCount = userMessages.filter(item => item.status === "open").length;
    const therapistOpenCount = therapistMessages.filter(item => item.status === "open").length;

    supportCount.textContent = `${userOpenCount} user / ${therapistOpenCount} therapist open`;

    container.innerHTML = `
      ${renderSupportGroup("Users Customer Care", "Messages from client accounts.", userMessages)}
      ${renderSupportGroup("Therapists Customer Care", "Messages from therapist accounts.", therapistMessages)}
    `;
  } catch (error) {
    console.error(error);
    container.innerHTML = `
      <div class="notice notice-error">
        <strong>Unable to load support messages</strong>
        <p>Please check that the server is running.</p>
      </div>
    `;
  }
}

function renderSupportGroup(title, description, messages) {
  const openCount = messages.filter(item => item.status === "open").length;
  const content = messages.length
    ? messages.map(renderSupportTicket).join("")
    : `
      <div class="empty-state">
        <strong>No ${escapeHTML(title.toLowerCase())} messages</strong>
        <p>Matching support requests will appear here.</p>
      </div>
    `;

  return `
    <section class="admin-subgroup">
      <div class="admin-subgroup-title">
        <div>
          <h3>${escapeHTML(title)}</h3>
          <p>${escapeHTML(description)}</p>
        </div>
        <span>${openCount} open</span>
      </div>
      <div class="admin-group-list">
        ${content}
      </div>
    </section>
  `;
}

function renderSupportTicket(item) {
  return `
    <article class="admin-application support-ticket">
      <div class="admin-application-header">
        <div>
          <p class="eyebrow">${escapeHTML(item.status)}</p>
          <h3>${escapeHTML(item.sender_email)}</h3>
          <p>${escapeHTML(item.sender_role)} - ${escapeHTML(formatDate(item.created_at))}</p>
        </div>
      </div>
      <div class="admin-copy">
        <h4>Message</h4>
        <p>${escapeHTML(item.message)}</p>
        ${item.admin_reply ? `<h4>Reply</h4><p>${escapeHTML(item.admin_reply)}</p>` : ""}
      </div>
      <div class="support-reply-form">
        <textarea data-reply-input="${item.id}" rows="3" placeholder="Reply to this message">${item.admin_reply ? escapeHTML(item.admin_reply) : ""}</textarea>
        <button type="button" data-support-reply="${item.id}">Send Reply</button>
      </div>
    </article>
  `;
}

async function handleSupportAction(event) {
  const button = event.target.closest("[data-support-reply]");
  if (!button) return;

  const id = button.dataset.supportReply;
  const input = document.querySelector(`[data-reply-input="${id}"]`);
  const reply = input.value.trim();

  if (!reply) {
    alert("Please enter a reply.");
    return;
  }

  const res = await fetch(`${API_BASE}/reply_customer_care`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, reply })
  });
  const data = await res.json();
  alert(data.message);
  loadSupportInbox();
}

function logoutAdmin() {
  localStorage.clear();
  window.location.href = "index.html";
}

function escapeHTML(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttribute(value) {
  return escapeHTML(value).replace(/`/g, "&#096;");
}

function formatAmount(amount, currency = "NGN") {
  const numericAmount = Number(amount || 0) / 100;
  return `${currency || "NGN"} ${numericAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatRate(rate) {
  if (!rate) return "N/A";
  const numericRate = Number(rate);
  if (Number.isNaN(numericRate)) {
    return `#${rate}`;
  }

  return `#${numericRate.toLocaleString()}`;
}

function parseAvailability(value) {
  if (!value) {
    return { duration: "", slots: [], legacy: "" };
  }

  try {
    const parsed = JSON.parse(value);
    if (parsed && Array.isArray(parsed.slots)) {
      return {
        duration: parsed.duration || "",
        slots: parsed.slots
          .filter(slot => slot && slot.day)
          .map(slot => ({
            day: slot.day,
            start: slot.start || "",
            end: slot.end || ""
          })),
        legacy: ""
      };
    }
  } catch (error) {
    // Older profiles stored availability as readable text, so keep supporting it.
  }

  const parts = String(value).split("|").map(part => part.trim());
  if (parts.length >= 2) {
    const days = parts[0].split(",").map(day => day.trim()).filter(Boolean);
    const [start, end] = (parts[1] || "").split("-").map(time => (time || "").trim());
    const durationMatch = (parts[2] || "").match(/(\d+)/);

    if (days.length && start && end) {
      return {
        duration: durationMatch ? durationMatch[1] : "",
        slots: days.map(day => ({ day, start, end })),
        legacy: ""
      };
    }
  }

  return { duration: "", slots: [], legacy: String(value) };
}

function formatAvailability(value) {
  const availability = parseAvailability(value);

  if (availability.legacy) return availability.legacy;
  if (!availability.slots.length) return "No availability provided.";

  const slots = availability.slots
    .map(slot => `${slot.day}: ${formatTime(slot.start)}-${formatTime(slot.end)}`)
    .join("; ");
  const duration = availability.duration ? ` (${availability.duration}-minute sessions)` : "";

  return `${slots}${duration}`;
}

function formatTime(value) {
  if (!value) return "";

  const [hourValue, minuteValue] = value.split(":");
  const hour = Number(hourValue);
  if (Number.isNaN(hour)) return value;

  const suffix = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;

  return `${displayHour}:${minuteValue || "00"} ${suffix}`;
}

function formatDate(value) {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}
