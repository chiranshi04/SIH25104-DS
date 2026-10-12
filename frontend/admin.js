const API_BASE_URL = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
const TOKEN_KEY = "sih25104_access_token";
const USER_KEY = "sih25104_user";
const token = localStorage.getItem(TOKEN_KEY);
let user;
try { user = JSON.parse(localStorage.getItem(USER_KEY) || "null"); } catch (error) { user = null; }
const errorBox = document.getElementById("admin-error");
const isManager = user && ["staff", "admin"].includes(user.role);
if (!token || !isManager) {
  sessionStorage.setItem("admin_message", "Admin or staff access is required.");
  window.location.href = "login.html";
}

document.getElementById("admin-user-label").textContent = user ? `Signed in as ${user.name} (${user.role})` : "";
function showError(message) { errorBox.textContent = message; errorBox.classList.remove("hidden"); }
function clearError() { errorBox.classList.add("hidden"); }
function headers() { return { "Content-Type": "application/json", Authorization: `Bearer ${token}` }; }
async function api(path, options = {}) { return apiFetch(path, options); }
function cell(text) { const node = document.createElement("td"); node.textContent = text ?? ""; return node; }
function button(text, handler) { const node = document.createElement("button"); node.type = "button"; node.textContent = text; node.addEventListener("click", handler); return node; }

async function loadStats() {
  const data = await api("/admin/stats");
  const panel = document.getElementById("tab-overview"); panel.textContent = "";
  const grid = document.createElement("div"); grid.className = "stats-grid";
  Object.entries(data).forEach(([key, value]) => { const card = document.createElement("div"); card.className = "stat-card"; const label = document.createElement("strong"); label.textContent = key.replaceAll("_", " "); const number = document.createElement("span"); number.textContent = value; card.append(label, number); grid.appendChild(card); });
  panel.appendChild(grid);
}

function resetNoticeForm() { document.getElementById("notice-form").reset(); document.getElementById("notice-id").value = ""; document.getElementById("notice-active").checked = true; document.getElementById("notice-cancel").classList.add("hidden"); }
async function loadNotices() {
  const data = await api("/admin/notices"); const host = document.getElementById("notices-table"); host.textContent = "";
  data.forEach((notice) => { const article = document.createElement("article"); article.className = "admin-notice"; const title = document.createElement("h3"); title.textContent = `${notice.title} (${notice.is_active ? "active" : "inactive"})`; const content = document.createElement("p"); content.textContent = notice.content; const actions = document.createElement("div"); actions.append(button("Edit", () => { document.getElementById("notice-id").value = notice.id; document.getElementById("notice-title").value = notice.title; document.getElementById("notice-content").value = notice.content; document.getElementById("notice-active").checked = notice.is_active; document.getElementById("notice-cancel").classList.remove("hidden"); }), button("Delete", async () => { if (!confirm("Delete this notice?")) return; try { await api(`/notices/${notice.id}`, { method: "DELETE" }); await loadNotices(); await loadStats(); } catch (error) { showError(error.message); } })); article.append(title, content, actions); host.appendChild(article); });
}
document.getElementById("notice-form").addEventListener("submit", async (event) => { event.preventDefault(); clearError(); const id = document.getElementById("notice-id").value; const body = { title: document.getElementById("notice-title").value, content: document.getElementById("notice-content").value, is_active: document.getElementById("notice-active").checked }; try { await api(id ? `/notices/${id}` : "/notices", { method: id ? "PUT" : "POST", body: JSON.stringify(body) }); resetNoticeForm(); await loadNotices(); await loadStats(); } catch (error) { showError(error.message); } });
document.getElementById("notice-cancel").addEventListener("click", resetNoticeForm);

async function loadFeedback(page = 1) { const filter = document.getElementById("feedback-filter").value; const query = new URLSearchParams({ page, page_size: 10 }); if (filter) query.set("feedback", filter); const data = await api(`/admin/feedback?${query}`); const host = document.getElementById("feedback-table"); host.textContent = ""; const table = document.createElement("table"); const head = document.createElement("tr"); ["Feedback", "Question", "Answer", "Language", "Confidence", "Sources", "Created"].forEach((text) => { const th = document.createElement("th"); th.textContent = text; head.appendChild(th); }); table.appendChild(head); data.items.forEach((item) => { const row = document.createElement("tr"); row.append(cell(item.feedback), cell(item.question), cell(item.answer), cell(item.language), cell(`${Math.round(item.confidence * 100)}%`), cell(item.sources.map((source) => source.document).join(", ")), cell(new Date(item.created_at).toLocaleString())); table.appendChild(row); }); host.appendChild(table); const pager = document.getElementById("feedback-pagination"); pager.textContent = `Page ${data.page} · ${data.total} total`; if (page > 1) pager.appendChild(button("Previous", () => loadFeedback(page - 1))); if (page * data.page_size < data.total) pager.appendChild(button("Next", () => loadFeedback(page + 1))); }
document.getElementById("feedback-filter").addEventListener("change", () => loadFeedback(1));

async function loadDocuments() {
  const data = await api("/documents");
  const host = document.getElementById("documents-table");
  host.textContent = "";
  const table = document.createElement("table");
  const head = document.createElement("tr");
  ["Filename", "Size", "Uploaded", "Uploaded by", "Status", "Error", "Action"].forEach((text) => {
    const th = document.createElement("th"); th.textContent = text; head.appendChild(th);
  });
  table.appendChild(head);
  data.forEach((item) => {
    const row = document.createElement("tr");
    row.append(cell(item.original_filename), cell(`${(item.size_bytes / 1024).toFixed(1)} KB`), cell(new Date(item.uploaded_at).toLocaleString()), cell(item.uploaded_by_name));
    const statusCell = cell(item.ingestion_status); statusCell.className = `status-badge status-${item.ingestion_status}`;
    row.append(statusCell, cell(item.ingestion_error));
    const action = document.createElement("td");
    if (user.role === "admin") {
      action.appendChild(button("Delete", async () => {
        if (!confirm("Delete this document?")) return;
        try { const result = await api(`/documents/${item.id}`, { method: "DELETE" }); if (result.warning) showError(result.warning); await loadDocuments(); await loadStats(); }
        catch (error) { showError(error.message); }
      }));
    } else action.textContent = "Read-only";
    row.appendChild(action); table.appendChild(row);
  });
  host.appendChild(table);
}

const documentForm = document.getElementById("document-upload-form");
const documentFile = document.getElementById("document-file");
const documentStatus = document.getElementById("document-upload-status");
if (user.role !== "admin") {
  documentForm.classList.add("hidden");
  document.getElementById("document-permission-note").textContent = "Staff access is read-only.";
}
documentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (user.role !== "admin") return;
  const file = documentFile.files[0];
  if (!file) return;
  const extension = `.${file.name.split(".").pop().toLowerCase()}`;
  if (![".pdf", ".docx", ".txt"].includes(extension)) { showError("Only PDF, DOCX, and TXT files are allowed."); return; }
  if (file.size === 0) { showError("Empty files are not allowed."); return; }
  if (file.size > 10 * 1024 * 1024) { showError("File exceeds the 10 MB upload limit."); return; }
  documentStatus.textContent = "Uploading...";
  const formData = new FormData(); formData.append("file", file);
  try {
    await apiFetch("/documents/upload", { method: "POST", body: formData });
    documentStatus.textContent = "Upload complete."; documentForm.reset(); await loadDocuments(); await loadStats();
  } catch (error) { documentStatus.textContent = ""; showError(error.message); }
});

async function loadUsers() { const data = await api("/admin/users"); const host = document.getElementById("users-table"); host.textContent = ""; const table = document.createElement("table"); const head = document.createElement("tr"); ["Name", "Email", "Role", "Active", "Created"].forEach((text) => { const th = document.createElement("th"); th.textContent = text; head.appendChild(th); }); table.appendChild(head); data.forEach((item) => { const row = document.createElement("tr"); row.append(cell(item.name), cell(item.email)); const roleCell = document.createElement("td"); const activeCell = document.createElement("td"); if (user.role === "admin") { const role = document.createElement("select"); ["student", "staff", "admin"].forEach((value) => { const option = document.createElement("option"); option.value = value; option.textContent = value; option.selected = value === item.role; role.appendChild(option); }); role.addEventListener("change", () => patchUser(item, { role: role.value })); roleCell.appendChild(role); const active = document.createElement("input"); active.type = "checkbox"; active.checked = item.is_active; active.addEventListener("change", () => patchUser(item, { is_active: active.checked })); activeCell.appendChild(active); } else { roleCell.textContent = item.role; activeCell.textContent = item.is_active ? "yes" : "no"; } row.append(roleCell, activeCell, cell(new Date(item.created_at).toLocaleString())); table.appendChild(row); }); host.appendChild(table); }
async function patchUser(item, body) { try { await api(`/admin/users/${item.id}`, { method: "PATCH", body: JSON.stringify(body) }); await loadUsers(); } catch (error) { showError(error.message); await loadUsers(); } }

const loaders = { overview: loadStats, notices: loadNotices, feedback: () => loadFeedback(1), users: loadUsers, documents: loadDocuments };
document.querySelectorAll(".admin-tabs button:not([disabled])").forEach((tab) => tab.addEventListener("click", async () => { clearError(); document.querySelectorAll(".admin-tab-panel").forEach((panel) => panel.classList.add("hidden")); document.getElementById(`tab-${tab.dataset.tab}`).classList.remove("hidden"); try { await loaders[tab.dataset.tab](); } catch (error) { showError(error.message); } }));
document.getElementById("logout-btn").addEventListener("click", () => { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); window.location.href = "login.html"; });
(async function init() { try { await loadStats(); } catch (error) { showError(error.message); } })();
