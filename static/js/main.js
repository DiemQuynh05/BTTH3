// Common UI initializations
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

// Helper lấy Cookie (CSRF Token)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Toast Notification System
function showToast(message, type = "success") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container-custom";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast-notification border-start border-4 border-${type === "success" ? "success" : type === "error" ? "danger" : "primary"}`;

  const icon = type === "success" ? "bi-check-circle-fill text-success" : type === "error" ? "bi-exclamation-triangle-fill text-danger" : "bi-info-circle-fill text-primary";

  toast.innerHTML = `
    <div class="d-flex align-items-center gap-2">
      <i class="bi ${icon} fs-5"></i>
      <span class="small fw-medium">${message}</span>
    </div>
    <button type="button" class="btn-close ms-2" style="font-size:0.75rem;" aria-label="Close"></button>
  `;

  toast.querySelector(".btn-close").addEventListener("click", () => {
    toast.remove();
  });

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Gắn global helper vào window
window.AppUtils = {
  getCookie,
  showToast,
  fetchJson: async (url, options = {}) => {
    const defaultHeaders = {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": getCookie("csrftoken") || "",
    };
    if (!(options.body instanceof FormData)) {
      defaultHeaders["Content-Type"] = "application/json";
    }
    options.headers = { ...defaultHeaders, ...(options.headers || {}) };
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || `Lỗi HTTP ${res.status}`);
    }
    return data;
  }
};
