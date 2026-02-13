/* Small UX improvements + Mobile Navbar Toggle */
document.addEventListener("DOMContentLoaded", () => {
  // Smooth scroll for anchor links (if any)
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener("click", (e) => {
      const id = a.getAttribute("href");
      const el = document.querySelector(id);
      if (el) {
        e.preventDefault();
        el.scrollIntoView({ behavior: "smooth" });
      }
    });
  });

  // ✅ Mobile navbar hamburger toggle
  const btn = document.querySelector(".nav-toggle");
  const nav = document.getElementById("siteNav");

  if (btn && nav) {
    btn.addEventListener("click", () => {
      const opened = nav.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", opened ? "true" : "false");
    });
  }
});