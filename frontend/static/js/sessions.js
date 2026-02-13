/**
 * Sessions page — lazy-loading tree browser for S3 session recordings.
 */
(function () {
    const tree = document.getElementById('session-tree');
    const detail = document.getElementById('session-detail');
    if (!tree) return; // S3 not configured — nothing to render

    const detailPath = document.getElementById('session-detail-path');
    const detailContent = document.getElementById('session-detail-content');
    const closeBtn = document.getElementById('session-detail-close');

    // Password gate — reuse the same key as the main app
    function getAuthHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const saved = localStorage.getItem('story-engine-auth');
        if (saved) headers['X-Auth'] = saved;
        return headers;
    }

    async function apiFetch(url) {
        const resp = await fetch(url, { headers: getAuthHeaders() });
        if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
        return resp.json();
    }

    function createLoadingNode() {
        const el = document.createElement('div');
        el.className = 'tree-item tree-loading';
        el.textContent = 'Loading\u2026';
        return el;
    }

    function createErrorNode(message) {
        const el = document.createElement('div');
        el.className = 'warning';
        el.style.margin = '4px 0';
        el.textContent = message;
        return el;
    }

    // ── Tree node helpers ──

    function createFolderNode(label, level, onExpand) {
        const item = document.createElement('div');
        item.className = 'tree-item tree-folder';

        const toggle = document.createElement('span');
        toggle.className = 'tree-toggle';
        toggle.textContent = '\u25B6'; // ▶

        const name = document.createElement('span');
        name.className = 'tree-folder-name';
        name.textContent = label;

        item.appendChild(toggle);
        item.appendChild(name);

        const children = document.createElement('div');
        children.className = 'tree-children';
        children.style.display = 'none';

        let loaded = false;

        item.addEventListener('click', async () => {
            if (!loaded) {
                loaded = true;
                const loader = createLoadingNode();
                children.appendChild(loader);
                children.style.display = '';
                toggle.textContent = '\u25BC';
                await onExpand(children);
                loader.remove();
                return;
            }
            const open = children.style.display !== 'none';
            children.style.display = open ? 'none' : '';
            toggle.textContent = open ? '\u25B6' : '\u25BC'; // ▶ / ▼
        });

        const wrapper = document.createElement('div');
        wrapper.appendChild(item);
        wrapper.appendChild(children);
        return wrapper;
    }

    function createFileNode(label, level, onClick) {
        const item = document.createElement('div');
        item.className = 'tree-item tree-file';

        const icon = document.createElement('span');
        icon.className = 'tree-toggle';
        icon.textContent = '\u2022'; // bullet

        const name = document.createElement('span');
        name.className = 'tree-file-name';
        name.textContent = label;

        item.appendChild(icon);
        item.appendChild(name);
        item.addEventListener('click', onClick);
        return item;
    }

    // ── Data loaders ──

    async function loadRoot() {
        const loader = createLoadingNode();
        tree.appendChild(loader);
        try {
            const data = await apiFetch('/api/sessions/tree');
            loader.remove();
            data.folders.forEach(folder => {
                const node = createFolderNode(folder, 0, (container) => loadDateFolders(container, folder));
                tree.appendChild(node);
            });
            if (data.folders.length === 0) {
                tree.textContent = 'No sessions recorded yet.';
            }
        } catch (err) {
            loader.remove();
            tree.appendChild(createErrorNode('Failed to load sessions: ' + err.message));
        }
    }

    async function loadDateFolders(container, page) {
        try {
            const data = await apiFetch('/api/sessions/tree/' + encodeURIComponent(page));
            data.dates.forEach(date => {
                const node = createFolderNode(date, 1, (c) => loadFiles(c, page, date));
                container.appendChild(node);
            });
        } catch (err) {
            container.appendChild(createErrorNode('Error: ' + err.message));
        }
    }

    async function loadFiles(container, page, date) {
        try {
            const data = await apiFetch('/api/sessions/tree/' + encodeURIComponent(page) + '/' + encodeURIComponent(date));
            data.files.forEach(file => {
                const node = createFileNode(file.filename, 2, () => loadFileContent(page, date, file.filename));
                container.appendChild(node);
            });
        } catch (err) {
            container.appendChild(createErrorNode('Error: ' + err.message));
        }
    }

    async function loadFileContent(page, date, filename) {
        detailPath.textContent = `sessions/${page}/${date}/${filename}`;
        detailContent.textContent = 'Loading\u2026';
        detail.style.display = '';
        try {
            const url = '/api/sessions/file/' + [page, date, filename].map(encodeURIComponent).join('/');
            const data = await apiFetch(url);
            let pretty;
            try {
                pretty = JSON.stringify(JSON.parse(data.content), null, 2);
            } catch {
                pretty = data.content;
            }
            detailPath.textContent = data.key;
            detailContent.textContent = pretty;
        } catch (err) {
            detailPath.textContent = 'Error';
            detailContent.textContent = err.message;
        }
    }

    // ── Init ──

    closeBtn.addEventListener('click', () => {
        detail.style.display = 'none';
    });

    let initialized = false;

    function init() {
        if (initialized) return;
        if (window.APP_CONFIG.hasPassword && !localStorage.getItem('story-engine-auth')) {
            setTimeout(init, 500);
            return;
        }
        initialized = true;
        loadRoot();
    }

    document.addEventListener('DOMContentLoaded', init);
    if (document.readyState !== 'loading') init();
})();
