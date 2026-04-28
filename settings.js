const SETTINGS_API_BASE = "";
const SESSION_DEPOSIT_KOBO = 500000;

document.addEventListener("DOMContentLoaded", () => {
  const email = localStorage.getItem("email");
  const role = localStorage.getItem("userRole");

  if (!email || role !== "user") {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("profileForm").addEventListener("submit", saveProfile);
  document.getElementById("editProfileBtn").addEventListener("click", enableEdit);
  document.getElementById("dob").addEventListener("change", updateAge);
  document.getElementById("paystackButton").addEventListener("click", payWithPaystackFromSettings);
  document.getElementById("recordPaymentButton").addEventListener("click", recordTestPayment);

  loadProfile();
});

async function loadProfile() {
  const email = localStorage.getItem("email");

  try {
    const res = await fetch(`${SETTINGS_API_BASE}/get_profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    const data = await res.json();

    if (data.profile) {
      document.getElementById("name").value = data.profile.name || "";
      document.getElementById("dob").value = data.profile.dob || "";
      document.getElementById("gender").value = data.profile.gender || "";
      document.getElementById("location").value = data.profile.location || "";
      document.getElementById("primaryLanguage").value = data.profile.primary_language || "";
      document.getElementById("secondaryLanguage").value = data.profile.secondary_language || "";
      updateAge();
    }
  } catch (error) {
    console.error("Profile load failed:", error);
  }
}

async function saveProfile(event) {
  event.preventDefault();

  const email = localStorage.getItem("email");
  const preview = document.getElementById("preview");

  try {
    const res = await fetch(`${SETTINGS_API_BASE}/update_profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        name: document.getElementById("name").value,
        dob: document.getElementById("dob").value,
        gender: document.getElementById("gender").value,
        location: document.getElementById("location").value,
        primary_language: document.getElementById("primaryLanguage").value,
        secondary_language: document.getElementById("secondaryLanguage").value,
        specialties: []
      })
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.message || "Profile update failed");
    }

    preview.textContent = "Profile saved. We will match you with therapists who speak " + document.getElementById("primaryLanguage").value + ".";
    disableProfileFields();
  } catch (error) {
    preview.textContent = error.message;
  }
}

function enableEdit() {
  document.querySelectorAll("#profileForm input, #profileForm select").forEach(element => {
    if (element.id !== "ageDisplay") {
      element.disabled = false;
    }
  });
}

function disableProfileFields() {
  document.querySelectorAll("#profileForm input, #profileForm select").forEach(element => {
    element.disabled = true;
  });
}

function updateAge() {
  document.getElementById("ageDisplay").value = calculateAge(document.getElementById("dob").value);
}

function calculateAge(dob) {
  if (!dob) return "";
  const birthDate = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();

  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }

  return age;
}

function payWithPaystackFromSettings() {
  const email = localStorage.getItem("email");
  const paymentMessage = document.getElementById("paymentMessage");

  if (!window.PaystackPop) {
    paymentMessage.textContent = "Paystack is not loaded. Please check your internet connection.";
    return;
  }

  const handler = PaystackPop.setup({
    key: "pk_test_1fab358fb60e7c6d5fd6898d94c29be6e314cde8",
    email,
    amount: SESSION_DEPOSIT_KOBO,
    currency: "NGN",
    callback: async function(response) {
      paymentMessage.textContent = "Payment received. Verifying...";

      const res = await fetch(`${SETTINGS_API_BASE}/verify_payment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          amount: SESSION_DEPOSIT_KOBO,
          currency: "NGN",
          reference: response.reference
        })
      });
      const data = await res.json();
      paymentMessage.textContent = data.message;
    },
    onClose: function() {
      paymentMessage.textContent = "Payment window closed.";
    }
  });

  handler.openIframe();
}

async function recordTestPayment() {
  const paymentMessage = document.getElementById("paymentMessage");
  const res = await fetch(`${SETTINGS_API_BASE}/pay`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: localStorage.getItem("email"),
      amount: SESSION_DEPOSIT_KOBO,
      currency: "NGN",
      provider: "paystack-test"
    })
  });
  const data = await res.json();
  paymentMessage.textContent = data.message + " (" + data.reference + ")";
}
