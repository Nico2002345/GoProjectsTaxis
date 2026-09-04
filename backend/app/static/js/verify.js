const phoneInput = document.getElementById("phone");
const errorEl = document.getElementById("error");
const infoEl = document.getElementById("info");

const params = new URLSearchParams(window.location.search);
const prefillPhone = params.get("phone");
if (prefillPhone) phoneInput.value = prefillPhone;

function hideMessages() {
  errorEl.style.display = "none";
  infoEl.style.display = "none";
}

document.getElementById("verify-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideMessages();

  const payload = {
    phone: phoneInput.value.trim(),
    pin: document.getElementById("pin").value.trim(),
  };

  try {
    const data = await TaxisMituAPI.apiFetch("/api/auth/verify-email", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    TaxisMituAPI.setSession(data.access_token, data.user);
    window.location.href = data.user.role === "driver" ? "/driver" : "/passenger";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = "block";
  }
});

document.getElementById("resend-btn").addEventListener("click", async () => {
  hideMessages();
  const phone = phoneInput.value.trim();
  if (!phone) {
    errorEl.textContent = "Ingresa tu teléfono para reenviar el código.";
    errorEl.style.display = "block";
    return;
  }
  try {
    await TaxisMituAPI.apiFetch("/api/auth/resend-pin", {
      method: "POST",
      body: JSON.stringify({ phone }),
    });
    infoEl.textContent = "Código reenviado. Revisa tu correo.";
    infoEl.style.display = "block";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = "block";
  }
});
