// alert("NEW SCRIPT IS RUNNING");
document.addEventListener("DOMContentLoaded", function () {

  /* ---------------- sidebar toggle (mobile) ---------------- */
  var toggle = document.getElementById("sidebarToggle");
  var sidebar = document.getElementById("sidebar");

  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
    document.addEventListener("click", function (e) {
      if (window.innerWidth <= 900 &&
          sidebar.classList.contains("open") &&
          !sidebar.contains(e.target) &&
          !toggle.contains(e.target)) {
        sidebar.classList.remove("open");
      }
    });
  }

  /* ---------------- page-load fade-in ---------------- */
  var main = document.querySelector(".main");
  if (main) {
    main.classList.add("page-fade-in");
  }

  /* ---------------- page transition on internal nav clicks ---------------- */
  var overlay = document.createElement("div");
  overlay.className = "page-transition-overlay";
  document.body.appendChild(overlay);

  document.querySelectorAll('a[href^="/"], .sidebar a, .nav-item').forEach(function (link) {
    link.addEventListener("click", function (e) {
      var href = link.getAttribute("href");
      if (!href || href.startsWith("#") || link.target === "_blank" || e.metaKey || e.ctrlKey) return;
      e.preventDefault();
      overlay.classList.add("active");
      setTimeout(function () {
        window.location.href = href;
      }, 220);
    });
  });

  /* ---------------- hero heading: staggered word reveal ---------------- */
  var heroHeading = document.querySelector(".hero-copy h1");
  if (heroHeading && !heroHeading.dataset.split) {
    heroHeading.dataset.split = "true";
    var html = heroHeading.innerHTML;
    var wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    var words = [];
    wrapper.childNodes.forEach(function (node) {
      if (node.nodeType === Node.TEXT_NODE) {
        node.textContent.split(" ").forEach(function (w) {
          if (w.trim().length) words.push({ text: w, tag: null });
        });
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        words.push({ text: node.textContent, tag: node.tagName.toLowerCase(), className: node.className });
      }
    });
    heroHeading.innerHTML = "";
    words.forEach(function (w, i) {
      var span = document.createElement("span");
      span.className = "word-reveal";
      span.style.animationDelay = (i * 0.09) + "s";
      if (w.tag === "em") {
        var em = document.createElement("em");
        em.textContent = w.text;
        span.appendChild(em);
      } else {
        span.textContent = w.text;
      }
      heroHeading.appendChild(span);
      heroHeading.appendChild(document.createTextNode(" "));
    });
  }

  /* ---------------- scroll reveal with stagger ---------------- */
  try {
  var revealGroups = [
    ".card", ".testi-card", ".timeline-item", ".pillar",
    ".team-card", ".stat-card", ".stat"
  ];
  var revealTargets = document.querySelectorAll(revealGroups.join(","));

  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    var perParentIndex = new Map();
    revealTargets.forEach(function (el) {
      var parent = el.parentElement;
      var idx = perParentIndex.get(parent) || 0;
      el.style.transitionDelay = Math.min(idx * 0.08, 0.56) + "s";
      perParentIndex.set(parent, idx + 1);
      el.classList.add("reveal-base");
      io.observe(el);
    });
  } else {
    revealTargets.forEach(function (el) { el.classList.add("revealed"); });
  }
  } catch (err) {
    console.error("Scroll reveal failed, showing content directly:", err);
    document.querySelectorAll(".reveal-base").forEach(function (el) { el.classList.add("revealed"); });
  }

  /* ---------------- section heading reveal ---------------- */
  try {
  var headingTargets = document.querySelectorAll(".section-head, .page-section > h1, .page-section > .divider-ring");
  if ("IntersectionObserver" in window) {
    var ioHead = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          ioHead.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });
    headingTargets.forEach(function (el) {
      el.classList.add("reveal-base");
      ioHead.observe(el);
    });
  } else {
    headingTargets.forEach(function (el) { el.classList.add("revealed"); });
  }
  } catch (err) {
    console.error("Heading reveal failed, showing content directly:", err);
    document.querySelectorAll(".reveal-base").forEach(function (el) { el.classList.add("revealed"); });
  }

  /* ---------------- number count-up for stats ---------------- */
  function animateCount(el) {
    var raw = el.textContent.trim();
    var match = raw.match(/^([^\d]*)(\d+(?:\.\d+)?)(.*)$/);
    if (!match) return;
    var prefix = match[1], target = parseFloat(match[2]), suffix = match[3];
    var isFloat = match[2].indexOf(".") !== -1;
    var duration = 1100;
    var start = null;

    function step(ts) {
      if (!start) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var value = target * eased;
      el.textContent = prefix + (isFloat ? value.toFixed(1) : Math.round(value)) + suffix;
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = prefix + (isFloat ? target.toFixed(1) : target) + suffix;
    }
    requestAnimationFrame(step);
  }

  var countTargets = document.querySelectorAll(".stat .num, .stat-card .num");
  if ("IntersectionObserver" in window && countTargets.length) {
    var ioCount = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          animateCount(entry.target);
          ioCount.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    countTargets.forEach(function (el) { ioCount.observe(el); });
  }

  /* ---------------- card tilt + magnetic hover ---------------- */
  var tiltEls = document.querySelectorAll(".card, .team-card, .stat-card, .testi-card");
  tiltEls.forEach(function (el) {
    el.addEventListener("mousemove", function (e) {
      var rect = el.getBoundingClientRect();
      var x = (e.clientX - rect.left) / rect.width - 0.5;
      var y = (e.clientY - rect.top) / rect.height - 0.5;
      el.style.transform = "perspective(600px) rotateX(" + (-y * 5) + "deg) rotateY(" + (x * 5) + "deg) translateY(-3px)";
    });
    el.addEventListener("mouseleave", function () {
      el.style.transform = "";
    });
  });

  /* ---------------- button magnetic hover ---------------- */
  var magneticBtns = document.querySelectorAll(".btn-gold, .btn-ghost");
  magneticBtns.forEach(function (btn) {
    btn.addEventListener("mousemove", function (e) {
      var rect = btn.getBoundingClientRect();
      var x = (e.clientX - rect.left) / rect.width - 0.5;
      var y = (e.clientY - rect.top) / rect.height - 0.5;
      btn.style.transform = "translate(" + (x * 6) + "px, " + (y * 6 - 2) + "px)";
    });
    btn.addEventListener("mouseleave", function () {
      btn.style.transform = "";
    });
  });
});