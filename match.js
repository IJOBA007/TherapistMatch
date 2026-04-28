const MIN_SPECIALTIES = 1;
const MAX_SPECIALTIES = 4;

document.addEventListener("DOMContentLoaded", () => {
  bindSpecialtyPicker();
  loadProfileLanguage();
});

document.addEventListener("click", event => {
  const button = event.target.closest("[data-book-email]");
  if (button) {
    bookSession(button.dataset.bookEmail);
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

  if (therapists.length === 0) {
    results.innerHTML = `
      <div class="empty-state">
        <strong>No verified therapists found</strong>
        <p>Try a different language or specialty combination.</p>
      </div>
    `;
    return;
  }

  results.innerHTML = therapists.map(therapist => `
    <article class="match-card">
      ${therapist.profile_photo ? `<img class="profile-photo" src="${therapist.profile_photo}" alt="">` : ""}
      <div>
        <h3>${escapeHTML(therapist.name || "Therapist")}</h3>
        <p>${escapeHTML(therapist.specialization || "General Practice")}</p>
        <p>${escapeHTML(therapist.location || "Location not set")} - ${escapeHTML(formatLanguages(therapist))}</p>
        <p>${escapeHTML(formatRate(therapist.hourly_rate))}</p>
        <p><strong>Available:</strong> ${escapeHTML(formatAvailability(therapist.availability))}</p>
        <p>${escapeHTML(therapist.bio || "No bio added yet.")}</p>
      </div>
      <button type="button" data-book-email="${escapeAttribute(therapist.email)}">Book</button>
    </article>
  `).join("");
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
    return `Hourly rate: #${rate}`;
  }

  return `Hourly rate: #${numericRate.toLocaleString()}`;
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
