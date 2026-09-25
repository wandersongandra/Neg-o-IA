const reload = () => window.location.reload();

document.getElementById("retry-button")?.addEventListener("click", reload);
window.addEventListener("online", reload);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.addEventListener("controllerchange", reload);
}
