const API_BASE = "http://localhost:5069";
const PLATFORM = "p2p_chat";
const STUDENTS = ["StudentA", "StudentB"];
const CURRENT_USER_KEY = "safeguardCurrentUser";
const WORD_CATEGORIES = [
    "insult",
    "mockery",
    "humiliation",
    "exclusion",
    "harassment",
    "threat",
    "self-harm encouragement",
    "identity-targeted",
    "sexual-harassment",
    "appearance-shaming",
    "body-shaming",
    "gaslighting",
    "profanity-targeted",
    "intimidation"
];

let currentUser = loadSavedPerspective();
let messages = [];
let alerts = [];
let latestAnalyses = {};

const elements = {
    connectionStatus: document.getElementById("connectionStatus"),
    refreshMessagesBtn: document.getElementById("refreshMessagesBtn"),
    currentPerspective: document.getElementById("currentPerspective"),
    switchUserBtn: document.getElementById("switchUserBtn"),
    noticeArea: document.getElementById("noticeArea"),
    chatMessages: document.getElementById("chatMessages"),
    messageForm: document.getElementById("messageForm"),
    messageInput: document.getElementById("messageInput"),
    latestResult: document.getElementById("latestResult"),
    loadStudentABtn: document.getElementById("loadStudentABtn"),
    loadStudentBBtn: document.getElementById("loadStudentBBtn"),
    sessionResult: document.getElementById("sessionResult"),
    stakeholderFilter: document.getElementById("stakeholderFilter"),
    minScoreInput: document.getElementById("minScoreInput"),
    searchAlertsBtn: document.getElementById("searchAlertsBtn"),
    refreshAlertsBtn: document.getElementById("refreshAlertsBtn"),
    alertsList: document.getElementById("alertsList"),
    wordForm: document.getElementById("wordForm"),
    wordPhraseInput: document.getElementById("wordPhraseInput"),
    wordScoreInput: document.getElementById("wordScoreInput"),
    wordCategoryInput: document.getElementById("wordCategoryInput"),
    loadWordsBtn: document.getElementById("loadWordsBtn"),
    wordRegisterResult: document.getElementById("wordRegisterResult")
};

document.addEventListener("DOMContentLoaded", () => {
    updatePerspectiveDisplay();
    bindEvents();
    loadMessages();
    loadAlerts();
    renderCategoryOptions();
    setupSocket();
});

function bindEvents() {
    elements.switchUserBtn.addEventListener("click", switchPerspective);
    elements.refreshMessagesBtn.addEventListener("click", resetSimulation);
    elements.messageForm.addEventListener("submit", sendMessage);
    elements.loadStudentABtn.addEventListener("click", () => loadSession(STUDENTS[0]));
    elements.loadStudentBBtn.addEventListener("click", () => loadSession(STUDENTS[1]));
    elements.refreshAlertsBtn.addEventListener("click", loadAlerts);
    elements.searchAlertsBtn.addEventListener("click", searchAlerts);
    elements.stakeholderFilter.addEventListener("change", loadAlerts);
    elements.wordForm.addEventListener("submit", addWordRegister);
    elements.loadWordsBtn.addEventListener("click", loadWordCount);
}

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || "Backend request failed");
    }

    return data;
}

async function loadMessages() {
    try {
        const data = await apiRequest("/messages");
        messages = data
            .filter((message) => message.platform === PLATFORM)
            .sort((a, b) => Number(a.id || 0) - Number(b.id || 0));

        renderMessages();
        setConnection(true);
        clearNotice();
    } catch (error) {
        setConnection(false);
        showNotice("Could not load messages. Make sure the backend is running on http://localhost:5069.", true);
    }
}

async function resetSimulation() {
    elements.refreshMessagesBtn.disabled = true;
    elements.refreshMessagesBtn.textContent = "Restarting...";

    try {
        await apiRequest("/reset", {
            method: "POST",
            body: JSON.stringify({})
        });

        messages = [];
        alerts = [];
        latestAnalyses = {};
        elements.messageInput.value = "";
        elements.minScoreInput.value = "";
        elements.stakeholderFilter.value = "";
        elements.latestResult.textContent = "Send a message to see the analysis.";
        elements.sessionResult.textContent = "Choose a student to load session data.";

        renderMessages();
        renderAlerts();
        setConnection(true);
        showNotice("Chat restarted. Messages, alerts, sessions, and queue were cleared.", false);
    } catch (error) {
        setConnection(false);
        showNotice("Could not restart the chat. Make sure the backend is running.", true);
    } finally {
        elements.refreshMessagesBtn.disabled = false;
        elements.refreshMessagesBtn.textContent = "Refresh Chat";
    }
}

async function sendMessage(event) {
    event.preventDefault();

    const text = elements.messageInput.value.trim();
    if (!text) {
        showNotice("Please type a message before sending.", true);
        return;
    }

    const sender = currentUser;
    setSendLoading(true);

    try {
        const result = await apiRequest("/messages", {
            method: "POST",
            body: JSON.stringify({
                sender,
                platform: PLATFORM,
                text
            })
        });

        const message = result.message || {
            id: Date.now(),
            sender,
            platform: PLATFORM,
            text,
            timestamp: new Date().toISOString()
        };

        latestAnalyses[message.id] = {
            analysis: result.analysis || {},
            session: result.session_pattern || {}
        };

        messages.push(message);
        messages.sort((a, b) => Number(a.id || 0) - Number(b.id || 0));

        elements.messageInput.value = "";
        renderMessages();
        renderLatestResult(result);
        addIncomingAlerts(result.alerts || []);
        setConnection(true);
        clearNotice();
    } catch (error) {
        setConnection(false);
        showNotice(error.message || "Message could not be sent. Check if the backend is running.", true);
    } finally {
        setSendLoading(false);
    }
}

function renderMessages() {
    elements.chatMessages.innerHTML = "";

    if (messages.length === 0) {
        elements.chatMessages.innerHTML = '<div class="empty-state">No p2p_chat messages yet.</div>';
        return;
    }

    messages.forEach((message) => {
        const row = document.createElement("div");
        const isMine = message.sender === currentUser;
        row.className = `message-row ${isMine ? "mine" : "theirs"}`;

        const bubble = document.createElement("div");
        bubble.className = "message-bubble";

        const meta = document.createElement("div");
        meta.className = "message-meta";
        meta.textContent = `${safeText(message.sender)} - ${formatTime(message.timestamp)}`;

        const text = document.createElement("div");
        text.className = "message-text";
        text.textContent = message.text || "N/A";

        bubble.appendChild(meta);
        bubble.appendChild(text);

        const savedAnalysis = latestAnalyses[message.id];
        if (savedAnalysis) {
            bubble.appendChild(createAnalysisLine(savedAnalysis.analysis));
        }

        row.appendChild(bubble);
        elements.chatMessages.appendChild(row);
    });

    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function createAnalysisLine(analysis) {
    const line = document.createElement("div");
    line.className = "analysis-line";

    const level = analysis.level || "N/A";
    line.appendChild(createBadge(level));

    const details = document.createElement("span");
    details.textContent = `Score: ${valueOrNA(analysis.score)} | Action: ${valueOrNA(analysis.action)}`;
    line.appendChild(details);

    const matchedWords = formatList(analysis.matched_words);
    if (matchedWords !== "N/A") {
        const words = document.createElement("span");
        words.textContent = `| Matched: ${matchedWords}`;
        line.appendChild(words);
    }

    return line;
}

function switchPerspective() {
    currentUser = currentUser === STUDENTS[0] ? STUDENTS[1] : STUDENTS[0];
    savePerspective();
    updatePerspectiveDisplay();
    renderMessages();
}

function updatePerspectiveDisplay() {
    const otherUser = currentUser === STUDENTS[0] ? STUDENTS[1] : STUDENTS[0];
    elements.currentPerspective.textContent = `Current perspective: ${currentUser}`;
    elements.switchUserBtn.textContent = `Switch to ${otherUser}`;
    elements.messageInput.placeholder = `Message as ${currentUser}...`;
}

function loadSavedPerspective() {
    const savedUser = localStorage.getItem(CURRENT_USER_KEY);
    return STUDENTS.includes(savedUser) ? savedUser : STUDENTS[0];
}

function savePerspective() {
    localStorage.setItem(CURRENT_USER_KEY, currentUser);
}

function renderLatestResult(result) {
    const analysis = result.analysis || {};
    const session = result.session_pattern || {};
    const totalMessages = session.total_messages ?? session.total;

    elements.latestResult.innerHTML = "";
    elements.latestResult.appendChild(createDataGrid([
        ["Score", valueOrNA(analysis.score)],
        ["Level", createBadge(analysis.level || "N/A")],
        ["Action", valueOrNA(analysis.action)],
        ["Categories", formatList(analysis.categories)],
        ["Matched words", formatList(analysis.matched_words)],
        ["Pattern level", valueOrNA(session.pattern_level)],
        ["Total messages", valueOrNA(totalMessages)],
        ["High count", valueOrNA(session.high_count)],
        ["Escalating", formatBoolean(session.escalating)]
    ]));
}

async function loadAlerts() {
    const stakeholder = elements.stakeholderFilter.value;
    const path = stakeholder ? `/alerts?stakeholder=${encodeURIComponent(stakeholder)}` : "/alerts";

    try {
        const data = await apiRequest(path);
        alerts = data.filter((alert) => !alert.platform || alert.platform === PLATFORM);
        renderAlerts();
        setConnection(true);
    } catch (error) {
        setConnection(false);
        showNotice("Could not load alerts from the backend.", true);
    }
}

async function searchAlerts() {
    const minScore = elements.minScoreInput.value.trim();
    if (minScore === "") {
        showNotice("Enter a minimum score before searching alerts.", true);
        return;
    }

    try {
        const data = await apiRequest(`/alerts/search?min_score=${encodeURIComponent(minScore)}`);
        const stakeholder = elements.stakeholderFilter.value;
        alerts = data.filter((alert) => {
            const matchesPlatform = !alert.platform || alert.platform === PLATFORM;
            const matchesStakeholder = !stakeholder || alert.stakeholder === stakeholder;
            return matchesPlatform && matchesStakeholder;
        });
        renderAlerts();
        setConnection(true);
        clearNotice();
    } catch (error) {
        setConnection(false);
        showNotice("Alert search failed. Check the backend and score value.", true);
    }
}

function addIncomingAlerts(newAlerts) {
    newAlerts.forEach((alert) => {
        if (!alertExists(alert)) {
            alerts.unshift(alert);
        }
    });
    renderAlerts();
}

function renderAlerts() {
    elements.alertsList.innerHTML = "";

    if (alerts.length === 0) {
        elements.alertsList.innerHTML = '<div class="empty-state">No alerts found for this view.</div>';
        return;
    }

    groupAlerts(alerts).forEach((alert) => {
        const card = document.createElement("div");
        card.className = "alert-card";

        const top = document.createElement("div");
        top.className = "alert-top";

        const title = document.createElement("div");
        title.className = "alert-title";
        title.textContent = `alert for ${valueOrNA(alert.sender)} (${formatList(alert.stakeholders)})`;

        top.appendChild(title);
        top.appendChild(createBadge(alert.effective_level || alert.level || "N/A"));

        const grid = createDataGrid([
            ["Stakeholders", formatList(alert.stakeholders)],
            ["Action", valueOrNA(alert.action)],
            ["Score", valueOrNA(alert.score)],
            ["Matched words", formatList(alert.matched_words)],
            ["Message", valueOrNA(alert.original_message)]
        ]);

        card.appendChild(top);
        card.appendChild(grid);
        elements.alertsList.appendChild(card);
    });
}

function groupAlerts(alertList) {
    const grouped = new Map();

    alertList.forEach((alert) => {
        const key = [
            valueOrNA(alert.original_message),
            valueOrNA(alert.sender),
            valueOrNA(alert.score),
            valueOrNA(alert.action),
            valueOrNA(alert.effective_level || alert.level)
        ].join("|");

        if (!grouped.has(key)) {
            grouped.set(key, {
                ...alert,
                stakeholders: []
            });
        }

        const group = grouped.get(key);
        if (alert.stakeholder && !group.stakeholders.includes(alert.stakeholder)) {
            group.stakeholders.push(alert.stakeholder);
        }
    });

    return Array.from(grouped.values());
}

async function loadSession(student) {
    try {
        const data = await apiRequest(`/session?sender=${encodeURIComponent(student)}&platform=${encodeURIComponent(PLATFORM)}`);
        const totalMessages = data.total_messages ?? data.total;
        elements.sessionResult.innerHTML = "";
        elements.sessionResult.appendChild(createDataGrid([
            ["Student", student],
            ["Pattern level", valueOrNA(data.pattern_level)],
            ["Total messages", valueOrNA(totalMessages)],
            ["High count", valueOrNA(data.high_count)],
            ["Escalating", formatBoolean(data.escalating)]
        ]));
        setConnection(true);
        clearNotice();
    } catch (error) {
        setConnection(false);
        showNotice(`Could not load session for ${student}.`, true);
    }
}

async function loadWordCount() {
    try {
        const data = await apiRequest("/words");
        elements.wordRegisterResult.textContent = `words.json currently has ${valueOrNA(data.count)} entries.`;
        setConnection(true);
        clearNotice();
    } catch (error) {
        setConnection(false);
        elements.wordRegisterResult.textContent = "Could not load words.json count from the backend.";
    }
}

function renderCategoryOptions() {
    const currentValue = elements.wordCategoryInput.value;
    const categories = [...WORD_CATEGORIES].sort((a, b) => a.localeCompare(b));

    elements.wordCategoryInput.innerHTML = '<option value="">Choose category</option>';

    categories.forEach((category) => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        elements.wordCategoryInput.appendChild(option);
    });

    if (categories.includes(currentValue)) {
        elements.wordCategoryInput.value = currentValue;
    }
}

async function addWordRegister(event) {
    event.preventDefault();

    const phrase = elements.wordPhraseInput.value.trim();
    const score = elements.wordScoreInput.value.trim();
    const category = elements.wordCategoryInput.value.trim();

    if (!phrase || !score || !category) {
        elements.wordRegisterResult.textContent = "Please fill in phrase, score, and category.";
        return;
    }

    try {
        const data = await apiRequest("/words", {
            method: "POST",
            body: JSON.stringify({
                phrase,
                score: Number(score),
                category
            })
        });

        elements.wordForm.reset();
        elements.wordRegisterResult.textContent =
            `Saved "${data.entry.phrase}" with score ${data.entry.score} in ${data.entry.category}. Total entries: ${data.count}.`;
        setConnection(true);
        clearNotice();
    } catch (error) {
        setConnection(false);
        elements.wordRegisterResult.textContent = error.message || "Could not save the new word register.";
    }
}

function setupSocket() {
    if (typeof io === "undefined") {
        showNotice("Socket.IO could not load, so real-time alerts are disabled.", false);
        return;
    }

    const socket = io(API_BASE, {
        transports: ["websocket", "polling"]
    });

    socket.on("connect", () => {
        setConnection(true);
    });

    socket.on("connect_error", () => {
        setConnection(false);
    });

    socket.on("new_alert", (alert) => {
        if (!alert.platform || alert.platform === PLATFORM) {
            if (!alertExists(alert)) {
                alerts.unshift(alert);
            }
            renderAlerts();
        }
    });
}

function createDataGrid(items) {
    const grid = document.createElement("div");
    grid.className = "data-grid";

    items.forEach(([label, value]) => {
        const labelElement = document.createElement("strong");
        labelElement.textContent = label;

        const valueElement = document.createElement("span");
        if (value instanceof Node) {
            valueElement.appendChild(value);
        } else {
            valueElement.textContent = value;
        }

        grid.appendChild(labelElement);
        grid.appendChild(valueElement);
    });

    return grid;
}

function createBadge(level) {
    const badge = document.createElement("span");
    const normalized = String(level || "unknown").toLowerCase().replace(/[^a-z]/g, "");
    badge.className = `badge level-${normalized}`;
    badge.textContent = String(level || "N/A").toUpperCase();
    return badge;
}

function alertExists(newAlert) {
    return alerts.some((alert) => {
        return valueOrNA(alert.timestamp) === valueOrNA(newAlert.timestamp)
            && valueOrNA(alert.stakeholder) === valueOrNA(newAlert.stakeholder)
            && valueOrNA(alert.sender) === valueOrNA(newAlert.sender)
            && valueOrNA(alert.score) === valueOrNA(newAlert.score)
            && valueOrNA(alert.original_message) === valueOrNA(newAlert.original_message);
    });
}

function setConnection(isOnline) {
    elements.connectionStatus.classList.toggle("online", isOnline);
    elements.connectionStatus.classList.toggle("offline", !isOnline);
    elements.connectionStatus.textContent = isOnline ? "Backend connected" : "Backend not connected";
}

function setSendLoading(isLoading) {
    const button = elements.messageForm.querySelector("button");
    button.disabled = isLoading;
    button.textContent = isLoading ? "Sending..." : "Send";
}

function showNotice(message, isError) {
    elements.noticeArea.innerHTML = "";
    const notice = document.createElement("div");
    notice.className = `notice ${isError ? "error" : ""}`;
    notice.textContent = message;
    elements.noticeArea.appendChild(notice);
}

function clearNotice() {
    elements.noticeArea.innerHTML = "";
}

function formatList(value) {
    if (!Array.isArray(value) || value.length === 0) {
        return "N/A";
    }
    return value.join(", ");
}

function formatBoolean(value) {
    if (typeof value !== "boolean") {
        return "N/A";
    }
    return value ? "Yes" : "No";
}

function valueOrNA(value) {
    if (value === null || value === undefined || value === "") {
        return "N/A";
    }
    return String(value);
}

function formatTime(timestamp) {
    if (!timestamp) {
        return "N/A";
    }

    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) {
        return timestamp;
    }

    return date.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function safeText(value) {
    return value || "N/A";
}
