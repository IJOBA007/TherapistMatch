const API_BASE = "";
const MIN_SPECIALTIES = 1;
const MAX_SPECIALTIES = 4;

let therapistProfile = null;

document.addEventListener("DOMContentLoaded", () => {
  initTherapistPortal();
});

async function initTherapistPortal() {
  const email = localStorage.getItem("email");
  const role = localStorage.getItem("userRole");

  if (!email || role !== "therapist") {
    window.location.href = "index.html";
    return;
  }

  bindNavigation();
  bindSpecialtyPicker();
  bindAvailabilityBuilder();
  document.getElementById("credentialsForm").addEventListener("submit", submitCredentials);

  await loadTherapistProfile();
  await loadBookings();
}

function bindSpecialtyPicker() {
  document.querySelectorAll("input[name='specialization']").forEach(input => {
    input.addEventListener("change", updateSpecialtyPicker);
  });

  updateSpecialtyPicker();
}

function getSelectedSpecialties() {
  return Array.from(document.querySelectorAll("input[name='specialization']:checked"))
    .map(input => input.value);
}

function updateSpecialtyPicker() {
  const selected = getSelectedSpecialties();
  const isAtLimit = selected.length >= MAX_SPECIALTIES;
  const counter = document.getElementById("therapistSpecialtyCounter");

  document.querySelectorAll("input[name='specialization']").forEach(input => {
    input.disabled = !input.checked && isAtLimit;
    input.closest("label").classList.toggle("disabled", input.disabled);
  });

  if (counter) {
    counter.textContent = `${selected.length} of ${MAX_SPECIALTIES} selected`;
  }
}

function bindAvailabilityBuilder() {
  document.querySelectorAll("input[name='availability_days']").forEach(input => {
    input.addEventListener("change", syncAvailabilityRows);
  });

  const sessionLength = document.getElementById("sessionLength");
  if (sessionLength) {
    sessionLength.addEventListener("change", updateAvailabilityBuilder);
  }

  syncAvailabilityRows();
}

function getSelectedAvailabilityDays() {
  return Array.from(document.querySelectorAll("input[name='availability_days']:checked"))
    .map(input => input.value);
}

function getAvailabilityRows() {
  return Array.from(document.querySelectorAll(".availability-time-row")).map(row => ({
    day: row.dataset.day,
    start: row.querySelector("[data-availability-start]").value,
    end: row.querySelector("[data-availability-end]").value
  }));
}

function syncAvailabilityRows() {
  const rowsContainer = document.getElementById("availabilityRows");
  const selectedDays = getSelectedAvailabilityDays();
  const existingSlots = [
    ...parseAvailability(document.getElementById("availability").value).slots,
    ...getAvailabilityRows()
  ];
  const slotMap = existingSlots.reduce((map, slot) => {
    if (slot.day) {
      map[slot.day] = slot;
    }
    return map;
  }, {});

  rowsContainer.innerHTML = selectedDays.map(day => {
    const slot = slotMap[day] || {};
    return `
      <div class="availability-time-row" data-day="${escapeAttribute(day)}">
        <strong>${escapeHTML(day)}</strong>
        <label>
          From
          <input type="time" data-availability-start value="${escapeAttribute(slot.start || "")}">
        </label>
        <label>
          Until
          <input type="time" data-availability-end value="${escapeAttribute(slot.end || "")}">
        </label>
      </div>
    `;
  }).join("");

  rowsContainer.querySelectorAll("input").forEach(input => {
    input.addEventListener("input", updateAvailabilityBuilder);
    input.addEventListener("change", updateAvailabilityBuilder);
  });

  updateAvailabilityBuilder();
}

function updateAvailabilityBuilder() {
  const availabilityInput = document.getElementById("availability");
  const summary = document.getElementById("availabilityDaysSummary");
  const preview = document.getElementById("availabilityPreview");
  const selectedDays = getSelectedAvailabilityDays();
  const duration = document.getElementById("sessionLength").value;
  const slots = getAvailabilityRows();
  const completeSlots = slots.filter(slot => slot.start && slot.end && slot.start < slot.end);

  if (summary) {
    summary.textContent = selectedDays.length ? `${selectedDays.length} day${selectedDays.length === 1 ? "" : "s"} selected` : "Select days";
  }

  if (selectedDays.length && completeSlots.length === selectedDays.length) {
    availabilityInput.value = JSON.stringify({
      duration,
      slots: completeSlots
    });
    preview.textContent = formatAvailability(availabilityInput.value);
    return;
  }

  if (!selectedDays.length) {
    availabilityInput.value = "";
    preview.textContent = "Select days, then set the exact time for each selected day.";
  } else {
    availabilityInput.value = "";
    preview.textContent = `Add start and end times for each selected day (${duration}-minute sessions).`;
  }
}

function validateAvailability() {
  const savedAvailability = document.getElementById("availability").value;
  const selectedDays = getSelectedAvailabilityDays();
  const slots = getAvailabilityRows();

  if (!selectedDays.length && savedAvailability) return "";
  if (!selectedDays.length) return "Please select at least one day you are available.";

  for (const slot of slots) {
    if (!slot.start || !slot.end) {
      return `Please enter both start and end time for ${slot.day}.`;
    }

    if (slot.start >= slot.end) {
      return `${slot.day}'s end time must be later than the start time.`;
    }
  }

  return "";
}

function hydrateAvailability(availability) {
  const availabilityInput = document.getElementById("availability");
  availabilityInput.value = availability || "";
  const parsedAvailability = parseAvailability(availability);

  document.querySelectorAll("input[name='availability_days']").forEach(input => {
    input.checked = parsedAvailability.slots.some(slot => slot.day === input.value);
  });
  setValue("sessionLength", parsedAvailability.duration || "60");

  if (!availability) {
    syncAvailabilityRows();
    return;
  }

  if (!parsedAvailability.slots.length) {
    document.getElementById("availabilityRows").innerHTML = "";
    document.getElementById("availabilityDaysSummary").textContent = "Select days";
    document.getElementById("availabilityPreview").textContent = formatAvailability(availability);
    return;
  }

  syncAvailabilityRows();
}

function bindNavigation() {
  document.querySelectorAll(".nav-button").forEach(button => {
    button.addEventListener("click", () => {
      const viewId = button.dataset.view;

      document.querySelectorAll(".nav-button").forEach(item => item.classList.remove("active"));
      button.classList.add("active");

      document.querySelectorAll(".therapist-view").forEach(view => {
        view.hidden = view.id !== viewId;
      });
    });
  });
}

async function loadTherapistProfile() {
  const email = localStorage.getItem("email");

  try {
    const res = await fetch(`${API_BASE}/get_therapist_profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });

    if (!res.ok) {
      throw new Error("Unable to load therapist profile");
    }

    const data = await res.json();
    therapistProfile = data.therapist;

    hydrateForm(therapistProfile);
    renderStatus(therapistProfile);
    renderProfileSummary(therapistProfile);
  } catch (error) {
    console.error(error);
    document.getElementById("statusPanel").innerHTML = `
      <div class="notice notice-error">
        <strong>Profile unavailable</strong>
        <p>Please log out and sign in again.</p>
      </div>
    `;
  }
}

function getStatus(profile) {
  if (!profile) return "draft";
  if (profile.verification_status) return profile.verification_status;
  if (profile.verified === 1) return "verified";
  return profile.license_number ? "pending" : "draft";
}

function renderStatus(profile) {
  const status = getStatus(profile);
  const statusLabel = document.getElementById("statusLabel");
  const statusPanel = document.getElementById("statusPanel");
  const title = document.getElementById("therapistTitle");
  const subtitle = document.getElementById("therapistSubtitle");
  const submitButton = document.getElementById("submitCredentialsBtn");
  const profileStrength = document.getElementById("profileStrength");

  statusLabel.textContent = status.charAt(0).toUpperCase() + status.slice(1);
  statusLabel.className = `status-${status}`;
  profileStrength.textContent = `${calculateProfileStrength(profile)}%`;

  if (status === "verified") {
    title.textContent = `Welcome, ${profile.name || "Therapist"}`;
    subtitle.textContent = "Your therapist profile is verified and visible to matching clients.";
    submitButton.textContent = "Save Profile";
    statusPanel.innerHTML = `
      <div class="notice notice-success">
        <strong>Verified therapist</strong>
        <p>Your profile is approved. Keep your bio, availability, and rates current.</p>
      </div>
    `;
    return;
  }

  if (status === "pending") {
    title.textContent = "Application under review";
    subtitle.textContent = "Your credentials have been submitted. You can still update the application while admin reviews it.";
    submitButton.textContent = "Update Application";
    statusPanel.innerHTML = `
      <div class="notice notice-pending">
        <strong>Pending verification</strong>
        <p>Admin is reviewing your license, credentials, bio, and uploaded documents.</p>
      </div>
    `;
    return;
  }

  if (status === "rejected") {
    title.textContent = "Update your application";
    subtitle.textContent = "Admin needs more information before approving this therapist profile.";
    submitButton.textContent = "Resubmit Application";
    statusPanel.innerHTML = `
      <div class="notice notice-error">
        <strong>Needs revision</strong>
        <p>${escapeHTML(profile.rejection_reason || "Please review your credentials and resubmit.")}</p>
      </div>
    `;
    return;
  }

  title.textContent = "Complete your therapist application";
  subtitle.textContent = "Add your credentials, practice details, bio, and supporting documents for admin review.";
  submitButton.textContent = "Submit for Verification";
  statusPanel.innerHTML = `
    <div class="notice notice-info">
      <strong>Application not submitted</strong>
      <p>Complete the form below to join the therapist verification queue.</p>
    </div>
  `;
}

function hydrateForm(profile) {
  if (!profile) return;

  setValue("name", profile.name);
  setValue("location", profile.location);
  setValue("primaryLanguage", profile.primary_language);
  setValue("secondaryLanguage", profile.secondary_language);
  setValue("licenseNumber", profile.license_number);
  setValue("licenseState", profile.license_state);
  setValue("licenseExpiry", profile.license_expiry);
  setValue("experienceYears", profile.experience_years);
  setValue("hourlyRate", profile.hourly_rate);
  hydrateAvailability(profile.availability);
  setValue("education", profile.education);
  setValue("certifications", profile.certifications);
  setValue("bio", profile.bio);

  const formats = profile.session_formats || [];
  document.querySelectorAll("input[name='session_formats']").forEach(input => {
    input.checked = formats.includes(input.value);
  });

  const specialties = String(profile.specialization || "")
    .split(",")
    .map(item => item.trim())
    .filter(Boolean);

  document.querySelectorAll("input[name='specialization']").forEach(input => {
    input.checked = specialties.includes(input.value);
  });
  updateSpecialtyPicker();
}

function setValue(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.value = value || "";
  }
}

async function submitCredentials(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const submitButton = document.getElementById("submitCredentialsBtn");
  const formMessage = document.getElementById("formMessage");
  const selectedSpecialties = getSelectedSpecialties();
  const availabilityMessage = validateAvailability();

  if (selectedSpecialties.length < MIN_SPECIALTIES) {
    formMessage.textContent = "Please select at least 1 specialty.";
    return;
  }

  if (selectedSpecialties.length > MAX_SPECIALTIES) {
    formMessage.textContent = "Please select no more than 4 specialties.";
    return;
  }

  if (availabilityMessage) {
    formMessage.textContent = availabilityMessage;
    return;
  }

  updateAvailabilityBuilder();
  const formData = new FormData(form);
  formData.set("availability", document.getElementById("availability").value);
  formData.append("email", localStorage.getItem("email"));
  submitButton.disabled = true;
  submitButton.textContent = "Saving...";
  formMessage.textContent = "";

  try {
    const res = await fetch(`${API_BASE}/submit_credentials`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.message || "Unable to save application");
    }

    formMessage.textContent = data.message;
    document.getElementById("profilePhoto").value = "";
    document.getElementById("credentialDocument").value = "";
    await loadTherapistProfile();
  } catch (error) {
    formMessage.textContent = error.message;
  } finally {
    renderStatus(therapistProfile);
    submitButton.disabled = false;
  }
}

function renderProfileSummary(profile) {
  const container = document.getElementById("profileSummary");
  const status = getStatus(profile);
  const formats = profile.session_formats && profile.session_formats.length
    ? profile.session_formats.join(", ")
    : "Not set";

  container.innerHTML = `
    <div class="profile-header">
      ${renderProfilePhoto(profile)}
      <div>
        <p class="eyebrow">${escapeHTML(status)}</p>
        <h3>${escapeHTML(profile.name || "Unnamed therapist")}</h3>
        <p>${escapeHTML(profile.specialization || "Specialization not set")}</p>
      </div>
    </div>

    <div class="profile-detail-grid">
      <div><span>Location</span><strong>${escapeHTML(profile.location || "Not set")}</strong></div>
      <div><span>Languages</span><strong>${escapeHTML([profile.primary_language, profile.secondary_language].filter(Boolean).join(", ") || "Not set")}</strong></div>
      <div><span>Experience</span><strong>${escapeHTML(profile.experience_years || "0")} years</strong></div>
      <div><span>Rate</span><strong>${escapeHTML(formatRate(profile.hourly_rate))}</strong></div>
      <div><span>Availability</span><strong>${escapeHTML(formatAvailability(profile.availability))}</strong></div>
      <div><span>Session formats</span><strong>${escapeHTML(formats)}</strong></div>
    </div>

    <div class="profile-copy">
      <h4>Bio</h4>
      <p>${escapeHTML(profile.bio || "Bio not added yet.")}</p>
      <h4>Education</h4>
      <p>${escapeHTML(profile.education || "Education not added yet.")}</p>
      <h4>Certifications</h4>
      <p>${escapeHTML(profile.certifications || "Certifications not added yet.")}</p>
      ${profile.credential_document ? `<a class="document-link" href="${profile.credential_document}" target="_blank" rel="noopener">View credential document</a>` : ""}
    </div>
  `;
}

function renderProfilePhoto(profile) {
  if (profile.profile_photo) {
    return `<img class="profile-photo" src="${profile.profile_photo}" alt="">`;
  }

  const initials = (profile.name || "TM")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0].toUpperCase())
    .join("");

  return `<div class="profile-photo placeholder">${escapeHTML(initials || "TM")}</div>`;
}

async function loadBookings() {
  const bookings = document.getElementById("bookings");

  if (!therapistProfile || getStatus(therapistProfile) !== "verified") {
    bookings.innerHTML = `
      <div class="empty-state">
        <strong>Bookings unlock after verification</strong>
        <p>Once admin verifies your profile, client session requests will appear here.</p>
      </div>
    `;
    return;
  }

  const res = await fetch(`${API_BASE}/therapist_bookings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: localStorage.getItem("email") })
  });
  const data = await res.json();

  if (!data.bookings || data.bookings.length === 0) {
    bookings.innerHTML = `
      <div class="empty-state">
        <strong>No bookings yet</strong>
        <p>New client session requests will show up here.</p>
      </div>
    `;
    return;
  }

  bookings.innerHTML = data.bookings.map(renderBookingCard).join("");
}

function renderBookingCard(booking) {
  const userEmail = booking.user_email || booking[0];
  const date = booking.date || booking[1];
  const status = booking.status || booking[2] || "Pending";
  const profile = booking.user_profile || {};
  const languages = [profile.primary_language, profile.secondary_language].filter(Boolean).join(", ") || "Not set";
  const specialties = profile.specialties && profile.specialties.length
    ? profile.specialties.join(", ")
    : "Not provided yet";

  return `
    <article class="booking-row detailed-booking">
      <div class="booking-main">
        <div>
          <strong>${escapeHTML(profile.name || userEmail)}</strong>
          <span>${escapeHTML(userEmail)}</span>
          <span>${escapeHTML(formatDateTime(date))}</span>
        </div>
        <span class="booking-status">${escapeHTML(status)}</span>
      </div>
      <div class="booking-profile">
        <h4>Client profile sent before session</h4>
        <div class="booking-profile-grid">
          <div><span>Gender</span><strong>${escapeHTML(profile.gender || "Not set")}</strong></div>
          <div><span>Location</span><strong>${escapeHTML(profile.location || "Not set")}</strong></div>
          <div><span>Languages</span><strong>${escapeHTML(languages)}</strong></div>
          <div><span>Client needs</span><strong>${escapeHTML(specialties)}</strong></div>
        </div>
      </div>
    </article>
  `;
}

function formatDateTime(value) {
  if (!value) return "Date not set";
  return new Date(value).toLocaleString();
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

function calculateProfileStrength(profile) {
  if (!profile) return 0;

  const fields = [
    profile.name,
    profile.location,
    profile.primary_language,
    profile.license_number,
    profile.license_state,
    profile.license_expiry,
    profile.specialization,
    profile.experience_years,
    profile.hourly_rate,
    profile.availability,
    profile.education,
    profile.bio,
    profile.credential_document
  ];
  const completed = fields.filter(Boolean).length;

  return Math.round((completed / fields.length) * 100);
}

function formatRate(rate) {
  if (!rate) return "Not set";
  const numericRate = Number(rate);
  if (Number.isNaN(numericRate)) {
    return `₦${rate}`;
  }

  return `₦${numericRate.toLocaleString()}`;
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

function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}
