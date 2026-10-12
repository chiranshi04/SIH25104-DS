/* ==========================================================
   app.js — Phase 8: Authentication and conversation management
   ========================================================== */

const chatArea = document.getElementById("chat-area");
const emptyState = document.getElementById("empty-state");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const clearBtn = document.getElementById("clear-btn");
const errorBanner = document.getElementById("error-banner");
const errorText = document.getElementById("error-text");
const retryBtn = document.getElementById("retry-btn");
const errorDismiss = document.getElementById("error-dismiss");
const authStatus = document.getElementById("auth-status");
const conversationsSidebar = document.getElementById("conversations-sidebar");
const conversationList = document.getElementById("conversation-list");
const publicNoticesList = document.getElementById("public-notices-list");
const botTemplate = document.getElementById("bot-message-template");
const userTemplate = document.getElementById("user-message-template");
const loadingTemplate = document.getElementById("loading-template");

const API_BASE_URL = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
const CONVERSATION_STORAGE_KEY = "sih25104_conversation_id";
const TOKEN_STORAGE_KEY = "sih25104_access_token";
const USER_STORAGE_KEY = "sih25104_user";

let conversationId = getStoredConversationId();
let currentUser = getStoredUser();
let lastFailedText = "";

function createConversationId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const random = Math.random() * 16 | 0;
    const value = char === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

function getStoredConversationId() {
  const storedId = window.localStorage.getItem(CONVERSATION_STORAGE_KEY);
  if (storedId) return storedId;
  const newId = createConversationId();
  window.localStorage.setItem(CONVERSATION_STORAGE_KEY, newId);
  return newId;
}

function saveConversationId(newId) {
  conversationId = newId;
  window.localStorage.setItem(CONVERSATION_STORAGE_KEY, newId);
}

function getToken() {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

function getStoredUser() {
  try {
    return JSON.parse(window.localStorage.getItem(USER_STORAGE_KEY) || "null");
  } catch (error) {
    return null;
  }
}

function clearAuth() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(USER_STORAGE_KEY);
  currentUser = null;
  updateAuthUI();
}

function showSessionExpired() {
  clearAuth();
  showError("Session expired, please log in again");
}

function authHeaders() {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function updateAuthUI() {
  authStatus.textContent = "";
  if (currentUser && getToken()) {
    if (["staff", "admin"].includes(currentUser.role)) {
      const adminLink = document.createElement("a");
      adminLink.href = "admin.html";
      adminLink.textContent = "Admin";
      authStatus.appendChild(adminLink);
    }
    const logoutButton = document.createElement("button");
    logoutButton.type = "button";
    logoutButton.textContent = `Hi ${currentUser.name} · Logout`;
    logoutButton.addEventListener("click", () => {
      clearAuth();
      window.location.reload();
    });
    authStatus.appendChild(logoutButton);
    conversationsSidebar.classList.remove("hidden");
    loadConversationList();
  } else {
    const loginLink = document.createElement("a");
    loginLink.href = "login.html";
    loginLink.textContent = "Login";
    authStatus.appendChild(loginLink);
    conversationsSidebar.classList.add("hidden");
  }
}

/* ----------------------------------------------------------
   Rendering helpers
   ---------------------------------------------------------- */
function updateEmptyState() {
  const hasMessages = chatArea.querySelector(".message") !== null;
  emptyState.style.display = hasMessages ? "none" : "block";
}

function addUserMessage(text) {
  const node = userTemplate.content.cloneNode(true);
  node.querySelector(".answer-text").textContent = text;
  chatArea.appendChild(node);
  scrollToBottom();
  updateEmptyState();
}

function readableLanguage(value) {
  if (typeof value !== "string" || value.length === 0) return "";
  const labels = {
    english: "English",
    german: "German (Deutsch)",
    hindi: "Hindi (हिंदी)",
    hinglish: "Hinglish",
    spanish: "Spanish (Español)",
    french: "French (Français)",
    greek: "Greek (Ελληνικά)",
    italian: "Italian (Italiano)",
  };
  return labels[value.toLowerCase()] || `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function formatSource(source) {
  const parts = [];
  if (source && source.document !== undefined && source.document !== null) {
    parts.push(String(source.document));
  }
  if (source && source.page !== undefined && source.page !== null) {
    parts.push(`Page ${source.page}`);
  }
  if (source && source.section !== undefined && source.section !== null && source.section !== "") {
    parts.push(String(source.section));
  }
  return parts.join(" — ");
}

async function submitFeedback(messageElement, button, value) {
  const buttons = messageElement.querySelectorAll(".feedback-btn");
  const status = messageElement.querySelector(".feedback-status");
  const error = messageElement.querySelector(".feedback-error");
  buttons.forEach((item) => { item.disabled = true; });
  status.textContent = "";
  error.textContent = "";
  try {
    await apiFetch(`${API_BASE_URL}/feedback`, {
      method: "POST",
      body: JSON.stringify({
        response_id: Number(messageElement.dataset.responseId),
        feedback: value === "up" ? "positive" : "negative",
      }),
    });
    buttons.forEach((item) => item.classList.remove("selected"));
    button.classList.add("selected");
    status.textContent = "Thanks for your feedback";
  } catch (requestError) {
    buttons.forEach((item) => item.classList.remove("selected"));
    if (requestError.message !== "SESSION_EXPIRED") {
      error.textContent = "Could not save feedback. Please try again.";
    }
  } finally {
    buttons.forEach((item) => { item.disabled = false; });
  }
}

function addBotMessage(data) {
  const node = botTemplate.content.cloneNode(true);
  const messageElement = node.querySelector(".bot-message");
  if (data.response_id !== undefined && data.response_id !== null) {
    messageElement.dataset.responseId = data.response_id;
  }
  node.querySelector(".answer-text").textContent = data.answer;
  const languageLabel = readableLanguage(data.language);
  const languageTag = node.querySelector(".language-tag");
  if (languageLabel) {
    languageTag.textContent = `Language: ${languageLabel}`;
  } else {
    languageTag.classList.add("hidden");
  }

  const confidenceTag = node.querySelector(".confidence-tag");
  const confidenceNote = node.querySelector(".confidence-note");
  const confidence = data.confidence;
  if (typeof confidence === "number" && Number.isFinite(confidence)) {
    confidenceTag.textContent = `Confidence: ${Math.round(confidence * 100)}%`;
    if (confidence >= 0.75) confidenceTag.classList.add("confidence-normal");
    else if (confidence >= 0.5) confidenceTag.classList.add("confidence-caution");
    else {
      confidenceTag.classList.add("confidence-low");
      confidenceNote.textContent =
        "This answer may not be reliable. Please verify with the college office.";
      confidenceNote.classList.remove("hidden");
    }
  } else {
    confidenceTag.classList.add("hidden");
  }

  const sourcesBox = node.querySelector(".sources-box");
  const sourcesList = node.querySelector(".sources-list");
  if (Array.isArray(data.sources) && data.sources.length > 0) {
    data.sources.forEach((source) => {
      const li = document.createElement("li");
      li.textContent = formatSource(source);
      sourcesList.appendChild(li);
    });
  } else {
    const emptySources = document.createElement("p");
    emptySources.className = "sources-empty";
    emptySources.textContent = "No source found for this answer";
    sourcesBox.appendChild(emptySources);
  }

  const feedbackValue = data.feedback;
  node.querySelectorAll(".feedback-btn").forEach((button) => {
    if ((feedbackValue === "positive" && button.dataset.value === "up")
      || (feedbackValue === "negative" && button.dataset.value === "down")) {
      button.classList.add("selected");
    }
    button.addEventListener("click", () => {
      if (messageElement.dataset.responseId) {
        submitFeedback(messageElement, button, button.dataset.value);
      }
    });
  });
  chatArea.appendChild(node);
  scrollToBottom();
  updateEmptyState();
}

function clearRenderedMessages() {
  chatArea.querySelectorAll(".message").forEach((element) => element.remove());
  updateEmptyState();
}

function renderConversation(messages) {
  clearRenderedMessages();
  messages.forEach((item) => {
    if (item.sender === "user") addUserMessage(item.message);
    if (item.sender === "assistant") {
      addBotMessage({
        answer: item.message,
        language: item.language,
        confidence: item.confidence,
        sources: item.sources,
        response_id: item.response_id,
        feedback: item.feedback,
      });
    }
  });
}

function showLoading() {
  const node = loadingTemplate.content.cloneNode(true);
  chatArea.appendChild(node);
  scrollToBottom();
  return chatArea.querySelector(".loading-message:last-of-type");
}

function removeLoading(element) {
  if (element) element.remove();
}

function showError(message, canRetry = false) {
  errorText.textContent = message;
  errorBanner.classList.remove("hidden");
  retryBtn.classList.toggle("hidden", !canRetry);
}

function hideError() {
  errorBanner.classList.add("hidden");
  retryBtn.classList.add("hidden");
}

function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

/* ----------------------------------------------------------
   Authenticated API calls
   ---------------------------------------------------------- */
async function getBotReply(message, currentConversationId) {
  return apiFetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    body: JSON.stringify({
      conversation_id: currentConversationId,
      message,
    }),
  });
}

async function restoreConversation() {
  try {
    const data = await apiFetch(
      `${API_BASE_URL}/conversations/${encodeURIComponent(conversationId)}`
    );
    renderConversation(data.messages);
  } catch (error) {
    if (error.status !== 404) showError(error.message || "Could not restore this conversation.");
  }
}

async function loadConversationList() {
  try {
    const data = await apiFetch(`${API_BASE_URL}/conversations`);
    conversationList.textContent = "";
    data.conversations.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "conversation-item";
      const preview = document.createElement("span");
      preview.className = "conversation-preview";
      preview.textContent = item.preview || "(empty conversation)";
      const date = document.createElement("span");
      date.className = "conversation-date";
      date.textContent = new Date(item.updated_at).toLocaleString();
      button.append(preview, date);
      button.addEventListener("click", () => {
        saveConversationId(item.id);
        restoreConversation();
      });
      conversationList.appendChild(button);
    });
  } catch (error) { showError(error.message || "Could not load your conversations."); }
}

async function loadPublicNotices() {
  try {
    const notices = await apiFetch(`${API_BASE_URL}/notices`);
    publicNoticesList.textContent = "";
    notices.forEach((notice) => {
      const article = document.createElement("article");
      article.className = "public-notice";
      const title = document.createElement("h3");
      title.textContent = notice.title;
      const content = document.createElement("p");
      content.textContent = notice.content;
      article.append(title, content);
      publicNoticesList.appendChild(article);
    });
    if (notices.length === 0) {
      const empty = document.createElement("p");
      empty.textContent = "No active notices.";
      publicNoticesList.appendChild(empty);
    }
  } catch (error) {
    showError("Could not load notices.");
  }
}

/* ----------------------------------------------------------
   Main send handler and controls
   ---------------------------------------------------------- */
async function handleSend(textOverride = null, isRetry = false) {
  const text = textOverride === null ? messageInput.value.trim() : textOverride;
  if (!text) return;
  hideError();
  if (!isRetry) addUserMessage(text);
  if (!isRetry) messageInput.value = "";
  autoResizeInput();
  sendBtn.disabled = true;
  const loadingElement = showLoading();
  try {
    const data = await getBotReply(text, conversationId);
    removeLoading(loadingElement);
    saveConversationId(data.conversation_id);
    addBotMessage(data);
    lastFailedText = "";
    if (currentUser) loadConversationList();
  } catch (error) {
    removeLoading(loadingElement);
    lastFailedText = text;
    showError(error.message || "Request failed. Please try again.", true);
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

clearBtn.addEventListener("click", () => {
  saveConversationId(createConversationId());
  clearRenderedMessages();
  hideError();
});
errorDismiss.addEventListener("click", hideError);
retryBtn.addEventListener("click", () => {
  if (lastFailedText) handleSend(lastFailedText, true);
});
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    handleSend();
  }
});
messageInput.addEventListener("input", autoResizeInput);
function autoResizeInput() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${messageInput.scrollHeight}px`;
}
sendBtn.addEventListener("click", handleSend);

updateAuthUI();
updateEmptyState();
restoreConversation();
loadPublicNotices();
