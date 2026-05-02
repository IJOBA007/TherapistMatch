const MIN_SPECIALTIES = 1;
const MAX_SPECIALTIES = 4;
const MAX_CONSECUTIVE_SESSIONS = 8;

let currentTherapists = [];

document.addEventListener("DOMContentLoaded", () => {
  bindSpecialtyPicker();
  loadProfileLanguage();

  const preferredDate = document.getElementById("preferredDate");
  if (preferredDate) {
    preferredDate.min = getTodayDate();
  }

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

document.addEventListener("change", event => {
  const dateInput = event.target.closest("[data-book-date]");
  if (dateInput) {
    updateTimeSlots(dateInput);
    return;
  }

  const timeSelect = event.target.closest("[data-book-time]");
  if (timeSelect) {
    updateSessionCountOptions(timeSelect.closest(".match-card"));
    updateBookingButtonState(timeSelect.closest(".match-card"));
    return;
  }

  const sessionCount = event.target.closest("[data-session-count]");
  if (sessionCount) {
    updateBookingButtonState(sessionCount.closest(".match-card"));
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

function getPreferredDateTime() {
  const date = document.getElementById("preferredDate")?.value || "";
  const time = document.getElementById("preferredTime")?.value || "";

  if (!date && !time) {
    return { date: "", time: "", value: "" };
  }

  if (!date || !time) {
    return { error: "Choose both preferred date and preferred time, or leave both blank." };
  }

  return {
    date,
    time,
    value: `${date}T${time}`
  };
}

async function findMatch() {
  const primaryLanguage = document.getElementById("language").value;
  const specializations = getSelectedSpecialties();
  const preferred = getPreferredDateTime();
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

  if (preferred.error) {
    message.textContent = preferred.error;
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
      specializations,
      preferred_datetime: preferred.value
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
  const preferred = getPreferredDateTime();

  results.innerHTML = sortedTherapists.map(therapist => {
    const hasManualAvailability = therapist.manual_availability == 1;
    const isOnline = therapist.online_status === "online";
    const statusBadge = hasManualAvailability || isOnline 
      ? '<span class="online-badge">● Online</span>' 
      : '';
    const cleanStatusBadge = hasManualAvailability || isOnline
      ? '<span class="online-badge">Available now</span>'
      : '';
    const availabilityLabel = hasManualAvailability || isOnline
      ? "Accepting requests at any time while available now"
      : formatAvailability(therapist.availability);
    
    return `
    <article class="match-card">
      ${therapist.profile_photo ? `<img class="profile-photo" src="${therapist.profile_photo}" alt="">` : ""}
      <div>
        <h3>${escapeHTML(therapist.name || "Therapist")} ${cleanStatusBadge}</h3>
        <p>${escapeHTML(therapist.specialization || "General Practice")}</p>
        <p>${escapeHTML(therapist.location || "Location not set")} - ${escapeHTML(formatLanguages(therapist))}</p>
        <p>${escapeHTML(formatRate(therapist.hourly_rate))}</p>
        <p>${escapeHTML(formatRating(therapist))}</p>
        <p><strong>Available:</strong> ${escapeHTML(availabilityLabel)}</p>
        <p>${escapeHTML(therapist.bio || "No bio added yet.")}</p>
      </div>
      <div class="booking-controls">
        <label>
          Session date
          <input type="date" data-book-date min="${escapeAttribute(getTodayDate())}" value="${escapeAttribute(preferred.date || "")}" data-availability="${escapeAttribute(therapist.availability || "")}" data-manual-availability="${hasManualAvailability || isOnline ? "1" : "0"}" data-preferred-time="${escapeAttribute(preferred.value || "")}">
        </label>
        <label class="time-slot-container" style="display: none;">
          Available times
          <select data-book-time></select>
        </label>
        <label class="session-count-container" style="display: none;">
          Sessions in a row
          <select data-session-count></select>
        </label>
        <button type="button" data-book-email="${escapeAttribute(therapist.email)}" disabled>Book</button>
        <p class="booking-feedback" data-book-message></p>
      </div>
    </article>
  `;
  }).join("");

  results.querySelectorAll("[data-book-date]").forEach(input => {
    if (input.value) {
      updateTimeSlots(input);
    }
  });
}

function getTodayDate() {
  const today = new Date();
  return today.toISOString().split('T')[0];
}

function updateTimeSlots(dateInput) {
  const card = dateInput.closest(".match-card");
  const timeContainer = card.querySelector(".time-slot-container");
  const timeSelect = card.querySelector("[data-book-time]");
  const selectedDate = dateInput.value;
  const availabilityJson = dateInput.dataset.availability || "";
  const hasManualAvailability = dateInput.dataset.manualAvailability === "1";
  const preferredTime = dateInput.dataset.preferredTime || "";

  if (!selectedDate) {
    timeContainer.style.display = "none";
    timeSelect.innerHTML = "";
    updateSessionCountOptions(card);
    updateBookingButtonState(card);
    return;
  }

  if (hasManualAvailability) {
    const allSlots = generateTimeSlots("00:00", "24:00", 30);
    fillTimeSelect(timeSelect, selectedDate, allSlots, preferredTime);
    timeContainer.style.display = "block";
    updateSessionCountOptions(card);
    updateBookingButtonState(card);
    return;
  }

  const availability = parseAvailability(availabilityJson);
  if (!availability.slots.length) {
    timeSelect.innerHTML = '<option value="">Therapist availability not set</option>';
    timeContainer.style.display = "block";
    updateSessionCountOptions(card);
    updateBookingButtonState(card);
    return;
  }

  const date = new Date(`${selectedDate}T00:00`);
  const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const selectedDay = days[date.getDay()];
  const daySlots = availability.slots.filter(slot => slot.day === selectedDay);

  if (!daySlots.length) {
    timeSelect.innerHTML = `<option value="">${selectedDay} - Not available</option>`;
    timeContainer.style.display = "block";
    updateSessionCountOptions(card);
    updateBookingButtonState(card);
    return;
  }

  let allSlots = [];
  daySlots.forEach(slot => {
    allSlots = allSlots.concat(generateTimeSlots(slot.start, slot.end, availability.duration || 60));
  });

  fillTimeSelect(timeSelect, selectedDate, allSlots, preferredTime);
  timeContainer.style.display = "block";
  updateSessionCountOptions(card);
  updateBookingButtonState(card);
}

function generateTimeSlots(startTime, endTime, duration) {
  const slots = [];
  const startMinutes = minutesFromTime(startTime);
  const endMinutes = endTime === "24:00" ? 24 * 60 : minutesFromTime(endTime);
  const step = Number(duration) || 60;

  if (startMinutes === null || endMinutes === null || endMinutes <= startMinutes) {
    return slots;
  }

  for (let minute = startMinutes; minute + step <= endMinutes; minute += step) {
    const value = timeFromMinutes(minute);
    slots.push({
      value,
      label: formatTime(value)
    });
  }

  return slots;
}

function fillTimeSelect(timeSelect, selectedDate, slots, preferredTime) {
  const optionItems = slots.map(slot => ({
    value: `${selectedDate}T${slot.value}`,
    label: slot.label
  }));

  if (preferredTime && preferredTime.startsWith(`${selectedDate}T`) && !optionItems.some(slot => slot.value === preferredTime)) {
    const preferredClock = preferredTime.slice(11, 16);
    optionItems.unshift({
      value: preferredTime,
      label: formatTime(preferredClock)
    });
  }

  timeSelect.innerHTML = '<option value="">Select a time</option>' +
    optionItems.map(slot => `<option value="${escapeAttribute(slot.value)}">${escapeHTML(slot.label)}</option>`).join("");

  if (preferredTime && optionItems.some(slot => slot.value === preferredTime)) {
    timeSelect.value = preferredTime;
  }
}

function updateSessionCountOptions(card) {
  if (!card) return;

  const countContainer = card.querySelector(".session-count-container");
  const countSelect = card.querySelector("[data-session-count]");
  const timeSelect = card.querySelector("[data-book-time]");

  if (!countContainer || !countSelect || !timeSelect?.value) {
    if (countContainer) countContainer.style.display = "none";
    if (countSelect) countSelect.innerHTML = "";
    return;
  }

  const previousValue = Number(countSelect.value || 1);
  const maxSessions = getMaxSessionsFromSelectedTime(card);
  countSelect.innerHTML = Array.from({ length: maxSessions }, (_, index) => {
    const count = index + 1;
    return `<option value="${count}">${count} session${count === 1 ? "" : "s"}</option>`;
  }).join("");
  countSelect.value = String(Math.min(previousValue || 1, maxSessions));
  countContainer.style.display = "block";
}

function getMaxSessionsFromSelectedTime(card) {
  const dateInput = card.querySelector("[data-book-date]");
  const timeSelect = card.querySelector("[data-book-time]");
  const selectedDate = dateInput?.value || "";
  const selectedTime = timeSelect?.value || "";

  if (!selectedDate || !selectedTime) {
    return 1;
  }

  if (dateInput.dataset.manualAvailability === "1") {
    return MAX_CONSECUTIVE_SESSIONS;
  }

  const availability = parseAvailability(dateInput.dataset.availability || "");
  const duration = Number(availability.duration || 60) || 60;
  const selectedMinute = minutesFromTime(selectedTime.slice(11, 16));
  if (selectedMinute === null) {
    return 1;
  }

  const date = new Date(`${selectedDate}T00:00`);
  const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const selectedDay = days[date.getDay()];
  const maxFromSlots = availability.slots
    .filter(slot => slot.day === selectedDay)
    .reduce((max, slot) => {
      const slotStart = minutesFromTime(slot.start);
      const slotEnd = minutesFromTime(slot.end);
      if (slotStart === null || slotEnd === null) return max;
      if (selectedMinute < slotStart || selectedMinute + duration > slotEnd) return max;
      return Math.max(max, Math.floor((slotEnd - selectedMinute) / duration));
    }, 1);

  return Math.max(1, Math.min(maxFromSlots, MAX_CONSECUTIVE_SESSIONS));
}

function updateBookingButtonState(card) {
  if (!card) return;

  const dateInput = card.querySelector("[data-book-date]");
  const timeSelect = card.querySelector("[data-book-time]");
  const countSelect = card.querySelector("[data-session-count]");
  const bookButton = card.querySelector("[data-book-email]");

  if (bookButton) {
    bookButton.disabled = !dateInput?.value || !timeSelect?.value || !countSelect?.value;
  }
}

function timeFromMinutes(totalMinutes) {
  const minutes = ((totalMinutes % (24 * 60)) + (24 * 60)) % (24 * 60);
  const hour = Math.floor(minutes / 60).toString().padStart(2, "0");
  const minute = (minutes % 60).toString().padStart(2, "0");
  return `${hour}:${minute}`;
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
  const dateInput = card.querySelector("[data-book-date]");
  const timeSelect = card.querySelector("[data-book-time]");
  const feedback = card.querySelector("[data-book-message]");
  
  const selectedDate = dateInput.value;
  const selectedTime = timeSelect.value;
  const sessionCount = Number(card.querySelector("[data-session-count]")?.value || 1);

  if (!selectedDate) {
    feedback.textContent = "Choose the session date first.";
    return;
  }
  
  if (!selectedTime) {
    feedback.textContent = "Choose the session time from available slots.";
    return;
  }

  button.disabled = true;
  feedback.textContent = "Checking therapist availability...";

  const result = await bookSession(button.dataset.bookEmail, selectedTime, getSelectedSpecialties(), {
    silent: true,
    sessionCount
  });
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
