document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("error");
  errorEl.style.display = "none";

  const phone = document.getElementById("phone").value.trim();
  const password = document.getElementById("password").value;

  try {
    const data = await TaxisMituAPI.apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ phone, password }),
    });
    TaxisMituAPI.setSession(data.access_token, data.user);
    window.location.href = data.user.role === "driver" ? "/driver" : "/passenger";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = "block";
  }
});
