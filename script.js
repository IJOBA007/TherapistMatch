let socket = null;
const ADMIN_CONSOLE_PATH = "/tm-console-7f3a9c";

function getEmailValue() {
  return document.getElementById("email").value.trim().toLowerCase();
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showAuthMessage(message) {
  const messageElement = document.getElementById("message");
  if (messageElement) {
    messageElement.innerText = message;
  }
}

function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}

async function signup() {
  const email = getEmailValue();
  const password = document.getElementById("password").value;
  const role = document.getElementById("role").value;

  if (!email || !password) {
    showAuthMessage("Please enter email and password");
    return;
  }

  if (!isValidEmail(email)) {
    showAuthMessage("Please enter a valid email address.");
    return;
  }

  if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    showAuthMessage("Password must be at least 8 characters and include a letter and a number.");
    return;
  }

  try {
    const payload = { email, password, role };

    if (role === "admin") {
      const adminCode = prompt("Enter the admin signup code if one was provided.");
      if (adminCode) {
        payload.admin_code = adminCode;
      }
    }

    const res = await fetch("/signup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    console.log("Signup response:", data);

    if (res.ok) {
      localStorage.setItem("userRole", role);
      localStorage.setItem("email", email);
      localStorage.setItem("sessionToken", data.token || "");

      if (role === "therapist") {
        window.location.href = "therapist.html";
      } else if (role === "admin") {
        window.location.href = ADMIN_CONSOLE_PATH;
      } else {
        window.location.href = "dashboard.html";
      }
    } else {
      showAuthMessage(data.message);
    }
  } catch (error) {
    console.error("Signup error:", error);
    showAuthMessage("Connection error. Is the server running?");
  }
}

async function login() {
  const email = getEmailValue();
  const password = document.getElementById("password").value;
  const role = document.getElementById("role").value;

  if (!email || !password) {
    showAuthMessage("Please enter email and password");
    return;
  }

  if (!isValidEmail(email)) {
    showAuthMessage("Please enter a valid email address.");
    return;
  }

  try {
    const res = await fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ email, password, role })
    });

    const data = await res.json();
    console.log("Login response:", data);

    if (res.ok && data.message === "Login successful") {
      localStorage.setItem("userRole", data.role);
      localStorage.setItem("email", email);
      localStorage.setItem("sessionToken", data.token || "");

      if (data.role === "admin") {
        localStorage.clear();
        showAuthMessage("Please use the admin access page for this account.");
        return;
      }

      if (data.role === "therapist") {
        window.location.href = "therapist.html";
      } else {
        window.location.href = "dashboard.html";
      }
    } else {
      showAuthMessage(data.message || "Login failed");
    }
  } catch (error) {
    console.error("Login error:", error);
    showAuthMessage("Connection error. Is the server running?");
  }
}

async function bookSession(therapistEmail, date, clientNeeds = [], options = {}) {
  const email = localStorage.getItem("email");
  const sessionCount = Math.max(1, Number(options.sessionCount || options.session_count || 1) || 1);

  if (!email) {
    alert("Please log in before booking a session.");
    window.location.href = "index.html";
    return;
  }

  if (!date) {
    const message = "Please choose the appointment day and time.";
    if (!options.silent) alert(message);
    return { ok: false, data: { message } };
  }

  const res = await fetch("/book", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      user_email: email,
      therapist_email: therapistEmail,
      date,
      client_needs: clientNeeds,
      session_count: sessionCount
    })
  });

  const data = await res.json();
  if (!options.silent) {
    alert(data.message);
  }

  return { ok: res.ok, status: res.status, data };
}

async function pay() {
  const res = await fetch("/pay", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: localStorage.getItem("email"),
      amount: 500000,
      currency: "NGN",
      provider: "manual"
    })
  });

  const data = await res.json();
  alert(data.message);
}

const welcome = document.getElementById("welcome");

if (welcome) {
  welcome.innerText = "Welcome back, " + localStorage.getItem("email");
}

function payWithPaystack() {
  let handler = PaystackPop.setup({
    key: "pk_test_1fab358fb60e7c6d5fd6898d94c29be6e314cde8",
    email: localStorage.getItem("email"),
    amount: 500000,
    currency: "NGN",

    callback: function(response) {
      alert("Payment successful!");

      fetch("/verify_payment", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          email: localStorage.getItem("email"),
          amount: 500000,
          currency: "NGN",
          reference: response.reference
        })
      });
    },

    onClose: function() {
      alert("Payment cancelled");
    }
  });

  handler.openIframe();
}

if (document.getElementById("chatBox")) {
  socket = io();

  socket.on("message", function(msg) {
    document.getElementById("chatBox").innerHTML += `<p>${msg}</p>`;
  });
}

function sendMsg() {
  const msg = document.getElementById("msg").value;
  if (!socket) return;
  socket.send(msg);
}
