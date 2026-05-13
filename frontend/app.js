const VALID_CATEGORIES = [
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
  "profanity-general",
  "doxxing",
  "impersonation",
  "cyberstalking",
  "defamation",
  "intimidation"
];

const TARGET_WORDS = new Set(["you", "your", "u", "ur", "youre", "you're", "@user"]);
const HIGH_RISK_CATEGORIES = new Set(["threat", "self-harm encouragement", "sexual-harassment"]);

const FALLBACK_WORDS = {
  annoying: { score: 2, category: "insult" },
  loser: { score: 5, category: "humiliation" },
  "you are such a loser": { score: 8, category: "humiliation" },
  "nobody cares": { score: 5, category: "mockery" },
  "go away": { score: 5, category: "exclusion" },
  "kys": { score: 10, category: "self-harm encouragement" },
  stupid: { score: 5, category: "insult" }
};

const queueMessages = [
  "hey what's up",
  "you are such a loser",
  "nobody cares about this",
  "please stop spamming the chat",
  "kys you stupid",
  "that was a weird comment"
];

const state = {
  lexicon: {},
  baseCount: 0,
  backendCustomCount: 0,
  customCount: 0,
  localCustom: loadStoredJson("safeguardLocalCustom", {}),
  audit: loadStoredJson("safeguardAudit", []),
  lastResult: null
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

document.addEventListener("DOMContentLoaded", async () => {
  fillCategoryOptions();
  bindEvents();
  await loadLexicon();
  renderLexiconList();
  renderQueue();
  renderAudit();
  previewCurrentMessage();
});

function bindEvents() {
  $("#analyzeButton").addEventListener("click", analyzeCurrentMessage);
  $("#resetDemo").addEventListener("click", resetDemo);
  $("#messageInput").addEventListener("input", previewCurrentMessage);
  $("#analyzeQueue").addEventListener("click", scanQueue);
  $("#annotationForm").addEventListener("submit", saveCustomEntry);
  $("#lexiconSearch").addEventListener("input", renderLexiconList);
  $("#clearAudit").addEventListener("click", clearAudit);
  $("#copyJson").addEventListener("click", copyJson);
  $("#exportCustom").addEventListener("click", exportCustomJson);

  $$(".sample-row button").forEach((button) => {
    button.addEventListener("click", () => {
      $("#messageInput").value = button.dataset.sample;
      previewCurrentMessage();
    });
  });

  $$(".nav-list a").forEach((link) => {
    link.addEventListener("click", () => {
      $$(".nav-list a").forEach((item) => item.classList.remove("active"));
      link.classList.add("active");
    });
  });
}

async function loadLexicon() {
  const baseWords = await fetchJson(["../backend/words.json", "/backend/words.json"]);
  const customWords = await fetchJson(["../backend/custom_words.json", "/backend/custom_words.json"]);

  const base = baseWords || FALLBACK_WORDS;
  const custom = customWords || {};

  state.baseCount = Object.keys(base).length;
  state.backendCustomCount = Object.keys(custom).length;
  state.customCount = state.backendCustomCount + Object.keys(state.localCustom).length;
  state.lexicon = {
    ...base,
    ...custom,
    ...state.localCustom
  };

  const total = Object.keys(state.lexicon).length;
  $("#lexiconCount").textContent = `${total} phrases`;
  $("#lexiconSource").textContent = baseWords
    ? `${state.baseCount} base, ${state.customCount} custom`
    : "Fallback lexicon active";
  $("#engineStatus").textContent = baseWords ? "Loaded backend lexicon" : "Fallback lexicon";
}

async function fetchJson(paths) {
  for (const path of paths) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      continue;
    }
  }
  return null;
}

function previewCurrentMessage() {
  const message = $("#messageInput").value.trim();
  const result = analyzeMessage(message);
  state.lastResult = result;
  renderResult(result);
  return result;
}

function analyzeCurrentMessage() {
  const result = previewCurrentMessage();
  rememberAudit(result);
}

function analyzeMessage(message) {
  const normalized = normalizeText(message);
  const tokens = normalized ? normalized.split(" ") : [];
  const matches = findMatches(normalized);
  const matchedEntries = matches.map((match) => ({
    phrase: match.phrase,
    score: match.score,
    category: match.category,
    mode: "client_exact",
    occurrences: match.occurrences
  }));

  const categories = countBy(matchedEntries, "category");
  const exactScore = matchedEntries.reduce((sum, entry) => sum + entry.score, 0);
  const targeted = tokens.some((token) => TARGET_WORDS.has(token));
  const repetitionBonus = 0;
  const targetingBonus = targeted && exactScore > 0 ? 2 : 0;
  const toxicityBonus = calculateToxicityBonus(matchedEntries, tokens);
  const score = exactScore + repetitionBonus + targetingBonus + toxicityBonus;
  const level = classifyScore(score);
  const action = getAction(level);
  const reasonCodes = getReasonCodes(matchedEntries, targeted, repetitionBonus, toxicityBonus);

  return {
    success: true,
    data: {
      original_message: message,
      normalized_message: normalized,
      score,
      level,
      action,
      reason_codes: reasonCodes,
      targeted,
      repetition_bonus: repetitionBonus,
      targeting_bonus: targetingBonus,
      toxicity_accumulation: toxicityBonus,
      matched_words: matchedEntries.map((entry) => entry.phrase),
      matched_details: matchedEntries,
      categories,
      explanation: buildExplanation(categories, targeted, repetitionBonus, toxicityBonus)
    },
    errors: []
  };
}

function normalizeText(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s']/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function findMatches(normalized) {
  if (!normalized) {
    return [];
  }

  return Object.entries(state.lexicon)
    .map(([phrase, info]) => {
      const normalizedPhrase = normalizeText(phrase);
      const occurrences = countPhraseOccurrences(normalized, normalizedPhrase);
      return {
        phrase: normalizedPhrase,
        score: Number(info.score || 0),
        category: info.category || "harassment",
        occurrences
      };
    })
    .filter((entry) => entry.occurrences > 0)
    .sort((a, b) => b.score - a.score || a.phrase.localeCompare(b.phrase));
}

function countPhraseOccurrences(text, phrase) {
  if (!phrase) {
    return 0;
  }

  let count = 0;
  let index = text.indexOf(phrase);

  while (index !== -1) {
    const before = index === 0 ? " " : text[index - 1];
    const afterIndex = index + phrase.length;
    const after = afterIndex >= text.length ? " " : text[afterIndex];
    const hasBoundary = before === " " && after === " ";

    if (hasBoundary) {
      count += 1;
    }

    index = text.indexOf(phrase, index + 1);
  }

  return count;
}

function calculateToxicityBonus(matches, tokens) {
  let bonus = 0;

  if (matches.length >= 3) {
    bonus += 2;
  }

  if (matches.some((entry) => HIGH_RISK_CATEGORIES.has(entry.category))) {
    bonus += 3;
  }

  if (tokens.length <= 5 && matches.length > 0) {
    bonus += 1;
  }

  return bonus;
}

function classifyScore(score) {
  if (score >= 18) {
    return "HIGH";
  }
  if (score >= 7) {
    return "MEDIUM";
  }
  return "LOW";
}

function getAction(level) {
  if (level === "HIGH") {
    return "BLOCK";
  }
  if (level === "MEDIUM") {
    return "REVIEW";
  }
  return "ALLOW";
}

function getReasonCodes(matches, targeted, repetitionBonus, toxicityBonus) {
  const reasons = [];
  const categories = new Set(matches.map((entry) => entry.category));

  if (targeted) {
    reasons.push("targeted_abuse");
  }
  if (repetitionBonus > 0) {
    reasons.push("repetition");
  }
  if (toxicityBonus > 0) {
    reasons.push("toxicity_accumulation");
  }
  if (categories.has("self-harm encouragement")) {
    reasons.push("self_harm");
  }
  if (categories.has("threat")) {
    reasons.push("threat");
  }
  if (categories.has("sexual-harassment")) {
    reasons.push("sexual_harassment");
  }
  if (categories.has("identity-targeted")) {
    reasons.push("identity_attack");
  }
  if (reasons.length === 0 && matches.length > 0) {
    reasons.push("keyword_match");
  }

  return reasons;
}

function buildExplanation(categories, targeted, repetitionBonus, toxicityBonus) {
  const names = Object.entries(categories)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([name]) => name);

  if (names.length === 0) {
    return "No strong harassment indicators detected.";
  }

  let explanation = `Detected ${names.join(" and ")} language.`;

  if (targeted) {
    explanation += " Message appears directly targeted.";
  }
  if (repetitionBonus > 0) {
    explanation += " Repeated harmful patterns increased the risk.";
  }
  if (toxicityBonus > 0) {
    explanation += " Combined toxicity signals increased the final score.";
  }

  return explanation;
}

function renderResult(result) {
  const data = result.data;
  const ring = $("#riskRing");
  const scorePercent = Math.min(data.score, 30) / 30;
  const levelClass = data.level.toLowerCase();
  const actionClass = data.action.toLowerCase();

  $("#scoreValue").textContent = data.score;
  $("#levelBadge").textContent = data.level;
  $("#levelBadge").className = `level-badge ${levelClass}`;
  $("#actionValue").textContent = data.action;
  $("#explanationText").textContent = data.explanation;
  $("#targetedValue").textContent = data.targeted ? "Yes" : "No";
  $("#matchesValue").textContent = data.matched_details.length;
  $("#categoriesValue").textContent = Object.keys(data.categories).length;
  $("#bonusesValue").textContent =
    data.repetition_bonus + data.targeting_bonus + data.toxicity_accumulation;
  $("#normalizedText").textContent = data.normalized_message || "empty";
  $("#scanSummary").textContent = `${data.matched_details.length} phrase matches, ${data.score} total score`;
  $("#classifySummary").textContent = `${data.level} / ${data.action}`;
  ring.style.strokeDashoffset = String(314 - 314 * scorePercent);
  ring.style.stroke = data.level === "HIGH" ? "var(--red)" : data.level === "MEDIUM" ? "var(--amber)" : "var(--teal)";

  renderReasonCodes(data.reason_codes);
  renderMatchList(data.matched_details);
  renderCategoryBars(data.categories);
  $("#jsonOutput").textContent = JSON.stringify(result, null, 2);

  const panel = $("#riskPanel");
  panel.dataset.level = data.level;
  panel.querySelector("#actionValue").className = actionClass;
}

function renderReasonCodes(reasons) {
  const container = $("#reasonCodes");
  container.innerHTML = "";

  if (reasons.length === 0) {
    container.appendChild(emptyState("none"));
    return;
  }

  reasons.forEach((reason) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = reason;
    container.appendChild(chip);
  });
}

function renderMatchList(matches) {
  const container = $("#matchList");
  container.innerHTML = "";

  if (matches.length === 0) {
    container.appendChild(emptyState("No matched phrases"));
    return;
  }

  matches.forEach((match) => {
    const row = document.createElement("div");
    row.className = "match-item";
    row.innerHTML = `
      <div>
        <strong></strong>
        <p></p>
      </div>
      <span class="score-token"></span>
    `;
    row.querySelector("strong").textContent = match.phrase;
    row.querySelector("p").textContent = `${match.category} / ${match.mode} / ${match.occurrences} occurrence`;
    row.querySelector(".score-token").textContent = match.score;
    container.appendChild(row);
  });
}

function renderCategoryBars(categories) {
  const container = $("#categoryBars");
  const entries = Object.entries(categories).sort((a, b) => b[1] - a[1]);
  const max = entries.reduce((highest, [, value]) => Math.max(highest, value), 1);
  container.innerHTML = "";

  if (entries.length === 0) {
    container.appendChild(emptyState("No categories detected"));
    return;
  }

  entries.forEach(([category, count]) => {
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <span></span>
      <div class="bar-track"><div class="bar-fill"></div></div>
      <strong></strong>
    `;
    row.querySelector("span").textContent = category;
    row.querySelector(".bar-fill").style.width = `${(count / max) * 100}%`;
    row.querySelector("strong").textContent = count;
    container.appendChild(row);
  });
}

function renderQueue(results = []) {
  const container = $("#queueGrid");
  container.innerHTML = "";

  queueMessages.forEach((message, index) => {
    const result = results[index] || analyzeMessage(message);
    const data = result.data;
    const item = document.createElement("article");
    item.className = "queue-item";
    item.innerHTML = `
      <strong></strong>
      <p></p>
      <footer>
        <span class="action-pill"></span>
        <button class="ghost-button" type="button">Open</button>
      </footer>
    `;
    item.querySelector("strong").textContent = message;
    item.querySelector("p").textContent = data.explanation;
    const pill = item.querySelector(".action-pill");
    pill.textContent = `${data.level} / ${data.action}`;
    pill.classList.add(data.action.toLowerCase());
    item.querySelector("button").addEventListener("click", () => {
      $("#messageInput").value = message;
      previewCurrentMessage();
      document.querySelector("#scan").scrollIntoView({ behavior: "smooth" });
    });
    container.appendChild(item);
  });
}

function scanQueue() {
  const results = queueMessages.map((message) => analyzeMessage(message));
  renderQueue(results);
  results.forEach(rememberAudit);
}

function renderLexiconList() {
  const query = $("#lexiconSearch").value.trim().toLowerCase();
  const container = $("#lexiconList");
  const entries = Object.entries(state.lexicon)
    .filter(([phrase, info]) => {
      const category = String(info.category || "");
      return !query || phrase.toLowerCase().includes(query) || category.toLowerCase().includes(query);
    })
    .sort((a, b) => Number(b[1].score || 0) - Number(a[1].score || 0))
    .slice(0, 70);

  container.innerHTML = "";

  if (entries.length === 0) {
    container.appendChild(emptyState("No lexicon entries"));
    return;
  }

  entries.forEach(([phrase, info]) => {
    const item = document.createElement("div");
    item.className = "lexicon-item";
    item.innerHTML = `
      <div>
        <strong></strong>
        <p></p>
      </div>
      <span class="score-token"></span>
    `;
    item.querySelector("strong").textContent = phrase;
    item.querySelector("p").textContent = info.category || "harassment";
    item.querySelector(".score-token").textContent = info.score || 0;
    container.appendChild(item);
  });
}

function saveCustomEntry(event) {
  event.preventDefault();

  const phrase = normalizeText($("#newPhrase").value);
  const score = Number($("#newScore").value);
  const category = $("#newCategory").value;

  if (!phrase || !score) {
    return;
  }

  state.localCustom[phrase] = {
    score,
    category,
    severity: score >= 8 ? "high" : score >= 4 ? "medium" : "low",
    target_type: "unknown",
    directness: "direct",
    intent: "attack",
    platform_context: "general",
    needs_context: score < 8,
    repeat_sensitive: true
  };

  localStorage.setItem("safeguardLocalCustom", JSON.stringify(state.localCustom));
  state.lexicon[phrase] = state.localCustom[phrase];
  state.customCount = state.backendCustomCount + Object.keys(state.localCustom).length;
  $("#newPhrase").value = "";
  $("#newScore").value = "4";
  $("#lexiconCount").textContent = `${Object.keys(state.lexicon).length} phrases`;
  $("#lexiconSource").textContent = `${state.baseCount} base, ${state.customCount} custom`;
  renderLexiconList();
  previewCurrentMessage();
}

function fillCategoryOptions() {
  const select = $("#newCategory");
  VALID_CATEGORIES.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    select.appendChild(option);
  });
}

function rememberAudit(result) {
  const item = {
    timestamp: new Date().toISOString(),
    result
  };

  state.audit = [item, ...state.audit].slice(0, 12);
  localStorage.setItem("safeguardAudit", JSON.stringify(state.audit));
  renderAudit();
}

function renderAudit() {
  const container = $("#auditList");
  container.innerHTML = "";

  if (state.audit.length === 0) {
    container.appendChild(emptyState("No local audit entries"));
    return;
  }

  state.audit.forEach((entry) => {
    const data = entry.result.data;
    const item = document.createElement("div");
    item.className = "audit-item";
    item.innerHTML = `
      <time></time>
      <div>
        <strong></strong>
        <p></p>
      </div>
      <span class="action-pill"></span>
    `;
    item.querySelector("time").textContent = new Date(entry.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });
    item.querySelector("strong").textContent = data.original_message || "empty";
    item.querySelector("p").textContent = data.explanation;
    const pill = item.querySelector(".action-pill");
    pill.textContent = data.action;
    pill.classList.add(data.action.toLowerCase());
    container.appendChild(item);
  });
}

function clearAudit() {
  state.audit = [];
  localStorage.removeItem("safeguardAudit");
  renderAudit();
}

async function copyJson() {
  if (!state.lastResult) {
    return;
  }

  const value = JSON.stringify(state.lastResult, null, 2);

  try {
    await navigator.clipboard.writeText(value);
  } catch (error) {
    const range = document.createRange();
    range.selectNodeContents($("#jsonOutput"));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }

  $("#copyJson").textContent = "Copied";
  setTimeout(() => {
    $("#copyJson").textContent = "Copy";
  }, 1200);
}

function exportCustomJson() {
  const blob = new Blob([JSON.stringify(state.localCustom, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "custom_words.json";
  anchor.click();
  URL.revokeObjectURL(url);
}

async function resetDemo() {
  state.localCustom = {};
  state.audit = [];
  localStorage.removeItem("safeguardLocalCustom");
  localStorage.removeItem("safeguardAudit");

  $("#messageInput").value = "you are such a loser";
  $("#newPhrase").value = "";
  $("#newScore").value = "4";
  $("#newCategory").value = "mockery";
  $("#lexiconSearch").value = "";

  await loadLexicon();
  renderLexiconList();
  renderQueue();
  renderAudit();
  previewCurrentMessage();
  document.querySelector("#scan").scrollIntoView({ behavior: "smooth" });
}

function countBy(items, key) {
  return items.reduce((acc, item) => {
    acc[item[key]] = (acc[item[key]] || 0) + 1;
    return acc;
  }, {});
}

function loadStoredJson(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch (error) {
    return fallback;
  }
}

function emptyState(text) {
  const element = document.createElement("p");
  element.className = "empty-state";
  element.textContent = text;
  return element;
}
