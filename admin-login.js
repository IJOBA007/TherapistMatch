const ADMIN_CONSOLE_PATH = "/admin/console";

function getAdminEmail() {
  return document.getElementById("adminEmail").value.trim().toLowerCase();
}

function getAdminPassword() {
  return document.getElementById("adminPassword").value;
}

function showAdminMessage(message) {
  document.getElementById("adminMessage").textContent = message;
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

  const adminCode = prompt("Enter the admin signup code if one was provided.");
  const payload = {
    ...credentials,
    role: "admin"
  };

  if (adminCode) {
    payload.admin_code = adminCode;
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
      return;
    }

    localStorage.setItem("userRole", "admin");
    localStorage.setItem("email", credentials.email);
    localStorage.setItem("sessionToken", data.token || "");
    window.location.href = ADMIN_CONSOLE_PATH;
  } catch (error) {
    console.error("Admin signup error:", error);
    showAdminMessage("Connection error. Is the server running?");
  }
}
