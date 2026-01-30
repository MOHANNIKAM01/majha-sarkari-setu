/* Small UX improvements */
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
});
