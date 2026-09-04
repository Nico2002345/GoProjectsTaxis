const user = TaxisMituAPI.requireRole("driver");
TaxisMituAPI.wireLogout();

const STATUS_LABELS = {
  requested: "Solicitado",
  accepted: "Aceptado",
  in_progress: "En curso",
  completed: "Completado",
  cancelled: "Cancelado",
};

const availabilityToggle = document.getElementById("availability-toggle");
const activeCard = document.getElementById("active-trip-card");
const requestsCard = document.getElementById("requests-card");
const requestsList = document.getElementById("requests-list");
const noRequests = document.getElementById("no-requests");

let activeTrip = null;
let availableTrips = [];

availabilityToggle.checked = !!user.is_available;

function renderRequests() {
  requestsList.innerHTML = "";
  if (availableTrips.length === 0) {
    noRequests.style.display = "block";
    return;
  }
  noRequests.style.display = "none";
  for (const trip of availableTrips) {
    const li = document.createElement("li");
    li.textContent = `${trip.passenger_name || "Pasajero"} — recogida: ${trip.pickup_address} `;
    const btn = document.createElement("button");
    btn.textContent = "Aceptar";
    btn.addEventListener("click", () => acceptTrip(trip.id));
    li.appendChild(btn);
    requestsList.appendChild(li);
  }
}

function renderActiveTrip() {
  if (!activeTrip) {
    activeCard.style.display = "none";
    requestsCard.style.display = "block";
    return;
  }
  activeCard.style.display = "block";
  requestsCard.style.display = "none";
  document.getElementById("active-passenger-name").textContent = activeTrip.passenger_name || "";
  document.getElementById("active-pickup").textContent = activeTrip.pickup_address;
  document.getElementById("active-status").textContent =
    STATUS_LABELS[activeTrip.status] || activeTrip.status;

  const startBtn = document.getElementById("start-trip");
  const completeBtn = document.getElementById("complete-trip");
  startBtn.style.display = activeTrip.status === "accepted" ? "inline-block" : "none";
  completeBtn.style.display = activeTrip.status === "in_progress" ? "inline-block" : "none";

  if (activeTrip.status === "completed" || activeTrip.status === "cancelled") {
    setTimeout(() => {
      activeTrip = null;
      renderActiveTrip();
      loadAvailableTrips();
    }, 3000);
  }
}

async function loadActiveTrip() {
  try {
    activeTrip = await TaxisMituAPI.apiFetch("/api/trips/active");
  } catch (_) {
    activeTrip = null;
  }
  renderActiveTrip();
  if (!activeTrip) await loadAvailableTrips();
}

async function loadAvailableTrips() {
  try {
    availableTrips = await TaxisMituAPI.apiFetch("/api/trips/available");
  } catch (_) {
    availableTrips = [];
  }
  renderRequests();
}

async function acceptTrip(tripId) {
  try {
    activeTrip = await TaxisMituAPI.apiFetch(`/api/trips/${tripId}/accept`, { method: "POST" });
    availableTrips = availableTrips.filter((t) => t.id !== tripId);
    renderActiveTrip();
  } catch (err) {
    alert(err.message);
    await loadAvailableTrips();
  }
}

availabilityToggle.addEventListener("change", async () => {
  try {
    const updated = await TaxisMituAPI.apiFetch("/api/drivers/me/availability", {
      method: "PATCH",
      body: JSON.stringify({ is_available: availabilityToggle.checked }),
    });
    user.is_available = updated.is_available;
    if (updated.is_available) await loadAvailableTrips();
  } catch (err) {
    alert(err.message);
    availabilityToggle.checked = !availabilityToggle.checked;
  }
});

document.getElementById("start-trip").addEventListener("click", async () => {
  if (!activeTrip) return;
  activeTrip = await TaxisMituAPI.apiFetch(`/api/trips/${activeTrip.id}/status`, {
    method: "POST",
    body: JSON.stringify({ status: "in_progress" }),
  });
  renderActiveTrip();
});

document.getElementById("complete-trip").addEventListener("click", async () => {
  if (!activeTrip) return;
  activeTrip = await TaxisMituAPI.apiFetch(`/api/trips/${activeTrip.id}/status`, {
    method: "POST",
    body: JSON.stringify({ status: "completed" }),
  });
  renderActiveTrip();
});

connectTaxisMituWS((message) => {
  if (message.type === "trip_requested" && !activeTrip) {
    availableTrips.push(message.trip);
    renderRequests();
  } else if (message.type === "trip_updated") {
    if (activeTrip && message.trip.id === activeTrip.id) {
      activeTrip = message.trip;
      renderActiveTrip();
    }
    availableTrips = availableTrips.filter((t) => t.id !== message.trip.id);
    renderRequests();
  }
});

loadActiveTrip();
