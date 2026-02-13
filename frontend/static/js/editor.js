/**
 * Story Engine - CodeMirror Editor Setup
 * Custom mode for variable highlighting and autocomplete.
 * Supports configurable variable sets via setAvailableVariables().
 */

// All available variables for autocomplete (default for story page)
let AVAILABLE_VARIABLES = ["step0_output", "step1_output", "step2_output"];

// Build regex from variable list
let variableRegex = buildVariableRegex(AVAILABLE_VARIABLES);

/**
 * Build a regex that matches any of the given variable names
 * @param {string[]} vars - Variable names to match
 * @returns {RegExp}
 */
function buildVariableRegex(vars) {
    // Build alternation pattern from variable names
    const pattern = vars.map(v => v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|");
    return new RegExp(pattern);
}

/**
 * Set available variables for highlighting and autocomplete.
 * Call before initAllEditors() to configure for the current page.
 * @param {string[]} vars - Array of variable names
 */
function setAvailableVariables(vars) {
    AVAILABLE_VARIABLES = vars;
    variableRegex = buildVariableRegex(vars);
}

// Define custom mode for variable highlighting
CodeMirror.defineMode("story-variables", function() {
    return {
        token: function(stream) {
            // Check for any variable pattern
            if (stream.match(variableRegex)) {
                return "variable-highlight";
            }
            // Move forward one character if no match
            stream.next();
            return null;
        }
    };
});

/**
 * Determine autocomplete trigger prefix from available variables.
 * Returns common prefixes to trigger on (e.g., "step", "prim", "idea", "post").
 */
function getAutocompletePrefixes() {
    const prefixes = new Set();
    for (const v of AVAILABLE_VARIABLES) {
        // Use first 4 chars as trigger prefix
        prefixes.add(v.substring(0, 4).toLowerCase());
    }
    return [...prefixes];
}

/**
 * Custom hint function for variable autocomplete
 * @param {CodeMirror.Editor} editor
 * @returns {Object|null} Hint object or null
 */
function variableHint(editor) {
    const cursor = editor.getCursor();
    const line = editor.getLine(cursor.line);

    // Find the start of the current word
    let start = cursor.ch;
    while (start > 0 && /\w/.test(line.charAt(start - 1))) {
        start--;
    }

    const word = line.substring(start, cursor.ch).toLowerCase();

    if (word.length < 3) {
        return null;
    }

    // Filter variables that match the current input
    const matches = AVAILABLE_VARIABLES.filter(v =>
        v.toLowerCase().startsWith(word) && v.toLowerCase() !== word
    );

    if (matches.length === 0) {
        return null;
    }

    return {
        list: matches,
        from: CodeMirror.Pos(cursor.line, start),
        to: cursor
    };
}

// Register the hint helper
CodeMirror.registerHelper("hint", "story-variables", variableHint);

/**
 * Initialize a CodeMirror editor from a textarea
 * @param {HTMLTextAreaElement} textarea - The textarea element to replace
 * @param {Object} options - Additional options
 * @returns {CodeMirror.Editor} The CodeMirror instance
 */
function initEditor(textarea, options = {}) {
    const editor = CodeMirror.fromTextArea(textarea, {
        mode: "story-variables",
        lineWrapping: true,
        lineNumbers: false,
        viewportMargin: Infinity,
        extraKeys: {
            "Tab": function(cm) {
                // Try to show autocomplete, otherwise insert tab
                const hints = variableHint(cm);
                if (hints && hints.list.length > 0) {
                    cm.showHint({
                        hint: variableHint,
                        completeSingle: true
                    });
                } else {
                    cm.replaceSelection("  ");
                }
            },
            "Ctrl-Space": function(cm) {
                cm.showHint({ hint: variableHint });
            }
        },
        ...options
    });

    // Auto-trigger autocomplete on input
    editor.on("inputRead", function(cm, change) {
        if (change.text[0] && /\w/.test(change.text[0])) {
            const cursor = cm.getCursor();
            const line = cm.getLine(cursor.line);

            // Find current word
            let start = cursor.ch;
            while (start > 0 && /\w/.test(line.charAt(start - 1))) {
                start--;
            }
            const word = line.substring(start, cursor.ch).toLowerCase();

            // Show hints if typing matches any autocomplete prefix
            const prefixes = getAutocompletePrefixes();
            if (word.length >= 4 && prefixes.some(p => word.startsWith(p))) {
                cm.showHint({
                    hint: variableHint,
                    completeSingle: false
                });
            }
        }
    });

    // Store reference to original textarea for form submission
    editor.originalTextarea = textarea;

    return editor;
}

/**
 * Get all editors on the page
 * @returns {Object} Map of editor IDs to CodeMirror instances
 */
const editors = {};

/**
 * Initialize all editors on the page
 */
function initAllEditors() {
    const textareas = document.querySelectorAll("textarea.code-editor");

    textareas.forEach(textarea => {
        const id = textarea.id;
        if (id && !editors[id]) {
            editors[id] = initEditor(textarea);

            // Sync content back to textarea on change
            editors[id].on("change", function(cm) {
                cm.save();
                // Trigger custom event for app.js to listen to
                textarea.dispatchEvent(new CustomEvent("editor-change", {
                    detail: { value: cm.getValue() }
                }));
            });
        }
    });
}

/**
 * Get editor by ID
 * @param {string} id - The textarea ID
 * @returns {CodeMirror.Editor|null} The editor instance or null
 */
function getEditor(id) {
    return editors[id] || null;
}

/**
 * Get editor value by ID
 * @param {string} id - The textarea ID
 * @returns {string} The editor content
 */
function getEditorValue(id) {
    const editor = editors[id];
    if (editor) {
        return editor.getValue();
    }
    // Fallback: get value from textarea directly if editor not initialized
    const textarea = document.getElementById(id);
    return textarea ? textarea.value : "";
}

/**
 * Set editor value by ID
 * @param {string} id - The textarea ID
 * @param {string} value - The new content
 */
function setEditorValue(id, value) {
    const editor = editors[id];
    if (editor) {
        editor.setValue(value);
    }
}

// Export functions for use in app.js / ideas.js
window.StoryEditor = {
    initAllEditors,
    getEditor,
    getEditorValue,
    setEditorValue,
    setAvailableVariables,
    editors
};
