/**
 * Story Engine - Ideas Page Logic
 */

// Output variable names for the ideas page
const IDEA_VARS = [
    "priming_output", "idea_output", "postprocess_output",
    "step0_output", "step1_output", "step2_output"
];
const OUTPUT_VAR_MAP = { 0: "priming_output", 1: "idea_output", 2: "postprocess_output" };
const STEP_ALIAS_MAP = { 0: "step0_output", 1: "step1_output", 2: "step2_output" };

// Application state
const state = {
    apiKey: "",
    modelId: "",
    outputs: {
        priming_output: "",
        idea_output: "",
        postprocess_output: "",
        step0_output: "",
        step1_output: "",
        step2_output: ""
    },
    authenticated: false
};

// DOM Elements
const elements = {};

/**
 * Initialize the application
 */
function init() {
    // Set variables for highlighting/autocomplete before initializing editors
    window.StoryEditor.setAvailableVariables(IDEA_VARS);

    // Cache DOM elements
    cacheElements();

    // Initialize CodeMirror editors
    window.StoryEditor.initAllEditors();

    // Redirect to home page for authentication if needed
    if (window.APP_CONFIG.hasPassword && localStorage.getItem("story-engine-auth") !== "true") {
        window.location.href = "/";
        return;
    }
    state.authenticated = true;

    // Set up API key handling
    setupApiKey();

    // Set up event listeners
    setupEventListeners();

    // Load state from localStorage
    loadState();

    // Update UI
    updateApiKeyWarning();
}

/**
 * Cache commonly used DOM elements
 */
function cacheElements() {
    elements.apiKeyInput = document.getElementById("api-key");
    elements.overrideCheckbox = document.getElementById("override-api-key");
    elements.apiKeyOverride = document.getElementById("api-key-override");
    elements.modelSelect = document.getElementById("model-select");
    elements.apiKeyWarning = document.getElementById("api-key-warning");

    elements.loadingOverlay = document.getElementById("loading-overlay");
    elements.loadingText = document.getElementById("loading-text");

    elements.sampleGenresBtn = document.getElementById("sample-genres-btn");
    elements.sampleWordsBtn = document.getElementById("sample-words-btn");
    elements.includePriming = document.getElementById("include-priming");
}

/**
 * Set up API key handling
 */
function setupApiKey() {
    if (window.APP_CONFIG.hasEnvApiKey) {
        state.apiKey = "__ENV_KEY__";
        updateApiKeyWarning();
    }
    if (elements.modelSelect) {
        state.modelId = elements.modelSelect.value;
    }
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // API key override checkbox
    if (elements.overrideCheckbox) {
        elements.overrideCheckbox.addEventListener("change", (e) => {
            if (elements.apiKeyOverride) {
                elements.apiKeyOverride.style.display = e.target.checked ? "block" : "none";
            }
            if (!e.target.checked && window.APP_CONFIG.hasEnvApiKey) {
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

    // Sample buttons
    if (elements.sampleGenresBtn) {
        elements.sampleGenresBtn.addEventListener("click", handleSampleGenres);
    }
    if (elements.sampleWordsBtn) {
        elements.sampleWordsBtn.addEventListener("click", handleSampleWords);
    }

    // Generate buttons
    document.querySelectorAll(".idea-generate-btn").forEach(btn => {
        btn.addEventListener("click", () => handleGenerate(parseInt(btn.dataset.step)));
    });

    // Copy buttons
    document.querySelectorAll(".idea-copy-btn").forEach(btn => {
        btn.addEventListener("click", () => handleCopy(parseInt(btn.dataset.step)));
    });

    // Edit/Done toggle buttons
    document.querySelectorAll(".edit-toggle-btn").forEach(btn => {
        btn.addEventListener("click", () => handleEditToggle(btn));
    });

    // Copy buttons for editors
    document.querySelectorAll(".editor-copy-btn").forEach(btn => {
        btn.addEventListener("click", () => handleEditorCopy(btn));
    });

    // Editor change events for variable status updates
    document.querySelectorAll("textarea.code-editor").forEach(textarea => {
        textarea.addEventListener("editor-change", () => {
            const match = textarea.id.match(/idea-step(\d+)-user/);
            if (match) {
                updateVariablesStatus(parseInt(match[1]));
            }
        });
    });
}

/**
 * Handle Sample Genres button
 */
async function handleSampleGenres() {
    elements.sampleGenresBtn.disabled = true;
    elements.sampleGenresBtn.textContent = "Sampling...";
    try {
        const response = await fetch("/api/ideas/sample-genres", { method: "POST" });
        const data = await response.json();
        if (response.ok) {
            window.StoryEditor.setEditorValue("idea-step0-user", data.prompt);
        } else {
            alert(`Error: ${data.detail || "Failed to sample genres"}`);
        }
    } catch (error) {
        console.error("Sample genres error:", error);
        alert(`Error: ${error.message}`);
    } finally {
        elements.sampleGenresBtn.disabled = false;
        elements.sampleGenresBtn.textContent = "Sample Genres";
    }
}

/**
 * Handle Sample Words button
 */
async function handleSampleWords() {
    elements.sampleWordsBtn.disabled = true;
    elements.sampleWordsBtn.textContent = "Sampling...";
    try {
        const response = await fetch("/api/ideas/sample-words", { method: "POST" });
        const data = await response.json();
        if (response.ok) {
            window.StoryEditor.setEditorValue("idea-step1-user", data.prompt);
        } else {
            alert(`Error: ${data.detail || "Failed to sample words"}`);
        }
    } catch (error) {
        console.error("Sample words error:", error);
        alert(`Error: ${error.message}`);
    } finally {
        elements.sampleWordsBtn.disabled = false;
        elements.sampleWordsBtn.textContent = "Sample Words";
    }
}

/**
 * Handle generate button click
 * @param {number} stepNum - The step number (0, 1, or 2)
 */
async function handleGenerate(stepNum) {
    const systemPrompt = window.StoryEditor.getEditorValue(`idea-step${stepNum}-system`);
    const userPrompt = window.StoryEditor.getEditorValue(`idea-step${stepNum}-user`);

    if (!userPrompt.trim()) {
        alert("Please enter a user prompt");
        return;
    }
    if (!state.apiKey) {
        alert("Please enter an API key");
        return;
    }

    const includePriming = elements.includePriming ? elements.includePriming.checked : false;

    showLoading("Generating...");
    const apiKeyToSend = state.apiKey === "__ENV_KEY__" ? "" : state.apiKey;

    try {
        const response = await fetch("/api/ideas/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                api_key: apiKeyToSend,
                model_id: state.modelId,
                system_prompt: systemPrompt,
                user_prompt: userPrompt,
                outputs: state.outputs,
                step_num: stepNum,
                include_priming: includePriming
            })
        });

        const data = await response.json();

        if (response.ok) {
            const outputVar = OUTPUT_VAR_MAP[stepNum];
            const aliasVar = STEP_ALIAS_MAP[stepNum];
            state.outputs[outputVar] = data.output;
            state.outputs[aliasVar] = data.output;
            displayOutput(stepNum, data.output);
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
 */
function displayOutput(stepNum, output) {
    const section = document.getElementById(`idea-step${stepNum}-output-section`);
    const display = document.getElementById(`idea-step${stepNum}-output`);
    if (section && display) {
        section.style.display = "block";
        display.textContent = output;
    }
}

/**
 * Handle copy button click
 */
function handleCopy(stepNum) {
    const outputVar = OUTPUT_VAR_MAP[stepNum];
    const output = state.outputs[outputVar];
    if (!output) return;

    navigator.clipboard.writeText(output).then(() => {
        const btn = document.querySelector(`.idea-copy-btn[data-step="${stepNum}"]`);
        if (btn) {
            btn.classList.add("copied");
            setTimeout(() => btn.classList.remove("copied"), 1500);
        }
    }).catch(err => {
        console.error("Copy failed:", err);
        const ta = document.createElement("textarea");
        ta.value = output;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        const btn = document.querySelector(`.idea-copy-btn[data-step="${stepNum}"]`);
        if (btn) {
            btn.classList.add("copied");
            setTimeout(() => btn.classList.remove("copied"), 1500);
        }
    });
}

/**
 * Handle edit/done toggle button click
 */
function handleEditToggle(btn) {
    const editorId = btn.dataset.editor;
    const isEditing = btn.dataset.editing === "true";
    const editor = window.StoryEditor.getEditor(editorId);
    const wrapper = btn.closest(".editor-container").querySelector(".editor-wrapper");

    if (isEditing) {
        btn.textContent = "Edit";
        btn.dataset.editing = "false";
        btn.classList.add("editing-false");
        wrapper.classList.add("readonly");
        if (editor) editor.setOption("readOnly", true);
    } else {
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
 * Update variables status display for a step
 */
function updateVariablesStatus(stepNum) {
    const statusEl = document.getElementById(`idea-step${stepNum}-variables`);
    if (!statusEl) return;

    const userPrompt = window.StoryEditor.getEditorValue(`idea-step${stepNum}-user`);
    const pattern = /\b(?:(?:step\d+|priming|idea|postprocess)_output)\b/g;
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
    document.querySelectorAll(".idea-generate-btn").forEach(btn => {
        btn.disabled = !state.apiKey;
    });
}

function showLoading(text = "Loading...") {
    if (elements.loadingOverlay) {
        elements.loadingText.textContent = text;
        elements.loadingOverlay.style.display = "flex";
    }
}

function hideLoading() {
    if (elements.loadingOverlay) {
        elements.loadingOverlay.style.display = "none";
    }
}

/**
 * Save state to localStorage
 */
function saveState() {
    const saveData = {
        outputs: state.outputs,
        modelId: state.modelId
    };

    // Save prompts
    for (let i = 0; i <= 2; i++) {
        saveData[`step${i}_system`] = window.StoryEditor.getEditorValue(`idea-step${i}-system`);
        saveData[`step${i}_user`] = window.StoryEditor.getEditorValue(`idea-step${i}-user`);
    }

    if (elements.includePriming) {
        saveData.includePriming = elements.includePriming.checked;
    }

    localStorage.setItem("story-engine-ideas-state", JSON.stringify(saveData));
}

/**
 * Load state from localStorage
 */
function loadState() {
    try {
        const saved = localStorage.getItem("story-engine-ideas-state");
        if (!saved) return;

        const data = JSON.parse(saved);

        // Restore outputs
        if (data.outputs) {
            state.outputs = data.outputs;
            // Sync step aliases with named vars
            for (let i = 0; i <= 2; i++) {
                const outputVar = OUTPUT_VAR_MAP[i];
                const aliasVar = STEP_ALIAS_MAP[i];
                if (state.outputs[outputVar]) {
                    state.outputs[aliasVar] = state.outputs[outputVar];
                    displayOutput(i, state.outputs[outputVar]);
                }
            }
        }

        // Restore model selection
        if (data.modelId && elements.modelSelect) {
            elements.modelSelect.value = data.modelId;
            state.modelId = data.modelId;
        }

        // Restore prompts
        for (let i = 0; i <= 2; i++) {
            if (data[`step${i}_system`]) {
                window.StoryEditor.setEditorValue(`idea-step${i}-system`, data[`step${i}_system`]);
            }
            if (data[`step${i}_user`]) {
                window.StoryEditor.setEditorValue(`idea-step${i}-user`, data[`step${i}_user`]);
            }
            updateVariablesStatus(i);
        }

        if (elements.includePriming && data.includePriming !== undefined) {
            elements.includePriming.checked = data.includePriming;
        }
    } catch (error) {
        console.error("Error loading state:", error);
    }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", init);
