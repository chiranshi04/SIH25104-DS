const API_BASE_URL = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
const TOKEN_STORAGE_KEY = "sih25104_access_token";
const USER_STORAGE_KEY = "sih25104_user";
const messageBox = document.getElementById("auth-message");

const redirectMessage = window.sessionStorage.getItem("admin_message");
if (redirectMessage) {
  showMessage(redirectMessage);
  window.sessionStorage.removeItem("admin_message");
}

function showMessage(message) {
  messageBox.textContent = message;
  messageBox.classList.remove("hidden");
}

async function readError(response) {
  try {
    const data = await response.json();
    return data.detail || "Request failed";
  } catch (error) {
    return "Request failed";
  }
}

function saveLogin(data) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
  window.location.href = "index.html";
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    if (!response.ok) {
      showMessage(await readError(response));
      return;
    }
    saveLogin(await response.json());
  } catch (error) {
    showMessage("Could not connect to the server.");
  }
});

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: form.get("name"),
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    if (!response.ok) {
      showMessage(await readError(response));
      return;
    }
    showMessage("Account created. You can now log in.");
    event.currentTarget.reset();
  } catch (error) {
    showMessage("Could not connect to the server.");
  }
});
