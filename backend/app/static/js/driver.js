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
const offeredTripIds = new Set();

availabilityToggle.checked = !!user.is_available;

function formatCop(cents) {
  return `$${Math.round(cents / 100).toLocaleString("es-CO")}`;
}

function renderRequests() {
  requestsList.innerHTML = "";
  if (availableTrips.length === 0) {
    noRequests.style.display = "block";
    return;
  }
  noRequests.style.display = "none";
  for (const trip of availableTrips) {
    const li = document.createElement("li");
    const alreadyOffered = offeredTripIds.has(trip.id);
    li.textContent = `${trip.passenger_name || "Pasajero"} — recogida: ${trip.pickup_address} — ofrece ${formatCop(trip.offered_fare_cents)} `;

    if (alreadyOffered) {
      const span = document.createElement("span");
      span.textContent = "Ya enviaste una oferta — esperando al pasajero";
      li.appendChild(span);
    } else {
      const acceptBtn = document.createElement("button");
      acceptBtn.textContent = "Aceptar tarifa";
      acceptBtn.addEventListener("click", () => makeOffer(trip.id, null));
      li.appendChild(acceptBtn);

      const counterBtn = document.createElement("button");
      counterBtn.textContent = "Contraofertar";
      counterBtn.addEventListener("click", () => {
        const value = prompt("¿Cuánto quieres cobrar por este viaje? (COP)");
        if (!value) return;
        const cents = Math.round(parseFloat(value) * 100);
        if (!cents || cents <= 0) return;
        makeOffer(trip.id, cents);
      });
      li.appendChild(counterBtn);
    }
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
  document.getElementById("active-fare").textContent =
    activeTrip.agreed_fare_cents != null ? formatCop(activeTrip.agreed_fare_cents) : "";

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

async function makeOffer(tripId, fareCents) {
  try {
    await TaxisMituAPI.apiFetch(`/api/trips/${tripId}/offers`, {
      method: "POST",
      body: JSON.stringify({ fare_cents: fareCents }),
    });
    offeredTripIds.add(tripId);
    renderRequests();
  } catch (err) {
    alert(err.message);
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
    } else if (!activeTrip && message.trip.driver_id === user.id) {
      // A passenger picked our offer on this trip — adopt it as the active trip.
      activeTrip = message.trip;
      offeredTripIds.delete(message.trip.id);
      availableTrips = availableTrips.filter((t) => t.id !== message.trip.id);
      renderActiveTrip();
    } else {
      availableTrips = availableTrips.filter((t) => t.id !== message.trip.id);
      renderRequests();
    }
  } else if (message.type === "trip_offer_rejected" || message.type === "trip_closed") {
    offeredTripIds.delete(message.trip_id);
    availableTrips = availableTrips.filter((t) => t.id !== message.trip_id);
    renderRequests();
  }
});

loadActiveTrip();
