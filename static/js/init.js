/* boot wiring: global keydown, initial route. Loads LAST. */
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if ($("#cluster-drawer").classList.contains("open")) closeClusterDrawer();
  else if ($("#hist-drawer").classList.contains("open")) closeHistory();
});

routeFromHash();
updateAppBadge();
