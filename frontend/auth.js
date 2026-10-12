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

function saveLogin(data) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
  window.location.href = "index.html";
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const data = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
    });
    saveLogin(data);
  } catch (error) {
    showMessage(error.message || "Login failed. Please try again.");
  }
});

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    showMessage("Account created. You can now log in.");
    event.currentTarget.reset();
  } catch (error) {
    showMessage(error.message || "Registration failed. Please try again.");
  }
});
