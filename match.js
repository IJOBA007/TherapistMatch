const MIN_SPECIALTIES = 1;
const MAX_SPECIALTIES = 4;

let currentTherapists = [];

document.addEventListener("DOMContentLoaded", () => {
  bindSpecialtyPicker();
  loadProfileLanguage();

  const sortPreference = document.getElementById("sortPreference");
  if (sortPreference) {
    sortPreference.addEventListener("change", () => renderTherapists(currentTherapists));
  }
});

document.addEventListener("click", event => {
  const button = event.target.closest("[data-book-email]");
  if (button) {
    handleBooking(button);
  }
});

function bindSpecialtyPicker() {
  document.querySelectorAll("input[name='specialties']").forEach(input => {
    input.addEventListener("change", updateSpecialtyPicker);
  });

  updateSpecialtyPicker();
}

function getSelectedSpecialties() {
  return Array.from(document.querySelectorAll("input[name='specialties']:checked"))
    .map(input => input.value);
}

function updateSpecialtyPicker() {
  const selected = getSelectedSpecialties();
  const isAtLimit = selected.length >= MAX_SPECIALTIES;
  const counter = document.getElementById("specialtyCounter");
  const message = document.getElementById("matchMessage");

  document.querySelectorAll("input[name='specialties']").forEach(input => {
    input.disabled = !input.checked && isAtLimit;
    input.closest("label").classList.toggle("disabled", input.disabled);
  });

  counter.textContent = `${selected.length} of ${MAX_SPECIALTIES} selected`;

  if (selected.length === 0) {
    message.textContent = "Pick at least 1 specialty to start matching.";
  } else if (selected.length === MAX_SPECIALTIES) {
    message.textContent = "You have selected the maximum of 4 specialties.";
  } else {
    message.textContent = "";
  }
}

async function findMatch() {
  const primaryLanguage = document.getElementById("language").value;
  const specializations = getSelectedSpecialties();
  const results = document.getElementById("results");
  const message = document.getElementById("matchMessage");

  if (!primaryLanguage) {
    message.textContent = "Please choose the language you want your therapist to speak.";
    results.innerHTML = "";
    return;
  }

  if (specializations.length < MIN_SPECIALTIES) {
    message.textContent = "Please select at least 1 specialty.";
    results.innerHTML = "";
    return;
  }

  if (specializations.length > MAX_SPECIALTIES) {
    message.textContent = "Please select no more than 4 specialties.";
    results.innerHTML = "";
    return;
  }

  message.textContent = "";
  results.innerHTML = "<p>Searching...</p>";

  const res = await fetch("/match", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      primary_language: primaryLanguage,
      specializations
    })
  });

  const data = await res.json();

  if (!res.ok) {
    results.innerHTML = `
      <div class="empty-state">
        <strong>Unable to match right now</strong>
        <p>${escapeHTML(data.message || "Please try again.")}</p>
      </div>
    `;
    return;
  }

  const therapists = data.therapists || [];
  currentTherapists = therapists;

  if (therapists.length === 0) {
    results.innerHTML = `
      <div class="empty-state">
        <strong>No verified therapists found</strong>
        <p>Try a different language or specialty combination.</p>
      </div>
    `;
    return;
  }

  renderTherapists(therapists);
}

function renderTherapists(therapists) {
  const results = document.getElementById("results");
  const sortedTherapists = sortTherapists([...(therapists || [])]);

  results.innerHTML = sortedTherapists.map(therapist => `
    <article class="match-card">
      ${therapist.profile_photo ? `<img class="profile-photo" src="${therapist.profile_photo}" alt="">` : ""}
      <div>
        <h3>${escapeHTML(therapist.name || "Therapist")}</h3>
        <p>${escapeHTML(therapist.specialization || "General Practice")}</p>
        <p>${escapeHTML(therapist.location || "Location not set")} - ${escapeHTML(formatLanguages(therapist))}</p>
        <p>${escapeHTML(formatRate(therapist.hourly_rate))}</p>
        <p>${escapeHTML(formatRating(therapist))}</p>
        <p><strong>Available:</strong> ${escapeHTML(formatAvailability(therapist.availability))}</p>
        <p>${escapeHTML(therapist.bio || "No bio added yet.")}</p>
      </div>
      <div class="booking-controls">
        <label>
          Session time
          <input type="datetime-local" data-book-time min="${escapeAttribute(getBookingMinimum())}">
        </label>
        <button type="button" data-book-email="${escapeAttribute(therapist.email)}">Book</button>
        <p class="booking-feedback" data-book-message></p>
      </div>
    </article>
  `).join("");
}

function sortTherapists(therapists) {
  const preference = document.getElementById("sortPreference")?.value || "best";

  return therapists.sort((first, second) => {
    if (preference === "pay") {
      return getRateValue(first.hourly_rate) - getRateValue(second.hourly_rate);
    }

    if (preference === "availability") {
      return getAvailabilityScore(second.availability) - getAvailabilityScore(first.availability);
    }

    if (preference === "rating") {
      return getRatingValue(second) - getRatingValue(first);
    }

    return getRatingValue(second) - getRatingValue(first)
      || getAvailabilityScore(second.availability) - getAvailabilityScore(first.availability)
      || getRateValue(first.hourly_rate) - getRateValue(second.hourly_rate);
  });
}

async function handleBooking(button) {
  const card = button.closest(".match-card");
  const timeInput = card.querySelector("[data-book-time]");
  const feedback = card.querySelector("[data-book-message]");
  const selectedTime = timeInput.value;

  if (!selectedTime) {
    feedback.textContent = "Choose the session day and time first.";
    return;
  }

  button.disabled = true;
  feedback.textContent = "Checking therapist availability...";

  const result = await bookSession(button.dataset.bookEmail, selectedTime, getSelectedSpecialties(), { silent: true });
  feedback.textContent = result?.data?.message || "Unable to book right now.";
  feedback.classList.toggle("success", Boolean(result?.ok));
  feedback.classList.toggle("error", !result?.ok);
  button.disabled = false;
}

async function loadProfileLanguage() {
  const email = localStorage.getItem("email");
  if (!email) return;

  try {
    const res = await fetch("/get_profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    const language = data.profile && data.profile.primary_language;

    if (language) {
      document.getElementById("language").value = language;
    }
  } catch (error) {
    console.error("Profile language load failed:", error);
  }
}

function formatLanguages(therapist) {
  return [therapist.primary_language, therapist.secondary_language]
    .filter(Boolean)
    .join(", ") || "Language not set";
}

function formatRate(rate) {
  if (!rate) return "Rate not set";
  const numericRate = Number(rate);
  if (Number.isNaN(numericRate)) {
    return `Hourly rate: NGN ${rate}`;
  }

  return `Hourly rate: NGN ${numericRate.toLocaleString()}`;
}

function formatRating(therapist) {
  const rating = Number(therapist.rating_average || 0);
  const count = Number(therapist.rating_count || 0);

  if (!rating || !count) {
    return "Quality rating: New therapist";
  }

  return `Quality rating: ${rating.toFixed(1)} / 5 (${count} rating${count === 1 ? "" : "s"})`;
}

function getRateValue(rate) {
  const numericRate = Number(rate);
  return Number.isNaN(numericRate) || numericRate <= 0 ? Number.MAX_SAFE_INTEGER : numericRate;
}

function getRatingValue(therapist) {
  return Number(therapist.rating_average || 0);
}

function getAvailabilityScore(value) {
  const availability = parseAvailability(value);

  return availability.slots.reduce((total, slot) => {
    const start = minutesFromTime(slot.start);
    const end = minutesFromTime(slot.end);
    return start === null || end === null || end <= start ? total : total + (end - start);
  }, 0);
}

function minutesFromTime(value) {
  if (!value || !value.includes(":")) return null;
  const [hourValue, minuteValue] = value.split(":");
  const hour = Number(hourValue);
  const minute = Number(minuteValue);

  if (Number.isNaN(hour) || Number.isNaN(minute)) return null;
  return hour * 60 + minute;
}

function getBookingMinimum() {
  const date = new Date(Date.now() + 60 * 60 * 1000);
  date.setMinutes(Math.ceil(date.getMinutes() / 15) * 15, 0, 0);
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return offsetDate.toISOString().slice(0, 16);
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
    // Keep supporting older profiles that saved availability as readable text.
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
  if (!availability.slots.length) return "Not set";

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
