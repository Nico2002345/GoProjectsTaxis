const TaxisMituAPI = (() => {
  const TOKEN_KEY = "taxismitu_token";
  const USER_KEY = "taxismitu_user";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  function setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  async function apiFetch(path, options = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(path, { ...options, headers });
    if (res.status === 401) {
      clearSession();
      window.location.href = "/login";
      throw new Error("Not authenticated");
    }
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        if (Array.isArray(body.detail)) {
          // FastAPI's automatic 422 validation errors: a list of
          // {loc, msg, ...} objects rather than a plain string.
          detail = body.detail.map((e) => e.msg || JSON.stringify(e)).join(", ");
        } else if (body.detail) {
          detail = body.detail;
        }
      } catch (_) {}
      throw new Error(detail);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  function requireRole(role) {
    const user = getUser();
    if (!user || !getToken()) {
      window.location.href = "/login";
      return null;
    }
    if (user.role !== role) {
      window.location.href = user.role === "driver" ? "/driver" : "/passenger";
      return null;
    }
    return user;
  }

  function wireLogout() {
    const link = document.getElementById("logout-link");
    if (link) {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        clearSession();
        window.location.href = "/login";
      });
    }
  }

  return { getToken, getUser, setSession, clearSession, apiFetch, requireRole, wireLogout };
})();
