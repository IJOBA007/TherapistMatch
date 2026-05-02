document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector(".sidebar, .therapist-sidebar");
  if (!sidebar) return;

  document.body.classList.add("has-mobile-sidebar");
  loadSidebarBadges();

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "sidebar-toggle";
  toggle.setAttribute("aria-expanded", "false");
  toggle.textContent = "Menu";

  const backdrop = document.createElement("div");
  backdrop.className = "sidebar-backdrop";

  document.body.prepend(toggle);
  document.body.appendChild(backdrop);

  function openSidebar() {
    document.body.classList.add("sidebar-open");
    toggle.setAttribute("aria-expanded", "true");
  }

  function closeSidebar() {
    document.body.classList.remove("sidebar-open");
    toggle.setAttribute("aria-expanded", "false");
  }

  toggle.addEventListener("click", () => {
    if (document.body.classList.contains("sidebar-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  backdrop.addEventListener("click", closeSidebar);

  sidebar.addEventListener("click", event => {
    if (event.target.closest("a, .nav-button")) {
      closeSidebar();
    }
  });

  let touchStartX = 0;
  let touchStartY = 0;

  document.addEventListener("touchstart", event => {
    const touch = event.touches[0];
    touchStartX = touch.clientX;
    touchStartY = touch.clientY;
  }, { passive: true });

  document.addEventListener("touchend", event => {
    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - touchStartX;
    const deltaY = Math.abs(touch.clientY - touchStartY);
    const isHorizontalSwipe = Math.abs(deltaX) > 70 && deltaY < 80;

    if (!isHorizontalSwipe) return;

    if (touchStartX < 28 && deltaX > 0) {
      openSidebar();
    }

    if (document.body.classList.contains("sidebar-open") && deltaX < 0) {
      closeSidebar();
    }
  }, { passive: true });
});

async function loadSidebarBadges() {
  const email = localStorage.getItem("email");
  const role = localStorage.getItem("userRole");

  if (!email || !role) return;

  try {
    const res = await fetch("/get_notifications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, role })
    });

    if (!res.ok) return;

    const data = await res.json();
    const bookingTarget = role === "therapist" ? "bookings" : "dashboard";

    setSidebarBadge(bookingTarget, data.bookings || 0);
    setSidebarBadge("support", data.support || 0);
  } catch (error) {
    console.error("Sidebar badge load failed:", error);
  }
}

function setSidebarBadge(name, count) {
  document.querySelectorAll(`[data-badge='${name}']`).forEach(badge => {
    if (count > 0) {
      badge.textContent = count;
      badge.style.display = "inline-flex";
    } else {
      badge.textContent = "";
      badge.style.display = "none";
    }
  });
}
