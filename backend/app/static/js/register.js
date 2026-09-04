const roleSelect = document.getElementById("role");
const plateField = document.getElementById("plate-field");

function togglePlateField() {
  plateField.style.display = roleSelect.value === "driver" ? "block" : "none";
}
roleSelect.addEventListener("change", togglePlateField);
togglePlateField();

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("error");
  errorEl.style.display = "none";

  const phone = document.getElementById("phone").value.trim();

  const payload = {
    full_name: document.getElementById("full_name").value.trim(),
    cedula: document.getElementById("cedula").value.trim(),
    email: document.getElementById("email").value.trim(),
    phone,
    password: document.getElementById("password").value,
    role: roleSelect.value,
    vehicle_plate: roleSelect.value === "driver"
      ? document.getElementById("vehicle_plate").value.trim() || null
      : null,
    terms_accepted: document.getElementById("terms_accepted").checked,
  };

  try {
    await TaxisMituAPI.apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    window.location.href = `/verify?phone=${encodeURIComponent(phone)}`;
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = "block";
  }
});
