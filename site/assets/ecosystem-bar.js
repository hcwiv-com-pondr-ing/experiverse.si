/* ExperiVerse ecosystem bar: Esc closes an open menu (and the mark's card), a click outside closes it, and only one
   menu is open at a time. The bar works without this file. Henry C. Weismann IV, weismannweb.com. */
(function () {
  "use strict";
  var bar = document.querySelector("[data-eco-bar]");
  if (!bar) return;
  var menus = Array.prototype.slice.call(bar.querySelectorAll("details"));
  var brand = bar.querySelector(".eco-brand");
  function closeAll(except) { menus.forEach(function (d) { if (d !== except) d.open = false; }); }
  menus.forEach(function (d) {
    d.addEventListener("toggle", function () { if (d.open) closeAll(d); });
    d.addEventListener("focusout", function (e) { if (e.relatedTarget && !d.contains(e.relatedTarget)) d.open = false; });
  });
  document.addEventListener("click", function (e) { if (!bar.contains(e.target)) closeAll(); });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" && e.key !== "Esc") return;
    var open = menus.filter(function (d) { return d.open; })[0];
    if (open) { open.open = false; open.querySelector("summary").focus(); }
    if (brand && (brand.matches(":hover") || brand.contains(document.activeElement))) brand.classList.add("eco-off");
  });
  if (brand) {
    brand.addEventListener("mouseleave", function () { brand.classList.remove("eco-off"); });
    brand.addEventListener("focusout", function (e) { if (!brand.contains(e.relatedTarget)) brand.classList.remove("eco-off"); });
  }
})();
