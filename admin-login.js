const ADMIN_CONSOLE_PATH = "/tm-console-7f3a9c";
let adminTurnstileToken = "";
let adminTurnstileRequired = false;

function getAdminEmail() {
  return document.getElementById("adminEmail").value.trim().toLowerCase();
}

function getAdminPassword() {
  return document.getElementById("adminPassword").value;
}

function showAdminMessage(message) {
  document.getElementById("adminMessage").textContent = message;
}

function getAdminSignupStartedAt() {
  const startedAt = document.getElementById("adminSignupStartedAt");
  return startedAt ? startedAt.value : "";
}

function getAdminWebsiteTrapValue() {
  const website = document.getElementById("adminWebsite");
  return website ? website.value : "";
}

function resetAdminTurnstileWidget() {
  if (window.turnstile && adminTurnstileToken) {
    window.turnstile.reset();
  }
  adminTurnstileToken = "";
}

async function loadAdminTurnstile() {
  const widget = document.getElementById("adminTurnstileWidget");
  if (!widget) return;

  try {
    const res = await fetch("/security_config");
    const config = await res.json();
    adminTurnstileRequired = Boolean(config.turnstile_enabled);

    if (!adminTurnstileRequired || !config.turnstile_site_key) return;

    const renderWidget = () => {
      if (!window.turnstile) {
        setTimeout(renderWidget, 150);
        return;
      }

      window.turnstile.render(widget, {
        sitekey: config.turnstile_site_key,
        callback: token => {
          adminTurnstileToken = token;
        },
        "expired-callback": () => {
          adminTurnstileToken = "";
        },
        "error-callback": () => {
          adminTurnstileToken = "";
        }
      });
    };

    renderWidget();
  } catch (error) {
    console.error("Security config error:", error);
  }
}

function isValidAdminEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validateAdminForm() {
  const email = getAdminEmail();
  const password = getAdminPassword();

  if (!email || !password) {
    showAdminMessage("Please enter admin email and password.");
    return null;
  }

  if (!isValidAdminEmail(email)) {
    showAdminMessage("Please enter a valid admin email address.");
    return null;
  }

  return { email, password };
}

async function adminLogin() {
  const credentials = validateAdminForm();
  if (!credentials) return;

  showAdminMessage("Checking admin access...");

  try {
    const res = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...credentials, role: "admin" })
    });
    const data = await res.json();

    if (!res.ok) {
      showAdminMessage(data.message || "Admin login failed.");
      return;
    }

    if (data.role !== "admin") {
      localStorage.clear();
      showAdminMessage("This page is only for admin accounts.");
      return;
    }

    localStorage.setItem("userRole", "admin");
    localStorage.setItem("email", credentials.email);
    localStorage.setItem("sessionToken", data.token || "");
    window.location.href = ADMIN_CONSOLE_PATH;
  } catch (error) {
    console.error("Admin login error:", error);
    showAdminMessage("Connection error. Is the server running?");
  }
}

async function createAdminAccount() {
  const credentials = validateAdminForm();
  if (!credentials) return;

  if (credentials.password.length < 8 || !/[A-Za-z]/.test(credentials.password) || !/\d/.test(credentials.password)) {
    showAdminMessage("Password must be at least 8 characters and include a letter and a number.");
    return;
  }

  if (adminTurnstileRequired && !adminTurnstileToken) {
    showAdminMessage("Please complete the verification check.");
    return;
  }

  const adminCode = prompt("Enter the admin signup code if one was provided.");
  const payload = {
    ...credentials,
    role: "admin",
    signup_started_at: getAdminSignupStartedAt(),
    website: getAdminWebsiteTrapValue(),
    turnstile_token: adminTurnstileToken
  };

  if (adminCode) {
    payload.admin_code = adminCode.trim();
  }

  showAdminMessage("Creating admin access...");

  try {
    const res = await fetch("/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) {
      showAdminMessage(data.message || "Unable to create admin account.");
      resetAdminTurnstileWidget();
      return;
    }

    localStorage.setItem("userRole", "admin");
    localStorage.setItem("email", credentials.email);
    localStorage.setItem("sessionToken", data.token || "");
    window.location.href = ADMIN_CONSOLE_PATH;
  } catch (error) {
    console.error("Admin signup error:", error);
    showAdminMessage("Connection error. Is the server running?");
    resetAdminTurnstileWidget();
  }
}

const adminSignupStartedAt = document.getElementById("adminSignupStartedAt");
if (adminSignupStartedAt) {
  adminSignupStartedAt.value = String(Date.now());
}

loadAdminTurnstile();
