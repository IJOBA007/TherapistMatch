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
  } catch (error) {
    console.error("Dashboard profile load failed:", error);
    setWelcome("Welcome User");
  }
}

initDashboard();
