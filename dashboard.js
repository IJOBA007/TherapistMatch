function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}

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
    window.location.href = "admin.html";
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
  } catch (error) {
    console.error("Dashboard profile load failed:", error);
    setWelcome("Welcome User");
    await loadBookings(email);
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

  return `
    <article class="booking-row detailed-booking user-booking">
      <div class="booking-main">
        <div>
          <strong>${escapeHTML(therapist.name || booking.therapist_email)}</strong>
          <span>${escapeHTML(therapist.specialization || "General practice")}</span>
          <span>${escapeHTML(formatDateTime(booking.date))}</span>
        </div>
        <span class="booking-status">${escapeHTML(booking.status || "Pending")}</span>
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
    </article>
  `;
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

function formatDateTime(value) {
  if (!value) return "Date not set";
  return new Date(value).toLocaleString();
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
