TaxisMituAPI.requireRole("passenger");
TaxisMituAPI.wireLogout();

const STATUS_LABELS = {
  requested: "Buscando conductor…",
  accepted: "Conductor en camino",
  in_progress: "Viaje en curso",
  completed: "Viaje completado",
  cancelled: "Viaje cancelado",
};

const requestCard = document.getElementById("request-card");
const statusCard = document.getElementById("status-card");
const errorEl = document.getElementById("error");

let currentTrip = null;

function showRequestForm() {
  currentTrip = null;
  requestCard.style.display = "block";
  statusCard.style.display = "none";
}

function showTripStatus(trip) {
  currentTrip = trip;
  requestCard.style.display = "none";
  statusCard.style.display = "block";
  document.getElementById("trip-status").textContent = STATUS_LABELS[trip.status] || trip.status;

  const driverField = document.getElementById("trip-driver");
  if (trip.driver_name) {
    driverField.style.display = "block";
    document.getElementById("driver-name").textContent = trip.driver_name;
  } else {
    driverField.style.display = "none";
  }

  const cancelBtn = document.getElementById("cancel-trip");
  cancelBtn.style.display = trip.status === "in_progress" ? "none" : "inline-block";

  if (trip.status === "completed" || trip.status === "cancelled") {
    setTimeout(showRequestForm, 3000);
  }
}

async function loadActiveTrip() {
  try {
    const trip = await TaxisMituAPI.apiFetch("/api/trips/active");
    showTripStatus(trip);
  } catch (_) {
    showRequestForm();
  }
}

document.getElementById("use-location").addEventListener("click", () => {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition((pos) => {
    document.getElementById("pickup_address").dataset.lat = pos.coords.latitude;
    document.getElementById("pickup_address").dataset.lng = pos.coords.longitude;
    document.getElementById("pickup_address").placeholder =
      `Ubicación detectada (${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)})`;
  });
});

document.getElementById("request-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.style.display = "none";

  const pickupInput = document.getElementById("pickup_address");
  const payload = {
    pickup_address: pickupInput.value.trim(),
    pickup_lat: pickupInput.dataset.lat ? parseFloat(pickupInput.dataset.lat) : null,
    pickup_lng: pickupInput.dataset.lng ? parseFloat(pickupInput.dataset.lng) : null,
    dropoff_address: document.getElementById("dropoff_address").value.trim() || null,
  };

  try {
    const trip = await TaxisMituAPI.apiFetch("/api/trips", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showTripStatus(trip);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = "block";
  }
});

document.getElementById("cancel-trip").addEventListener("click", async () => {
  if (!currentTrip) return;
  try {
    const trip = await TaxisMituAPI.apiFetch(`/api/trips/${currentTrip.id}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "cancelled" }),
    });
    showTripStatus(trip);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = "block";
  }
});

connectTaxisMituWS((message) => {
  if (message.type === "trip_updated" && currentTrip && message.trip.id === currentTrip.id) {
    showTripStatus(message.trip);
  }
});

loadActiveTrip();
