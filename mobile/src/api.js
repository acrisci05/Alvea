// Client REST minimale verso il backend Alvea.
import { API_URL } from "./config";

export async function login(username, password) {
  // OAuth2PasswordRequestForm vuole x-www-form-urlencoded
  const body = new URLSearchParams({ username, password }).toString();
  const res = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Credenziali errate");
  return res.json(); // { access_token, token_type }
}

export async function register(username, password) {
  const res = await fetch(`${API_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Registrazione fallita");
  return res.json();
}

export async function getLatest(token, deviceId) {
  const res = await fetch(`${API_URL}/devices/${deviceId}/latest`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Nessuna lettura");
  return res.json();
}

export async function getAlerts(token, deviceId) {
  const res = await fetch(`${API_URL}/devices/${deviceId}/alerts?limit=20`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  return res.json();
}
