/**
 * Story Engine - Main Application Logic
 */

// Application state
const state = {
    apiKey: "",
    modelId: "",
    outputs: {
        step0_output: "",
        step1_output: "",
        step2_output: ""
    },
    evaluationHistory: [],
    authenticated: false
};

// DOM Elements
const elements = {};

/**
 * Initialize the application
 */
function init() {
    // Cache DOM elements
    cacheElements();

    // Initialize CodeMirror editors
    window.StoryEditor.initAllEditors();

    // Check for password gate
    if (window.APP_CONFIG.hasPassword) {
        checkAuthentication();
    } else {
        state.authenticated = true;
        hidePasswordModal();
    }

    // Set up API key handling
    setupApiKey();

    // Set up event listeners
    setupEventListeners();

    // Load state from localStorage
    loadState();

    // Update UI
    updateApiKeyWarning();
    updateSaveButton();
}

/**
 * Cache commonly used DOM elements
 */
function cacheElements() {
    elements.passwordModal = document.getElementById("password-modal");
    elements.passwordInput = document.getElementById("password-input");
    elements.loginBtn = document.getElementById("login-btn");
    elements.passwordError = document.getElementById("password-error");

    elements.apiKeyInput = document.getElementById("api-key");
    elements.overrideCheckbox = document.getElementById("override-api-key");
    elements.apiKeyOverride = document.getElementById("api-key-override");
    elements.modelSelect = document.getElementById("model-select");
    elements.apiKeyWarning = document.getElementById("api-key-warning");

    elements.loadingOverlay = document.getElementById("loading-overlay");
    elements.loadingText = document.getElementById("loading-text");

    elements.exportFullSessionBtn = document.getElementById("export-full-session-btn");
    elements.saveSessionContainer = document.getElementById("save-session-container");

    elements.evalModelSelect = document.getElementById("eval-model-select");
    elements.evalBtn = document.getElementById("eval-btn");
    elements.evalClearBtn = document.getElementById("eval-clear-btn");
    elements.evalHistory = document.getElementById("eval-history");
    elements.evalVariables = document.getElementById("eval-variables");
}

/**
 * Check if user is authenticated (for password protected apps)
 */
function checkAuthentication() {
    const savedAuth = localStorage.getItem("story-engine-auth");
    if (savedAuth === "true") {
        state.authenticated = true;
        hidePasswordModal();
    }
}

/**
 * Hide the password modal
 */
function hidePasswordModal() {
    if (elements.passwordModal) {
        elements.passwordModal.style.display = "none";
    }
}

/**
 * Set up API key handling
 */
function setupApiKey() {
    // If environment API key exists on server, mark it as available
    // The actual key stays server-side for security
    if (window.APP_CONFIG.hasEnvApiKey) {
        state.apiKey = "__ENV_KEY__";  // Marker that server has the key
        updateApiKeyWarning();
    }

    // Set initial model
    if (elements.modelSelect) {
        state.modelId = elements.modelSelect.value;
    }
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // Password login
    if (elements.loginBtn) {
        elements.loginBtn.addEventListener("click", handleLogin);
    }
    if (elements.passwordInput) {
        elements.passwordInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") handleLogin();
        });
    }

    // API key override checkbox
    if (elements.overrideCheckbox) {
        elements.overrideCheckbox.addEventListener("change", (e) => {
            if (elements.apiKeyOverride) {
                elements.apiKeyOverride.style.display = e.target.checked ? "block" : "none";
            }
            if (!e.target.checked && window.APP_CONFIG.hasEnvApiKey) {
                // Reset to server's env API key
                state.apiKey = "__ENV_KEY__";
                updateApiKeyWarning();
            }
        });
    }

    // API key input
    if (elements.apiKeyInput) {
        elements.apiKeyInput.addEventListener("input", (e) => {
            state.apiKey = e.target.value;
            updateApiKeyWarning();
            saveState();
        });
    }

    // Model select
    if (elements.modelSelect) {
        elements.modelSelect.addEventListener("change", (e) => {
            state.modelId = e.target.value;
            saveState();
        });
    }

    // Generate buttons
    document.querySelectorAll(".generate-btn").forEach(btn => {
        btn.addEventListener("click", () => handleGenerate(parseInt(btn.dataset.step)));
    });

    // Export buttons
    document.querySelectorAll(".export-btn").forEach(btn => {
        btn.addEventListener("click", () => handleExport(parseInt(btn.dataset.step)));
    });

    // Copy buttons (for output)
    document.querySelectorAll(".copy-btn").forEach(btn => {
        btn.addEventListener("click", () => handleCopy(parseInt(btn.dataset.step)));
    });

    // Edit/Done toggle buttons for editors
    document.querySelectorAll(".edit-toggle-btn").forEach(btn => {
        btn.addEventListener("click", () => handleEditToggle(btn));
    });

    // Copy buttons for editors
    document.querySelectorAll(".editor-copy-btn").forEach(btn => {
        btn.addEventListener("click", () => handleEditorCopy(btn));
    });

    // Export full session
    if (elements.exportFullSessionBtn) {
        elements.exportFullSessionBtn.addEventListener("click", handleExportFullSession);
    }

    // Evaluation panel
    if (elements.evalBtn) {
        elements.evalBtn.addEventListener("click", handleEvaluate);
    }
    if (elements.evalClearBtn) {
        elements.evalClearBtn.addEventListener("click", () => {
            state.evaluationHistory = [];
            renderEvaluationHistory();
            saveState();
        });
    }

    // Editor change events for variable status updates
    document.querySelectorAll("textarea.code-editor").forEach(textarea => {
        textarea.addEventListener("editor-change", (e) => {
            const match = textarea.id.match(/step(\d+)-user/);
            if (match) {
                updateVariablesStatus(parseInt(match[1]));
            }
            // Also update eval panel variable status
            if (textarea.id === "eval-user") {
                updateEvalVariablesStatus();
            }
        });
    });

    // Refresh eval panel editors when details is opened (CodeMirror needs this)
    const evalDetails = document.querySelector(".evaluation-panel details");
    if (evalDetails) {
        evalDetails.addEventListener("toggle", () => {
            if (evalDetails.open) {
                // Refresh CodeMirror editors inside the panel
                const evalSystem = window.StoryEditor.getEditor("eval-system");
                const evalUser = window.StoryEditor.getEditor("eval-user");
                if (evalSystem) evalSystem.refresh();
                if (evalUser) evalUser.refresh();
                // Update variable status
                updateEvalVariablesStatus();
            }
        });
    }
}

/**
 * Handle password login
 */
async function handleLogin() {
    const password = elements.passwordInput.value;

    try {
        const response = await fetch("/api/check-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password })
        });
        const data = await response.json();

        if (data.valid) {
            state.authenticated = true;
            localStorage.setItem("story-engine-auth", "true");
            hidePasswordModal();
        } else {
            elements.passwordError.style.display = "block";
        }
    } catch (error) {
        console.error("Login error:", error);
        elements.passwordError.textContent = "Error checking password";
        elements.passwordError.style.display = "block";
    }
}

/**
 * Handle generate button click
 * @param {number} stepNum - The step number (0, 1, or 2)
 */
async function handleGenerate(stepNum) {
    const systemPrompt = window.StoryEditor.getEditorValue(`step${stepNum}-system`);
    const userPrompt = window.StoryEditor.getEditorValue(`step${stepNum}-user`);

    if (!userPrompt.trim()) {
        alert("Please enter a user prompt");
        return;
    }

    if (!state.apiKey) {
        alert("Please enter an API key");
        return;
    }

    // Check for include previous
    const includeCheckbox = document.getElementById(`step${stepNum}-include-prev`);
    const includePrevious = includeCheckbox ? includeCheckbox.checked : false;

    // Build outputs object including user prompts for context
    const outputs = { ...state.outputs };
    for (let i = 0; i < stepNum; i++) {
        outputs[`step${i}_user`] = window.StoryEditor.getEditorValue(`step${i}-user`);
    }

    showLoading("Generating...");

    // If using server's env key, send empty string (server will use its env var)
    const apiKeyToSend = state.apiKey === "__ENV_KEY__" ? "" : state.apiKey;

    try {
        const response = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                api_key: apiKeyToSend,
                model_id: state.modelId,
                system_prompt: systemPrompt,
                user_prompt: userPrompt,
                outputs: outputs,
                include_previous: includePrevious,
                step_num: stepNum
            })
        });

        const data = await response.json();

        if (response.ok) {
            state.outputs[`step${stepNum}_output`] = data.output;
            displayOutput(stepNum, data.output);
            updateSaveButton();
            saveState();
            // Update variable status for subsequent steps
            for (let i = stepNum + 1; i <= 2; i++) {
                updateVariablesStatus(i);
            }
        } else {
            alert(`Error: ${data.detail || "Generation failed"}`);
        }
    } catch (error) {
        console.error("Generate error:", error);
        alert(`Error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

/**
 * Display output for a step
 * @param {number} stepNum - The step number
 * @param {string} output - The output text
 */
function displayOutput(stepNum, output) {
    const section = document.getElementById(`step${stepNum}-output-section`);
    const display = document.getElementById(`step${stepNum}-output`);

    if (section && display) {
        section.style.display = "block";

        // For step 2 (story), render as markdown-like content
        if (stepNum === 2) {
            display.classList.add("markdown");
            display.innerHTML = formatMarkdown(output);
        } else {
            display.classList.remove("markdown");
            display.textContent = output;
        }
    }
}

/**
 * Simple markdown formatting
 * @param {string} text - The text to format
 * @returns {string} HTML-formatted text
 */
function formatMarkdown(text) {
    // Escape HTML first
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Convert line breaks
    html = html.replace(/\n/g, "<br>");

    return html;
}

/**
 * Handle export button click
 * @param {number} stepNum - The step number
 */
async function handleExport(stepNum) {
    const step = window.APP_CONFIG.steps[stepNum];
    const systemPrompt = window.StoryEditor.getEditorValue(`step${stepNum}-system`);
    const userPrompt = window.StoryEditor.getEditorValue(`step${stepNum}-user`);

    const includeCheckbox = document.getElementById(`step${stepNum}-include-prev`);
    const includePrevious = includeCheckbox ? includeCheckbox.checked : false;

    // Gather all prompts for previous steps
    const allPrompts = [];
    for (let i = 0; i <= stepNum; i++) {
        allPrompts.push({
            system: window.StoryEditor.getEditorValue(`step${i}-system`),
            user: window.StoryEditor.getEditorValue(`step${i}-user`)
        });
    }

    try {
        const response = await fetch("/api/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                step_num: stepNum,
                step_title: step.title,
                system_prompt: systemPrompt,
                user_prompt: userPrompt,
                outputs: state.outputs,
                include_previous: includePrevious,
                all_prompts: allPrompts
            })
        });

        const text = await response.text();

        // Create download
        const blob = new Blob([text], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `step${stepNum}_prompts.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error("Export error:", error);
        alert(`Error exporting: ${error.message}`);
    }
}

/**
 * Handle copy button click
 * @param {number} stepNum - The step number
 */
function handleCopy(stepNum) {
    const output = state.outputs[`step${stepNum}_output`];
    if (!output) return;

    navigator.clipboard.writeText(output).then(() => {
        const btn = document.querySelector(`.copy-btn[data-step="${stepNum}"]`);
        if (btn) {
            btn.classList.add("copied");
            setTimeout(() => btn.classList.remove("copied"), 1500);
        }
    }).catch(err => {
        console.error("Copy failed:", err);
        // Fallback for older browsers
        const textarea = document.createElement("textarea");
        textarea.value = output;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    });
}

/**
 * Handle edit/done toggle button click
 * @param {HTMLButtonElement} btn - The button element
 */
function handleEditToggle(btn) {
    const editorId = btn.dataset.editor;
    const isEditing = btn.dataset.editing === "true";
    const editor = window.StoryEditor.getEditor(editorId);
    const wrapper = btn.closest(".editor-container").querySelector(".editor-wrapper");

    if (isEditing) {
        // Switch to read-only (Done clicked)
        btn.textContent = "Edit";
        btn.dataset.editing = "false";
        btn.classList.add("editing-false");
        wrapper.classList.add("readonly");
        if (editor) {
            editor.setOption("readOnly", true);
        }
    } else {
        // Switch to editing (Edit clicked)
        btn.textContent = "Done";
        btn.dataset.editing = "true";
        btn.classList.remove("editing-false");
        wrapper.classList.remove("readonly");
        if (editor) {
            editor.setOption("readOnly", false);
            editor.focus();
        }
    }
}

/**
 * Handle editor copy button click
 * @param {HTMLButtonElement} btn - The button element
 */
function handleEditorCopy(btn) {
    const editorId = btn.dataset.editor;
    const content = window.StoryEditor.getEditorValue(editorId);

    if (!content) return;

    navigator.clipboard.writeText(content).then(() => {
        btn.classList.add("copied");
        setTimeout(() => btn.classList.remove("copied"), 1500);
    }).catch(err => {
        console.error("Copy failed:", err);
        // Fallback for older browsers
        const textarea = document.createElement("textarea");
        textarea.value = content;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);

        btn.classList.add("copied");
        setTimeout(() => btn.classList.remove("copied"), 1500);
    });
}

/**
 * Handle export full session button click - downloads as text file
 */
function handleExportFullSession() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const dateStr = new Date().toLocaleString();

    let content = `Story Engine - Full Session Export\n`;
    content += `Generated: ${dateStr}\n`;
    content += `${"=".repeat(60)}\n\n`;

    for (let i = 0; i <= 2; i++) {
        const step = window.APP_CONFIG.steps[i];
        const systemPrompt = window.StoryEditor.getEditorValue(`step${i}-system`);
        const userPrompt = window.StoryEditor.getEditorValue(`step${i}-user`);
        const output = state.outputs[`step${i}_output`] || "";

        content += `${"=".repeat(60)}\n`;
        content += `STEP ${i}: ${step.title.toUpperCase()}\n`;
        content += `${"=".repeat(60)}\n\n`;

        content += `--- System Prompt ---\n`;
        content += `${systemPrompt}\n\n`;

        content += `--- User Prompt ---\n`;
        content += `${userPrompt}\n\n`;

        content += `--- Output ---\n`;
        content += `${output}\n\n`;
    }

    // Create and trigger download
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `story_session_${timestamp}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Handle evaluate button click
 */
async function handleEvaluate() {
    const systemPrompt = window.StoryEditor.getEditorValue("eval-system");
    const userPrompt = window.StoryEditor.getEditorValue("eval-user");
    const modelId = elements.evalModelSelect.value;
    const modelName = elements.evalModelSelect.options[elements.evalModelSelect.selectedIndex].text;

    if (!userPrompt.trim()) {
        alert("Please enter a user prompt");
        return;
    }

    if (!state.apiKey) {
        alert("Please enter an API key");
        return;
    }

    showLoading("Evaluating...");

    // If using server's env key, send empty string (server will use its env var)
    const apiKeyToSend = state.apiKey === "__ENV_KEY__" ? "" : state.apiKey;

    try {
        const response = await fetch("/api/evaluate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                api_key: apiKeyToSend,
                model_id: modelId,
                system_prompt: systemPrompt,
                user_prompt: userPrompt,
                outputs: state.outputs
            })
        });

        const data = await response.json();

        if (response.ok) {
            state.evaluationHistory.unshift({
                system_prompt: systemPrompt,
                user_prompt: userPrompt,
                response: data.response,
                model: modelName
            });
            renderEvaluationHistory();
            saveState();
        } else {
            alert(`Error: ${data.detail || "Evaluation failed"}`);
        }
    } catch (error) {
        console.error("Evaluate error:", error);
        alert(`Error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

/**
 * Update variable status for evaluation panel
 */
function updateEvalVariablesStatus() {
    if (!elements.evalVariables) return;

    const userPrompt = window.StoryEditor.getEditorValue("eval-user");
    const pattern = /\bstep\d+_output\b/g;
    const matches = userPrompt.match(pattern);

    if (!matches || matches.length === 0) {
        elements.evalVariables.innerHTML = "";
        return;
    }

    const unique = [...new Set(matches)];
    const valid = unique.filter(v => state.outputs[v]);
    const pending = unique.filter(v => !state.outputs[v]);

    let html = "Variables detected: ";
    if (valid.length > 0) {
        html += `<span class="valid">Ready: ${valid.join(", ")}</span>`;
    }
    if (pending.length > 0) {
        if (valid.length > 0) html += " | ";
        html += `<span class="pending">Pending: ${pending.join(", ")}</span>`;
    }

    elements.evalVariables.innerHTML = html;
}

/**
 * Render evaluation history
 */
function renderEvaluationHistory() {
    if (!elements.evalHistory) return;

    if (state.evaluationHistory.length === 0) {
        elements.evalHistory.innerHTML = "";
        return;
    }

    let html = "<hr><strong>Evaluation History:</strong>";

    state.evaluationHistory.forEach((item, index) => {
        const num = state.evaluationHistory.length - index;
        const userPreview = item.user_prompt && item.user_prompt.length > 150
            ? item.user_prompt.substring(0, 150) + "..."
            : (item.user_prompt || item.text || "");

        html += `
            <div class="eval-item">
                <div class="eval-item-header">#${num} (${item.model})</div>
                <div class="eval-item-text"><strong>System:</strong> ${escapeHtml(item.system_prompt || "N/A")}</div>
                <div class="eval-item-question"><strong>User:</strong> ${escapeHtml(userPreview)}</div>
                <div class="eval-item-response">${escapeHtml(item.response)}</div>
            </div>
        `;
    });

    elements.evalHistory.innerHTML = html;
}

/**
 * Update variables status display for a step
 * @param {number} stepNum - The step number
 */
function updateVariablesStatus(stepNum) {
    const statusEl = document.getElementById(`step${stepNum}-variables`);
    if (!statusEl) return;

    const userPrompt = window.StoryEditor.getEditorValue(`step${stepNum}-user`);
    const pattern = /\bstep\d+_output\b/g;
    const matches = userPrompt.match(pattern);

    if (!matches || matches.length === 0) {
        statusEl.innerHTML = "";
        return;
    }

    const unique = [...new Set(matches)];
    const valid = unique.filter(v => state.outputs[v]);
    const pending = unique.filter(v => !state.outputs[v]);

    let html = "Variables detected: ";
    if (valid.length > 0) {
        html += `<span class="valid">Ready: ${valid.join(", ")}</span>`;
    }
    if (pending.length > 0) {
        if (valid.length > 0) html += " | ";
        html += `<span class="pending">Pending: ${pending.join(", ")}</span>`;
    }

    statusEl.innerHTML = html;
}

/**
 * Update API key warning visibility
 */
function updateApiKeyWarning() {
    if (elements.apiKeyWarning) {
        elements.apiKeyWarning.style.display = state.apiKey ? "none" : "block";
    }

    // Update generate button states
    document.querySelectorAll(".generate-btn").forEach(btn => {
        btn.disabled = !state.apiKey;
    });

    // Update evaluate button state
    if (elements.evalBtn) {
        elements.evalBtn.disabled = !state.apiKey;
    }
}

/**
 * Update save session button visibility
 */
function updateSaveButton() {
    if (elements.saveSessionContainer) {
        const hasStep2Output = state.outputs.step2_output && state.outputs.step2_output.trim();
        elements.saveSessionContainer.style.display = hasStep2Output ? "block" : "none";
    }
}

/**
 * Show loading overlay
 * @param {string} text - Loading text to display
 */
function showLoading(text = "Loading...") {
    if (elements.loadingOverlay) {
        elements.loadingText.textContent = text;
        elements.loadingOverlay.style.display = "flex";
    }
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    if (elements.loadingOverlay) {
        elements.loadingOverlay.style.display = "none";
    }
}

/**
 * Escape HTML entities
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Save state to localStorage
 */
function saveState() {
    const saveData = {
        outputs: state.outputs,
        evaluationHistory: state.evaluationHistory,
        modelId: state.modelId
    };

    // Save prompts
    for (let i = 0; i <= 2; i++) {
        saveData[`step${i}_system`] = window.StoryEditor.getEditorValue(`step${i}-system`);
        saveData[`step${i}_user`] = window.StoryEditor.getEditorValue(`step${i}-user`);

        const includeCheckbox = document.getElementById(`step${i}-include-prev`);
        if (includeCheckbox) {
            saveData[`step${i}_include_prev`] = includeCheckbox.checked;
        }
    }

    // Don't save API key for security
    localStorage.setItem("story-engine-state", JSON.stringify(saveData));
}

/**
 * Load state from localStorage
 */
function loadState() {
    try {
        const saved = localStorage.getItem("story-engine-state");
        if (!saved) return;

        const data = JSON.parse(saved);

        // Restore outputs
        if (data.outputs) {
            state.outputs = data.outputs;
            for (let i = 0; i <= 2; i++) {
                if (state.outputs[`step${i}_output`]) {
                    displayOutput(i, state.outputs[`step${i}_output`]);
                }
            }
        }

        // Restore evaluation history
        if (data.evaluationHistory) {
            state.evaluationHistory = data.evaluationHistory;
            renderEvaluationHistory();
        }

        // Restore model selection
        if (data.modelId && elements.modelSelect) {
            elements.modelSelect.value = data.modelId;
            state.modelId = data.modelId;
        }

        // Restore prompts
        for (let i = 0; i <= 2; i++) {
            if (data[`step${i}_system`]) {
                window.StoryEditor.setEditorValue(`step${i}-system`, data[`step${i}_system`]);
            }
            if (data[`step${i}_user`]) {
                window.StoryEditor.setEditorValue(`step${i}-user`, data[`step${i}_user`]);
            }

            const includeCheckbox = document.getElementById(`step${i}-include-prev`);
            if (includeCheckbox && data[`step${i}_include_prev`] !== undefined) {
                includeCheckbox.checked = data[`step${i}_include_prev`];
            }

            updateVariablesStatus(i);
        }
    } catch (error) {
        console.error("Error loading state:", error);
    }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", init);
