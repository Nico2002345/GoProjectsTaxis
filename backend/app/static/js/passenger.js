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
// payment-card only exists in the DOM when PAYMENTS_ENABLED is true server-side.
const paymentCard = document.getElementById("payment-card");
const payNowBtn = document.getElementById("pay-now");

let currentTrip = null;

function formatCop(cents) {
  return `$${Math.round(cents / 100).toLocaleString("es-CO")}`;
}

function showRequestForm() {
  currentTrip = null;
  requestCard.style.display = "block";
  statusCard.style.display = "none";
  if (paymentCard) paymentCard.style.display = "none";
}

function renderOffers(trip) {
  const section = document.getElementById("offers-section");
  const list = document.getElementById("offers-list");
  list.innerHTML = "";

  const offers = (trip.offers || []).filter((o) => o.status === "pending");
  if (trip.status !== "requested" || offers.length === 0) {
    section.style.display = "none";
    return;
  }
  section.style.display = "block";
  for (const offer of offers) {
    const li = document.createElement("li");
    li.textContent = `${offer.driver_name || "Conductor"} — ${formatCop(offer.fare_cents)} `;
    const btn = document.createElement("button");
    btn.textContent = "Elegir";
    btn.addEventListener("click", () => selectOffer(trip.id, offer.id));
    li.appendChild(btn);
    list.appendChild(li);
  }
}

function showTripStatus(trip) {
  currentTrip = trip;
  requestCard.style.display = "none";
  statusCard.style.display = "block";
  document.getElementById("trip-status").textContent = STATUS_LABELS[trip.status] || trip.status;
  document.getElementById("trip-offered-fare").textContent = formatCop(trip.offered_fare_cents);

  const driverField = document.getElementById("trip-driver");
  if (trip.driver_name) {
    driverField.style.display = "block";
    document.getElementById("driver-name").textContent = trip.driver_name;
    document.getElementById("trip-agreed-fare").textContent =
      trip.agreed_fare_cents != null ? formatCop(trip.agreed_fare_cents) : "";
  } else {
    driverField.style.display = "none";
  }

  renderOffers(trip);

  const cancelBtn = document.getElementById("cancel-trip");
  cancelBtn.style.display = trip.status === "in_progress" ? "none" : "inline-block";

  if (paymentCard) {
    if (trip.status === "completed" && trip.agreed_fare_cents != null) {
      paymentCard.style.display = "block";
      document.getElementById("payment-amount").textContent = formatCop(trip.agreed_fare_cents);
    } else {
      paymentCard.style.display = "none";
    }
  }

  if (trip.status === "completed" || trip.status === "cancelled") {
    setTimeout(showRequestForm, 3000);
  }
}

async function selectOffer(tripId, offerId) {
  try {
    const trip = await TaxisMituAPI.apiFetch(`/api/trips/${tripId}/offers/${offerId}/select`, {
      method: "POST",
    });
    showTripStatus(trip);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = "block";
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
  const fareInput = document.getElementById("offered_fare");
  const payload = {
    pickup_address: pickupInput.value.trim(),
    pickup_lat: pickupInput.dataset.lat ? parseFloat(pickupInput.dataset.lat) : null,
    pickup_lng: pickupInput.dataset.lng ? parseFloat(pickupInput.dataset.lng) : null,
    dropoff_address: document.getElementById("dropoff_address").value.trim() || null,
    offered_fare_cents: Math.round(parseFloat(fareInput.value) * 100),
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

if (payNowBtn) {
  payNowBtn.addEventListener("click", async () => {
    if (!currentTrip) return;
    try {
      const payment = await TaxisMituAPI.apiFetch("/api/payments/checkout", {
        method: "POST",
        body: JSON.stringify({ trip_id: currentTrip.id }),
      });
      window.location.href = payment.checkout_url;
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.style.display = "block";
    }
  });
}

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
  } else if (
    message.type === "trip_offer_created" &&
    currentTrip &&
    message.trip_id === currentTrip.id
  ) {
    currentTrip.offers = [...(currentTrip.offers || []), message.offer];
    renderOffers(currentTrip);
  } else if (
    message.type === "payment_updated" &&
    paymentCard &&
    currentTrip &&
    message.payment.trip_id === currentTrip.id
  ) {
    const statusLine = document.getElementById("payment-status-line");
    statusLine.style.display = "block";
    document.getElementById("payment-status").textContent = message.payment.status;
  }
});

loadActiveTrip();
