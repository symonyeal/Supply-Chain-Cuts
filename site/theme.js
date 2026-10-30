/* Shared system-preference, saved preference and theme-button behavior. */
"use strict";
(() => {
  const button = document.getElementById("theme"), root = document.documentElement;
  const mode = matchMedia("(prefers-color-scheme: dark)");
  let stored;
  try { stored = localStorage.getItem("supply-theme"); } catch { /* Theme still works for this page. */ }
  if (["light", "dark"].includes(stored)) root.dataset.theme = stored;
  const dark = () => root.dataset.theme ? root.dataset.theme === "dark" : mode.matches;
  const label = () => {
    button.textContent = dark() ? "Light view" : "Dark view";
    button.setAttribute("aria-label", `Switch to ${dark() ? "light" : "dark"} theme`);
  };
  button.onclick = () => {
    root.dataset.theme = dark() ? "light" : "dark";
    try { localStorage.setItem("supply-theme", root.dataset.theme); } catch { /* Theme still works for this page. */ }
    label();
  };
  mode.addEventListener("change", label);
  label();
})();
