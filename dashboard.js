function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}

const ADMIN_CONSOLE_PATH = "/tm-console-7f3a9c";

function setWelcome(message) {
  const welcome = document.getElementById("welcome");
  if (welcome) {
    welcome.innerText = message;
  }
}

async function initDashboard() {
  const email = localStorage.getItem("email");
  const role = localStorage.getItem("userRole");

  if (!email || !role) {
    window.location.href = "index.html";
    return;
  }

  if (role === "therapist") {
    window.location.href = "therapist.html";
    return;
  }

  if (role === "admin") {
    window.location.href = ADMIN_CONSOLE_PATH;
    return;
  }

  try {
    const res = await fetch("/get_profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });

    const data = await res.json();

    if (data.profile && data.profile.name) {
      const firstName = data.profile.name.split(" ")[0];
      setWelcome("Welcome, " + firstName);
    } else {
      setWelcome("Welcome User");
    }

    if (
      !data.profile ||
      !data.profile.name ||
      !data.profile.dob ||
      !data.profile.gender ||
      !data.profile.location ||
      !data.profile.primary_language
    ) {
      alert("Please go to Settings and complete your profile information.");
    }

    await loadBookings(email);
    await loadNotifications();
  } catch (error) {
    console.error("Dashboard profile load failed:", error);
    setWelcome("Welcome User");
    await loadBookings(email);
    await loadNotifications();
  }
}

async function loadNotifications() {
  const email = localStorage.getItem("email");
  const role = localStorage.getItem("userRole");
  
  try {
    const res = await fetch("/get_notifications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, role })
    });
    
    const data = await res.json();
    
    // Update booking notification badge
    const bookingBadge = document.querySelector("[data-badge='dashboard']");
    if (bookingBadge && data.bookings > 0) {
      bookingBadge.textContent = data.bookings;
      bookingBadge.style.display = "inline-block";
    } else if (bookingBadge) {
      bookingBadge.style.display = "none";
    }
  } catch (error) {
    console.error("Notification load failed:", error);
  }
}

// Bind duplicate removal button
document.addEventListener("DOMContentLoaded", () => {
  const removeDupBtn = document.getElementById("removeDuplicates");
  if (removeDupBtn) {
    removeDupBtn.addEventListener("click", removeDuplicateBookings);
  }
});

async function removeDuplicateBookings() {
  if (!confirm("Cancel overlapping duplicate bookings and hide them from this list?")) {
    return;
  }
  
  const email = localStorage.getItem("email");
  
  const res = await fetch("/remove_duplicate_bookings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, role: localStorage.getItem("userRole") })
  });
  
  const data = await res.json();
  alert(data.message);
  
  if (res.ok) {
    await loadBookings(email);
    await loadNotifications();
  }
}

async function loadBookings(email) {
  const bookings = document.getElementById("bookings");
  if (!bookings) return;

  try {
    const res = await fetch("/user_bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    const rows = data.bookings || [];

    if (!rows.length) {
      bookings.innerHTML = `
        <div class="empty-state">
          <strong>No bookings yet</strong>
          <p>Your session requests will appear here.</p>
        </div>
      `;
      return;
    }

    bookings.innerHTML = rows.map(renderBooking).join("");
    bookings.querySelectorAll("[data-rating-submit]").forEach(button => {
      button.addEventListener("click", () => submitRating(button));
    });
    bookings.querySelectorAll(".cancel-my-booking").forEach(btn => {
      btn.addEventListener("click", () => cancelMyBooking(btn.dataset.bookingId));
    });
    bookings.querySelectorAll(".delete-my-booking").forEach(btn => {
      btn.addEventListener("click", () => deleteMyBooking(btn.dataset.bookingId));
    });
    bookings.querySelectorAll(".pay-session").forEach(btn => {
      btn.addEventListener("click", () => payForSession(btn.dataset.bookingId));
    });
    bookings.querySelectorAll(".pay-sessions").forEach(btn => {
      btn.addEventListener("click", () => payForSessions((btn.dataset.bookingIds || "").split(",").filter(Boolean)));
    });
  } catch (error) {
    console.error("Bookings load failed:", error);
    bookings.innerHTML = `
      <div class="empty-state">
        <strong>Unable to load bookings</strong>
        <p>Please refresh the page.</p>
      </div>
    `;
  }
}

function renderBooking(booking) {
  const therapist = booking.therapist || {};
  const review = booking.review || {};
  const rating = review.rating || "";
  const status = booking.status || "Pending";
  const isPending = status.toLowerCase() === "pending";
  const isRejected = status.toLowerCase() === "rejected";
  const isAccepted = status.toLowerCase() === "accepted";
  const canCancel = isPending;
  const canDelete = isRejected || status.toLowerCase() === "cancelled";
  const canChat = isAccepted && booking.can_chat;
  const needsPayment = isAccepted && !booking.paid;
  const meetLink = booking.meet_link || "https://meet.google.com/new";
  const accountBalance = Number(booking.account_balance || 0);
  const sessionPrice = Number(booking.session_price || 0);
  const groupActiveCount = Number(booking.group_active_count || booking.total_sessions || 1);
  const sequenceNumber = Number(booking.sequence_number || 1);
  const groupUnpaidIds = Array.isArray(booking.group_unpaid_booking_ids) ? booking.group_unpaid_booking_ids : [];
  const groupUnpaidCount = Number(booking.group_unpaid_count || 0);
  const groupUnpaidTotal = Number(booking.group_unpaid_total || sessionPrice);
  const paymentIds = groupUnpaidCount > 1 ? groupUnpaidIds : [booking.id];
  const paymentTotal = groupUnpaidCount > 1 ? groupUnpaidTotal : sessionPrice;
  const shortage = Math.max(paymentTotal - accountBalance, 0);
  const canPaySession = needsPayment && paymentTotal > 0 && accountBalance >= paymentTotal;
  const paymentNotice = canPaySession
    ? `Your account balance is ${formatNaira(accountBalance)}. Pay ${formatNaira(paymentTotal)} to unlock chat and Google Meet.`
    : `Add ${formatNaira(shortage)} more to pay for ${groupUnpaidCount > 1 ? "these sessions" : "this session"}.`;
  const paymentButtonLabel = groupUnpaidCount > 1
    ? `Pay ${groupUnpaidCount} Sessions`
    : "Pay for Session";

  return `
    <article class="booking-row detailed-booking user-booking">
      <div class="booking-main">
        <div>
          <strong>${escapeHTML(therapist.name || booking.therapist_email)}</strong>
          <span>${escapeHTML(therapist.specialization || "General practice")}</span>
          <span>${escapeHTML(formatDateTime(booking.date))}</span>
          ${groupActiveCount > 1 ? `<span>${escapeHTML(`Session ${sequenceNumber} of ${groupActiveCount}`)}</span>` : ""}
        </div>
        <span class="booking-status">${escapeHTML(status)}</span>
      </div>
      <div class="booking-profile">
        <h4>Quality rating</h4>
        <div class="rating-form">
          <select data-rating-value="${escapeAttribute(booking.therapist_email)}">
            <option value="">Rate therapist</option>
            <option value="5" ${rating === 5 ? "selected" : ""}>5 - Excellent</option>
            <option value="4" ${rating === 4 ? "selected" : ""}>4 - Good</option>
            <option value="3" ${rating === 3 ? "selected" : ""}>3 - Okay</option>
            <option value="2" ${rating === 2 ? "selected" : ""}>2 - Poor</option>
            <option value="1" ${rating === 1 ? "selected" : ""}>1 - Very poor</option>
          </select>
          <input data-rating-comment="${escapeAttribute(booking.therapist_email)}" value="${escapeAttribute(review.comment || "")}" placeholder="Optional note">
          <button type="button" data-rating-submit="${escapeAttribute(booking.therapist_email)}">Save Rating</button>
        </div>
        <p class="rating-message" data-rating-message="${escapeAttribute(booking.therapist_email)}"></p>
      </div>
      ${needsPayment ? `
      <div class="notice notice-pending booking-payment-notice">
        <strong>Session payment required</strong>
        <p>${escapeHTML(paymentNotice)}</p>
      </div>
      ` : ''}
      ${canCancel || canDelete || canChat || needsPayment ? `
      <div class="booking-actions">
        ${canChat ? `
        <a class="button-link" href="chat.html">Open Chat</a>
        <a class="button-link ghost-link" href="${escapeAttribute(meetLink)}" target="_blank" rel="noopener">Google Meet</a>
        ` : ''}
        ${needsPayment && canPaySession ? `<button type="button" class="${groupUnpaidCount > 1 ? "pay-sessions" : "pay-session"}" data-booking-id="${escapeAttribute(booking.id)}" data-booking-ids="${escapeAttribute(paymentIds.join(","))}">${escapeHTML(paymentButtonLabel)}</button>` : ''}
        ${needsPayment && !canPaySession ? `<a class="button-link ghost-link" href="settings.html">Top Up Account</a>` : ''}
        ${canDelete ? `<button type="button" class="delete-my-booking" data-booking-id="${booking.id}">Delete</button>` : ''}
        ${canCancel ? `
        <button type="button" class="cancel-my-booking" data-booking-id="${booking.id}">Cancel Booking</button>
        ` : ''}
      </div>
      ` : ''}
    </article>
  `;
}

async function payForSession(bookingId) {
  if (!bookingId) return;

  await payForSessions([bookingId]);
}

async function payForSessions(bookingIds) {
  const cleanIds = (bookingIds || []).filter(Boolean);
  if (!cleanIds.length) return;

  const sessionLabel = cleanIds.length === 1 ? "this session" : `${cleanIds.length} sessions`;
  if (!confirm(`Pay for ${sessionLabel} from your account balance?`)) {
    return;
  }

  const res = await fetch(cleanIds.length === 1 ? "/pay_for_session" : "/pay_for_sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      booking_id: cleanIds[0],
      booking_ids: cleanIds,
      user_email: localStorage.getItem("email")
    })
  });
  const data = await res.json();

  alert(data.message || `${sessionLabel} payment updated.`);

  if (res.ok) {
    await loadBookings(localStorage.getItem("email"));
    await loadNotifications();
  }
}

async function submitRating(button) {
  const therapistEmail = button.dataset.ratingSubmit;
  const ratingInput = document.querySelector(`[data-rating-value="${therapistEmail}"]`);
  const commentInput = document.querySelector(`[data-rating-comment="${therapistEmail}"]`);
  const message = document.querySelector(`[data-rating-message="${therapistEmail}"]`);

  if (!ratingInput.value) {
    message.textContent = "Choose a rating first.";
    return;
  }

  button.disabled = true;
  message.textContent = "Saving rating...";

  const res = await fetch("/rate_therapist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_email: localStorage.getItem("email"),
      therapist_email: therapistEmail,
      rating: ratingInput.value,
      comment: commentInput.value
    })
  });
  const data = await res.json();

  message.textContent = data.message || "Rating saved.";
  message.classList.toggle("success", res.ok);
  message.classList.toggle("error", !res.ok);
  button.disabled = false;
}

async function cancelMyBooking(bookingId) {
  if (!confirm("Are you sure you want to cancel this booking?")) {
    return;
  }
  
  const res = await fetch("/cancel_booking", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      booking_id: bookingId,
      user_email: localStorage.getItem("email")
    })
  });
  
  const data = await res.json();
  alert(data.message);
  
  if (res.ok) {
    await loadBookings(localStorage.getItem("email"));
    await loadNotifications();
  }
}

async function deleteMyBooking(bookingId) {
  if (!confirm("Delete this rejected booking from your dashboard?")) {
    return;
  }

  const res = await fetch("/delete_user_booking", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      booking_id: bookingId,
      user_email: localStorage.getItem("email")
    })
  });

  const data = await res.json();
  alert(data.message);

  if (res.ok) {
    await loadBookings(localStorage.getItem("email"));
    await loadNotifications();
  }
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

function escapeAttribute(value) {
  return escapeHTML(value).replace(/`/g, "&#096;");
}

initDashboard();
