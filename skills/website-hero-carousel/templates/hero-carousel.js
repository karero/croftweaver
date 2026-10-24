/* The hero carousel (the website-hero-carousel skill), installed as public/js/hero-carousel.js,
   a file of the site's own so that a strict Content-Security-Policy (script-src 'self') lets it
   run. Photos take turns, every data-interval milliseconds (default 6000). The swap is instant
   or, with data-swap="fade", a one-second cross-fade done in CSS; the script only says which
   slide is on show (data-active) and which dot (aria-current). Nothing is stored or sent.
   Without this script the page shows every slide one under the other (see HeroCarousel.astro).

   When it moves, after the WAI-ARIA Authoring Practices carousel pattern:
     - it stops when keyboard focus enters the carousel from outside, and stays stopped until
       the visitor presses Resume (pause "button") or reloads (pause "dots");
     - it waits while a mouse pointer is over it and while the tab is hidden, and starts afresh
       (a full interval) when the pointer leaves or the tab returns;
     - it starts stopped when the device asks for reduced motion.
   A slide is shown only when its image is complete: a late or failed image never leaves a
   blank slide, and the rotation passes over a slide whose image has failed. The one exception is the first slide at the start: it is shown while its image is
   still arriving (it is the first thing the visitor sees); if that image fails, the first other slide
   whose image is there takes its place, now or when it arrives, and the rotation goes on from there
   unless it is stopped. Choosing a dot shows that photo (when its image has arrived) and, with pause
   "dots", stops the rotation for good; with pause "button" it restarts the interval and never
   clears a pause. */
(function () {
  var root = document.querySelector('[data-hero-carousel]');
  if (!root) return;
  var slides = Array.prototype.slice.call(root.querySelectorAll('[data-hc-slide]'));
  var controls = root.querySelector('.hc-controls');
  var toggle = root.querySelector('[data-hc-toggle]');
  var picks = Array.prototype.slice.call(root.querySelectorAll('[data-hc-pick]'));
  var wrap = root.querySelector('.hc-slides');
  if (slides.length < 2 || !controls || !wrap) return;

  var INTERVAL = Number(root.getAttribute('data-interval')) || 6000;
  var dotsMode = root.getAttribute('data-pause') === 'dots';
  var current = 0;
  var paused = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var hovering = false;
  var away = document.hidden === true;
  var timer = null;
  var wanted = -1; // the slide a visitor picked that is still on its way
  var gen = 0; // changes whenever the timer is reset; the automatic swap to a late image acts only if nothing was reset since

  function image(i) { return slides[i].querySelector('img'); }
  function loaded(i) { var el = image(i); return !!el && el.complete && el.naturalWidth > 0; }
  function running() { return !paused && !hovering && !away; }
  function failed(i) { var el = image(i); return !!el && el.complete && el.naturalWidth === 0; }
  // the slide after i whose image has not failed (i itself when every other one has)
  function after(i) {
    for (var j = 1; j < slides.length; j++) { var n = (i + j) % slides.length; if (!failed(n)) return n; }
    return i;
  }

  function show(i) {
    current = i;
    wanted = -1;
    slides.forEach(function (slide, k) {
      if (k === i) slide.setAttribute('data-active', '');
      else slide.removeAttribute('data-active');
      // inert and hidden from screen readers at once: a slide that is still fading out can be neither tabbed to nor read out
      slide.inert = k !== i;
      if (k === i) slide.removeAttribute('aria-hidden');
      else slide.setAttribute('aria-hidden', 'true');
    });
    picks.forEach(function (button, k) {
      if (k === i) button.setAttribute('aria-current', 'true');
      else button.removeAttribute('aria-current');
    });
  }
  function label() {
    if (toggle) toggle.textContent = paused ? toggle.getAttribute('data-resume-text') : toggle.getAttribute('data-pause-text');
    wrap.setAttribute('aria-live', paused ? 'polite' : 'off');
  }
  function stop() {
    gen++;
    if (timer !== null) { clearTimeout(timer); timer = null; }
  }
  function schedule() {
    stop();
    if (running()) timer = setTimeout(tick, INTERVAL);
  }
  // A slide that is not ready yet. The automatic swap waits for the image only while nothing has
  // reset the timer since; a visitor's own pick (`wanted`) waits for its image whatever happens
  // meanwhile, until something else is shown. A failed image (complete, no width) is not waited
  // for: the click shows nothing (and, with pause "dots", has stopped the rotation) and the
  // automatic swap tries again at its next tick.
  function whenLoaded(idx, chosen) {
    var el = image(idx);
    if (!el || el.complete) return;
    var g = gen;
    if (chosen) wanted = idx;
    el.addEventListener('load', function () {
      if (chosen) {
        if (wanted === idx) { show(idx); schedule(); }
      } else if (g === gen && running() && after(current) === idx) {
        show(idx); schedule();
      }
    }, { once: true });
  }
  function tick() {
    timer = null;
    var next = after(current);
    if (loaded(next)) show(next);
    schedule();
    if (!loaded(next)) whenLoaded(next, false);
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      paused = !paused;
      // Resume is a request to rotate, also with the pointer still on the button; the hold for
      // the pointer applies again once it has left and come back.
      if (!paused) hovering = false;
      label();
      schedule();
    });
  }
  picks.forEach(function (button, k) {
    button.addEventListener('click', function () {
      if (dotsMode) { paused = true; label(); stop(); }
      if (loaded(k)) show(k);
      if (!dotsMode) schedule();
      if (!loaded(k)) whenLoaded(k, true);
    });
  });
  // Keyboard focus entering from outside stops it; moving between its own controls does not
  // matter, nor does a mouse click (not keyboard focus).
  root.addEventListener('focusin', function (event) {
    if (root.contains(event.relatedTarget)) return;
    if (!event.target.matches || !event.target.matches(':focus-visible')) return;
    if (!paused) { paused = true; label(); stop(); }
  });
  root.addEventListener('pointerenter', function (event) {
    if (event.pointerType !== 'mouse') return;
    hovering = true;
    stop();
  });
  root.addEventListener('pointerleave', function (event) {
    if (event.pointerType !== 'mouse') return;
    hovering = false;
    schedule();
  });
  document.addEventListener('visibilitychange', function () {
    away = document.hidden === true;
    schedule();
  });

  // The slide on show has failed (its image is complete and has no width): show the first other slide whose
  // image is there, now, or, if none is yet, as soon as one arrives. Never swaps away from a photo that is fine.
  function recover() {
    if (!failed(current)) return;
    for (var j = 1; j < slides.length; j++) {
      var n = (current + j) % slides.length;
      // the timer is left as it is: a running rotation goes on, a stopped one (reduced motion, a dot, focus) stays stopped
      if (loaded(n)) { show(n); return; }
    }
    slides.forEach(function (slide, k) {
      var img = image(k);
      if (k !== current && img) img.addEventListener('load', recover, { once: true });
    });
  }
  show(0);
  slides.forEach(function (slide, k) {
    var img = image(k);
    if (img) img.addEventListener('error', function () { if (current === k) recover(); });
  });
  recover(); // the first image may have failed before this script ran
  label();
  controls.hidden = false;
  root.setAttribute('data-ready', '');
  // Transitions (the fade) apply only from here on: read the style once so that the slides that
  // are not on show leave the page without fading out over the first one.
  void root.offsetWidth;
  root.setAttribute('data-live', '');
  schedule();
})();
