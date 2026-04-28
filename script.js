let socket = null;

function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}

async function signup() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const role = document.getElementById("role").value;

  if (!email || !password) {
    document.getElementById("message").innerText = "Please enter email and password";
    return;
  }

  try {
    const res = await fetch("/signup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ email, password, role })
    });

    const data = await res.json();
    console.log("Signup response:", data);

    if (res.ok) {
      localStorage.setItem("userRole", role);
      localStorage.setItem("email", email);

      if (role === "therapist") {
        window.location.href = "therapist.html";
      } else if (role === "admin") {
        window.location.href = "admin.html";
      } else {
        window.location.href = "dashboard.html";
      }
    } else {
      document.getElementById("message").innerText = data.message;
    }
  } catch (error) {
    console.error("Signup error:", error);
    document.getElementById("message").innerText = "Connection error. Is the server running?";
  }
}

async function login() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  try {
    const res = await fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();
    console.log("Login response:", data);

    if (res.ok && data.message === "Login successful") {
      localStorage.setItem("userRole", data.role);
      localStorage.setItem("email", email);

      if (data.role === "therapist") {
        window.location.href = "therapist.html";
      } else if (data.role === "admin") {
        window.location.href = "admin.html";
      } else {
        window.location.href = "dashboard.html";
      }
    } else {
      document.getElementById("message").innerText = data.message || "Login failed";
    }
  } catch (error) {
    console.error("Login error:", error);
    document.getElementById("message").innerText = "Connection error. Is the server running?";
  }
}

async function bookSession(therapistEmail) {
  const email = localStorage.getItem("email");

  if (!email) {
    alert("Please log in before booking a session.");
    window.location.href = "index.html";
    return;
  }

  const res = await fetch("/book", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      user_email: email,
      therapist_email: therapistEmail,
      date: new Date().toISOString()
    })
  });

  const data = await res.json();
  alert(data.message);
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
