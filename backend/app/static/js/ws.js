function connectTaxisMituWS(onMessage) {
  const token = TaxisMituAPI.getToken();
  if (!token) return null;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws?token=${encodeURIComponent(token)}`);

  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch (_) {}
  };

  ws.onclose = () => {
    setTimeout(() => connectTaxisMituWS(onMessage), 3000);
  };

  return ws;
}
