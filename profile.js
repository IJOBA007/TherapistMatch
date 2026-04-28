async function saveProfile() {
  const email = localStorage.getItem("email");
  if (!email) {
    alert("No email found in local storage.");
    return;
  }

  const specialties = [];
  document.querySelectorAll("#therapistSection input:checked").forEach(cb => {
    specialties.push(cb.value);
  });

  try {
    const res = await fetch("/update_profile", {
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
        specialties
      })
    });

    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }

    const data = await res.json();
    alert(data.message);

    document.getElementById("preview").innerText =
      "We will match you with therapists who speak " +
      document.getElementById("primaryLanguage").value;
  } catch (error) {
    console.error("Error saving profile:", error);
    alert("Failed to save profile. Please check the console for details.");
  }
}

function calculateAge(dob) {
  if (!dob) return '';
  const birthDate = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  return age;
}

// auto-fill on load
window.onload = function () {
  const email = localStorage.getItem("email");
  if (!email) return;

  fetch("/get_profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email })
  })
  .then(res => res.json())
  .then(data => {
    if (data.profile) {
      document.getElementById("name").value = data.profile.name || "";
      document.getElementById("dob").value = data.profile.dob || "";
      document.getElementById("ageDisplay").textContent = calculateAge(data.profile.dob);
      document.getElementById("gender").value = data.profile.gender || "";
      document.getElementById("location").value = data.profile.location || "";
      document.getElementById("primaryLanguage").value = data.profile.primary_language || "";
      document.getElementById("secondaryLanguage").value = data.profile.secondary_language || "";
    }
  });

  const role = localStorage.getItem("userRole");
  if (role === "therapist") {
    document.getElementById("therapistSection").style.display = "block";
  }

  // Update age display when DOB changes
  document.getElementById('dob').addEventListener('change', function() {
    document.getElementById('ageDisplay').textContent = calculateAge(this.value);
  });
};

function enableEdit() {
  document.querySelectorAll("input, select").forEach(el => {
    el.disabled = false;
  });
}