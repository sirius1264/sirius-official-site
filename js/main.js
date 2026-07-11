// ==========================================================================
// Sirius Official Site — main.js
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  initHeader();
  initNavToggle();
  initHeroImage();
  initReveal();
  initCountdown();
  initFooterYear();
  initContactForm();
});

// --- header: add background once scrolled past the hero -------------------------------
function initHeader() {
  const header = document.getElementById("siteHeader");
  const hero = document.querySelector(".hero");
  const threshold = () => (hero ? hero.offsetHeight - header.offsetHeight : 20);
  const onScroll = () => header.classList.toggle("scrolled", window.scrollY > threshold());
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
}

// --- hero image: fall back to a gradient if the photo hasn't been added yet ----------
function initHeroImage() {
  const media = document.querySelector(".hero-media");
  const img = document.getElementById("heroImage");
  if (!media || !img) return;

  const showFallback = () => media.classList.add("no-photo");

  if (img.complete) {
    if (img.naturalWidth === 0) showFallback();
  } else {
    img.addEventListener("error", showFallback);
  }

  // プロフィール写真も未設置なら壊れたアイコンを出さずグレーの背景だけにする
  document.querySelectorAll(".profile-img").forEach((el) => {
    el.addEventListener("error", () => { el.style.display = "none"; });
  });
}

// --- fade/slide-in reveal for sections as they scroll into view ----------------------
function initReveal() {
  const targets = document.querySelectorAll(".reveal");
  if (!targets.length) return;

  if (!("IntersectionObserver" in window)) {
    targets.forEach((el) => el.classList.add("in-view"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -80px 0px" }
  );

  targets.forEach((el) => observer.observe(el));
}

// --- mobile nav toggle ----------------------------------------------------
function initNavToggle() {
  const toggle = document.getElementById("navToggle");
  const nav = document.getElementById("nav");

  toggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    toggle.classList.toggle("is-open", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      nav.classList.remove("is-open");
      toggle.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    });
  });
}

// --- release countdown -----------------------------------------------------
function initCountdown() {
  const el = document.getElementById("countdown");
  if (!el) return;

  const target = new Date(el.dataset.target).getTime();
  const note = document.getElementById("releaseNote");
  const dEl = document.getElementById("cd-days");
  const hEl = document.getElementById("cd-hours");
  const mEl = document.getElementById("cd-mins");
  const sEl = document.getElementById("cd-secs");

  function tick() {
    const diff = target - Date.now();

    if (diff <= 0) {
      el.style.display = "none";
      note.textContent = "配信中です！";
      clearInterval(timer);
      return;
    }

    const days = Math.floor(diff / 86400000);
    const hours = Math.floor((diff % 86400000) / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    const secs = Math.floor((diff % 60000) / 1000);

    dEl.textContent = String(days).padStart(2, "0");
    hEl.textContent = String(hours).padStart(2, "0");
    mEl.textContent = String(mins).padStart(2, "0");
    sEl.textContent = String(secs).padStart(2, "0");
  }

  tick();
  const timer = setInterval(tick, 1000);
}

// --- footer year ------------------------------------------------------------
function initFooterYear() {
  const el = document.getElementById("year");
  if (el) el.textContent = new Date().getFullYear();
}

// --- contact form -------------------------------------------------------------
function initContactForm() {
  const form = document.getElementById("contactForm");
  const note = document.getElementById("formNote");
  if (!form) return;

  form.addEventListener("submit", (event) => {
    const action = form.getAttribute("action") || "";

    // フォーム送信サービス（Formspreeなど）が未設定の場合は案内を表示して送信をブロックする
    if (action.includes("your-form-id")) {
      event.preventDefault();
      note.textContent = "フォームの送信先が未設定です。Formspree等でエンドポイントを取得し、index.html の action 属性を差し替えてください。";
      note.style.color = "#ff6a3d";
      return;
    }

    note.textContent = "送信中...";
    note.style.color = "";
  });
}
