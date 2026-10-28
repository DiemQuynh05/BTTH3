document.querySelectorAll("input, textarea, select").forEach((el) => {
  if (!el.classList.contains("form-control") && !el.classList.contains("form-select")) {
    el.classList.add(el.tagName === "SELECT" ? "form-select" : "form-control");
  }
});
document.querySelectorAll("[data-clear-form]").forEach((button) => {
  button.addEventListener("click", () => {
    const form = button.closest("form");
    form?.querySelectorAll("input, select").forEach((field) => { field.value = ""; });
    form?.submit();
  });
});
