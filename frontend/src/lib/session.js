const TOKEN_KEY = "token";
const NAME_KEY = "userName";
const EMAIL_KEY = "userEmail";

export function hasToken() {
  return Boolean(localStorage.getItem(TOKEN_KEY));
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function getUserName() {
  return localStorage.getItem(NAME_KEY) || "";
}

export function getUserEmail() {
  return localStorage.getItem(EMAIL_KEY) || "";
}

export function saveSession({ token, name, email }) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(NAME_KEY, name);
  localStorage.setItem(EMAIL_KEY, email);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(NAME_KEY);
  localStorage.removeItem(EMAIL_KEY);
}
