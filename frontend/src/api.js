import { getToken } from "./lib/session";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function apiUrl(path) {
  if (!API_BASE_URL) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}

async function parseResponse(response) {
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const message = data?.detail || data?.message || "Request failed";
    throw new Error(message);
  }

  return data;
}

function authHeader() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function signupUser({ name, email, password }) {
  const form = new FormData();
  form.append("name", name);
  form.append("email", email);
  form.append("password", password);

  const response = await fetch(apiUrl("/api/auth/signup"), {
    method: "POST",
    body: form,
  });

  const data = await parseResponse(response);
  if (!data.success) {
    throw new Error(data.message || "Signup failed");
  }
  return data;
}

export async function loginUser({ email, password }) {
  const form = new FormData();
  form.append("email", email);
  form.append("password", password);

  const response = await fetch(apiUrl("/api/auth/login"), {
    method: "POST",
    body: form,
  });

  const data = await parseResponse(response);
  if (!data.success) {
    throw new Error(data.message || "Login failed");
  }
  return data;
}

export async function logoutUser() {
  const form = new FormData();
  form.append("token", getToken());

  await fetch(apiUrl("/api/auth/logout"), {
    method: "POST",
    body: form,
  });
}

export async function detectAccident(file) {
  const form = new FormData();
  form.append("video", file);

  const response = await fetch(apiUrl("/api/detect"), {
    method: "POST",
    headers: {
      ...authHeader(),
    },
    body: form,
  });

  return parseResponse(response);
}

export async function fetchHistory() {
  const response = await fetch(apiUrl("/api/history"), {
    headers: {
      ...authHeader(),
    },
  });

  return parseResponse(response);
}

export async function chatWithAssistant(message, history) {
  const response = await fetch(apiUrl("/api/chat/"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, history }),
  });

  return parseResponse(response);
}