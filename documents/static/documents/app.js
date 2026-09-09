let currentSubject = null;
let currentFolder = 'all';
let searchQuery = '';
let searchDebounceTimer = null;
let selectedFiles = [];
let subjectsList = [];
let isAdmin = false;

// Presentation Viewer State
let currentSlides = [];
let activeSlideIndex = 0;

// Preview & Gemini AI Tutor State
let currentPreviewDocId = null;
let currentPreviewDocTitle = null;
let activeAiFileId = null;
let activeAiDocTitle = null;
let aiIsLoading = false;

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadSubjectsData();
    setupDropzone();
    setupKeyboardNav();
    checkAiStatus();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('subject_bank_theme') || 'light';
    setTheme(savedTheme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next = current === 'light' ? 'dark' : 'light';
    setTheme(next);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('subject_bank_theme', theme);
    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');
    if (icon && label) {
        if (theme === 'light') {
            icon.textContent = '🌙';
            label.textContent = 'Dark';
        } else {
            icon.textContent = '☀️';
            label.textContent = 'Light';
        }
    }
}

// Toast Helper
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const msg = document.getElementById('toastMsg');
    const icon = document.getElementById('toastIcon');

    msg.textContent = message;
    toast.className = `toast ${type} show`;
    icon.textContent = type === 'success' ? '✅' : '⚠️';

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
}

// Fetch Initial Subjects & Stats
async function loadSubjectsData() {
    try {
        const res = await fetch('/api/subjects/');
        const data = await res.json();
        if (data.success) {
            subjectsList = data.subjects || [];
            isAdmin = data.is_admin || false;
            updateStatsBar(data.stats);
            updateSubjectDropdowns();
            
            if (currentSubject) {
                openSubjectView(currentSubject, currentFolder);
            } else {
                renderSubjectsGrid();
            }
        }
    } catch (err) {
        console.error("Error loading subjects:", err);
    }
}

function updateStatsBar(stats) {
    if (!stats) return;
    const totalDocsEl = document.getElementById('statTotalDocs');
    const totalSizeEl = document.getElementById('statTotalSize');
    const totalSubjEl = document.getElementById('statTotalSubjects');
    
    if (totalDocsEl) totalDocsEl.textContent = stats.total_docs || 0;
    if (totalSizeEl) totalSizeEl.textContent = stats.total_size_formatted || '0 B';
    if (totalSubjEl) totalSubjEl.textContent = stats.total_subjects || (subjectsList.length || 0);
}

function updateSubjectDropdowns() {
    const uploadSubjSelect = document.getElementById('docSubjectSelect');
    const folderSubjSelect = document.getElementById('folderSubjectSelect');
    
    if (uploadSubjSelect) {
        uploadSubjSelect.innerHTML = '<option value="">-- Select Subject --</option>';
        subjectsList.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.name;
            opt.textContent = s.name;
            uploadSubjSelect.appendChild(opt);
        });
    }

    if (folderSubjSelect) {
        folderSubjSelect.innerHTML = '<option value="">-- Select Subject --</option>';
        subjectsList.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.name;
            opt.textContent = s.name;
            folderSubjSelect.appendChild(opt);
        });
    }
}

function onUploadSubjectChange() {
    const subjName = document.getElementById('docSubjectSelect').value;
    const folderSelect = document.getElementById('docFolderSelect');
    folderSelect.innerHTML = '<option value="General">General</option>';
    
    const subject = subjectsList.find(s => s.name.toLowerCase() === subjName.toLowerCase());
    if (subject && subject.folders) {
        subject.folders.forEach(f => {
            if (f.toLowerCase() !== 'general') {
                const opt = document.createElement('option');
                opt.value = f;
                opt.textContent = f;
                folderSelect.appendChild(opt);
            }
        });
    }
}

// ================= RENDER SUBJECTS (TOP LEVEL) =================
function showAllSubjectsView() {
    currentSubject = null;
    currentFolder = 'all';
    
    document.getElementById('breadcrumbContainer').innerHTML = `
        <div class="breadcrumb-trail">
            <span class="breadcrumb-current">📚 All Subjects</span>
        </div>
    `;

    document.getElementById('subjectDetailSection').style.display = 'none';
    document.getElementById('allSubjectsSection').style.display = 'block';
    
    renderSubjectsGrid();
}

function renderSubjectsGrid() {
    const grid = document.getElementById('subjectsGrid');
    grid.innerHTML = '';

    const query = searchQuery.toLowerCase().trim();
    const filtered = subjectsList.filter(s => {
        if (!query) return true;
        return s.name.toLowerCase().includes(query) || (s.description || '').toLowerCase().includes(query);
    });

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📂</div>
                <h3>No subjects found</h3>
                <p>No subjects match your search query.</p>
                ${isAdmin ? `<button class="btn btn-primary" onclick="openCreateSubjectModal()">+ Add New Subject</button>` : ''}
            </div>
        `;
        return;
    }

    filtered.forEach(s => {
        const card = document.createElement('div');
        card.className = 'subject-card';
        card.onmouseenter = () => prefetchSubject(s.name);
        card.ontouchstart = () => prefetchSubject(s.name);
        card.onclick = (e) => {
            if (e.target.closest('.btn-delete-subject')) return;
            openSubjectView(s.name);
        };

        const foldersCount = (s.folders || []).length;
        const deleteBtnHtml = isAdmin ? `
            <button class="btn btn-sm btn-danger btn-delete-subject" onclick="deleteSubject('${escapeJs(s.name)}', event)" title="Delete Subject">
                🗑️
            </button>
        ` : '';

        card.innerHTML = `
            <div>
                <div class="subject-header">
                    <div class="subject-icon-box">📁</div>
                    <div style="flex: 1; overflow: hidden;">
                        <h3 class="subject-name">${escapeHtml(s.name)}</h3>
                        <p class="subject-desc">${escapeHtml(s.description || 'Study materials, lectures, and resources.')}</p>
                    </div>
                </div>

                <div class="subject-meta-tags">
                    <span class="folder-badge">📂 ${foldersCount} Folders</span>
                    <span class="file-count-badge">📄 ${s.file_count || 0} Documents</span>
                    <span class="file-count-badge">💾 ${s.total_size_formatted || '0 B'}</span>
                </div>
            </div>

            <div class="subject-footer">
                <button class="btn btn-sm btn-primary">
                    Open Folders →
                </button>
                ${deleteBtnHtml}
            </div>
        `;
        grid.appendChild(card);
    });
}

// ================= SUBJECT & FOLDER DETAIL VIEW =================
async function openSubjectView(subjectName, folderName = 'all') {
    currentSubject = subjectName;
    currentFolder = folderName;

    const subject = subjectsList.find(s => s.name.toLowerCase() === subjectName.toLowerCase());
    const folders = subject ? (subject.folders || ['General']) : ['General'];

    document.getElementById('allSubjectsSection').style.display = 'none';
    const detailSec = document.getElementById('subjectDetailSection');
    detailSec.style.display = 'block';

    // Update Breadcrumbs
    document.getElementById('breadcrumbContainer').innerHTML = `
        <div class="breadcrumb-trail">
            <span class="breadcrumb-item" onclick="showAllSubjectsView()">📚 All Subjects</span>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">📁 ${escapeHtml(subjectName)}</span>
        </div>
        <div style="display: flex; gap: 8px;">
            <button class="btn btn-sm btn-secondary" onclick="showAllSubjectsView()">← Back to Subjects</button>
            ${isAdmin ? `<button class="btn btn-sm btn-primary" onclick="openCreateFolderModalFor('${escapeJs(subjectName)}')">+ New Folder</button>` : ''}
            ${isAdmin ? `<button class="btn btn-sm btn-primary" onclick="openUploadModalFor('${escapeJs(subjectName)}', '${escapeJs(currentFolder)}')">+ Upload to Subject</button>` : ''}
        </div>
    `;

    // Render Folder Pills
    const pillsContainer = document.getElementById('folderPillsContainer');
    let pillsHtml = `
        <button class="folder-pill ${currentFolder === 'all' ? 'active' : ''}" onclick="selectFolder('all', this)">
            📂 All Documents
        </button>
    `;

    folders.forEach(f => {
        const isActive = currentFolder.toLowerCase() === f.toLowerCase();
        const deleteFolderBtn = (isAdmin && f.toLowerCase() !== 'general') ? `
            <span onclick="deleteFolder('${escapeJs(subjectName)}', '${escapeJs(f)}', event)" title="Delete folder" style="margin-left: 6px; cursor: pointer; opacity: 0.7;">&times;</span>
        ` : '';

        pillsHtml += `
            <button class="folder-pill ${isActive ? 'active' : ''}" onclick="selectFolder('${escapeJs(f)}', this)">
                📁 ${escapeHtml(f)} ${deleteFolderBtn}
            </button>
        `;
    });

    pillsContainer.innerHTML = pillsHtml;

    // Load and render documents
    fetchSubjectDocuments();
}

function selectFolder(folderName, btn) {
    currentFolder = folderName;
    document.querySelectorAll('.folder-pills .folder-pill').forEach(p => p.classList.remove('active'));
    if (btn) btn.classList.add('active');
    fetchSubjectDocuments();
}

// Client-Side In-Memory SWR Cache for Instant (0ms) Navigation
const clientDocCache = new Map();

function getDocCacheKey(subject, folder, query) {
    return `${(subject || '').toLowerCase()}::${(folder || 'all').toLowerCase()}::${(query || '').toLowerCase()}`;
}

function renderDocumentsSkeleton() {
    const grid = document.getElementById('documentsGrid');
    if (!grid) return;
    let html = '';
    for (let i = 0; i < 6; i++) {
        html += `
            <div class="skeleton-card skeleton-shimmer">
                <div style="display: flex; gap: 14px; margin-bottom: 14px;">
                    <div class="skeleton-box" style="width: 44px; height: 44px; border-radius: 10px;"></div>
                    <div style="flex: 1;">
                        <div class="skeleton-box skeleton-line title" style="width: 80%;"></div>
                        <div class="skeleton-box skeleton-line subtitle" style="width: 50%;"></div>
                    </div>
                </div>
                <div class="skeleton-meta" style="margin-top: 10px; padding-top: 10px;">
                    <div class="skeleton-box skeleton-badge" style="width: 60px;"></div>
                    <div class="skeleton-box skeleton-badge" style="width: 50px;"></div>
                </div>
            </div>
        `;
    }
    grid.innerHTML = html;
}

function prefetchSubject(subjectName) {
    if (!subjectName) return;
    const cacheKey = getDocCacheKey(subjectName, 'all', '');
    if (clientDocCache.has(cacheKey)) return;

    const params = new URLSearchParams();
    params.append('subject', subjectName);
    
    // Background fetch with priority hint
    fetch(`/api/documents/?${params.toString()}`, { priority: 'low' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                clientDocCache.set(cacheKey, { data: data.documents, timestamp: Date.now() });
            }
        })
        .catch(() => {});
}

async function fetchSubjectDocuments(allowCache = true) {
    const cacheKey = getDocCacheKey(currentSubject, currentFolder, searchQuery);

    // Instant SWR: render from memory in 0ms if previously loaded or prefetched
    if (allowCache && clientDocCache.has(cacheKey)) {
        const cached = clientDocCache.get(cacheKey);
        renderDocumentsGrid(cached.data);
        // If cache is fresh (< 20 seconds), skip network call completely
        if (Date.now() - cached.timestamp < 20000) {
            return;
        }
    } else {
        renderDocumentsSkeleton();
    }

    const params = new URLSearchParams();
    if (currentSubject) params.append('subject', currentSubject);
    if (currentFolder && currentFolder !== 'all') params.append('folder', currentFolder);
    if (searchQuery) params.append('q', searchQuery);

    try {
        const res = await fetch(`/api/documents/?${params.toString()}`);
        const data = await res.json();
        if (data.success) {
            clientDocCache.set(cacheKey, { data: data.documents, timestamp: Date.now() });
            renderDocumentsGrid(data.documents);
        }
    } catch (err) {
        console.error("Error fetching documents:", err);
    }
}

function renderDocumentsGrid(docs) {
    const grid = document.getElementById('documentsGrid');
    grid.innerHTML = '';

    if (!docs || docs.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📭</div>
                <h3>No documents in this folder</h3>
                <p>No materials have been added here yet.</p>
                ${isAdmin ? `<button class="btn btn-primary" onclick="openUploadModalFor('${escapeJs(currentSubject)}', '${escapeJs(currentFolder)}')">Upload First Document</button>` : ''}
            </div>
        `;
        return;
    }

    docs.forEach(doc => {
        const card = document.createElement('div');
        card.className = 'doc-card';

        const catIcons = {
            pdf: '📄',
            presentation: '📊',
            document: '📝',
            image: '🖼️',
            other: '📁'
        };
        const icon = catIcons[doc.category] || '📁';

        const deleteBtn = isAdmin ? `
            <button class="btn btn-sm btn-danger" onclick="deleteDocument('${doc.id}', '${escapeJs(doc.title)}')" title="Delete File">
                🗑️
            </button>
        ` : '';

        card.innerHTML = `
            <div>
                <div class="card-top">
                    <div class="badge-type ${doc.category}">
                        ${icon}
                    </div>
                    <div class="card-header-info">
                        <h4 class="card-title" title="${escapeHtml(doc.title)}">${escapeHtml(doc.title)}</h4>
                        <div class="card-filename" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
                    </div>
                </div>

                <div class="card-meta">
                    <span class="subject-pill">📁 ${escapeHtml(doc.folder || 'General')}</span>
                    <span>${escapeHtml(doc.file_size_formatted)}</span>
                </div>
            </div>

            <div>
                <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 14px;">
                    Stored ${escapeHtml(doc.upload_date)}
                </div>
                <div class="card-actions">
                    <button class="btn btn-sm btn-primary" onclick="openPreview('${doc.id}', '${escapeJs(doc.title)}')">
                        👁️ View Document
                    </button>
                    <a href="/documents/${doc.id}/download/" class="btn btn-sm btn-secondary" download title="Download file">
                        ⬇️
                    </a>
                    ${deleteBtn}
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

// Search Handler
function handleSearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        searchQuery = document.getElementById('searchInput').value.trim();
        if (currentSubject) {
            fetchSubjectDocuments();
        } else {
            renderSubjectsGrid();
        }
    }, 250);
}

// ================= ADMIN ACTIONS =================

// Create Subject
function openCreateSubjectModal() {
    document.getElementById('newSubjectName').value = '';
    document.getElementById('newSubjectDesc').value = '';
    document.getElementById('createSubjectModal').classList.add('active');
}

function closeCreateSubjectModal() {
    document.getElementById('createSubjectModal').classList.remove('active');
}

async function handleCreateSubjectSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('newSubjectName').value.trim();
    const desc = document.getElementById('newSubjectDesc').value.trim();

    if (!name) {
        showToast("Please enter a subject name", "error");
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', desc);

    try {
        const res = await fetch('/api/subjects/create/', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message);
            closeCreateSubjectModal();
            loadSubjectsData();
        } else {
            showToast(data.error || "Failed to create subject", "error");
        }
    } catch (err) {
        showToast("Error creating subject", "error");
    }
}

async function deleteSubject(subjectName, event) {
    if (event) event.stopPropagation();
    if (!confirm(`Are you sure you want to delete "${subjectName}" and ALL of its folders and documents from MongoDB?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/subjects/${encodeURIComponent(subjectName)}/delete/`, {
            method: 'POST'
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message);
            if (currentSubject === subjectName) {
                showAllSubjectsView();
            }
            loadSubjectsData();
        } else {
            showToast(data.error || "Failed to delete subject", "error");
        }
    } catch (err) {
        showToast("Error deleting subject", "error");
    }
}

// Create Folder
function openCreateFolderModal() {
    openCreateFolderModalFor(currentSubject || '');
}

function openCreateFolderModalFor(subjName) {
    const select = document.getElementById('folderSubjectSelect');
    if (subjName) select.value = subjName;
    document.getElementById('newFolderName').value = '';
    document.getElementById('createFolderModal').classList.add('active');
}

function closeCreateFolderModal() {
    document.getElementById('createFolderModal').classList.remove('active');
}

async function handleCreateFolderSubmit(event) {
    event.preventDefault();
    const subject = document.getElementById('folderSubjectSelect').value.trim();
    const folderName = document.getElementById('newFolderName').value.trim();

    if (!subject || !folderName) {
        showToast("Please select a subject and enter a folder name", "error");
        return;
    }

    const formData = new FormData();
    formData.append('subject', subject);
    formData.append('folder_name', folderName);

    try {
        const res = await fetch('/api/folders/create/', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message);
            closeCreateFolderModal();
            await loadSubjectsData();
            if (currentSubject && currentSubject.toLowerCase() === subject.toLowerCase()) {
                openSubjectView(subject, folderName);
            }
        } else {
            showToast(data.error || "Failed to create folder", "error");
        }
    } catch (err) {
        showToast("Error creating folder", "error");
    }
}

async function deleteFolder(subjectName, folderName, event) {
    if (event) event.stopPropagation();
    if (!confirm(`Are you sure you want to delete folder "${folderName}" and all its files?`)) {
        return;
    }

    const formData = new FormData();
    formData.append('subject', subjectName);
    formData.append('folder_name', folderName);

    try {
        const res = await fetch('/api/folders/delete/', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message);
            await loadSubjectsData();
            openSubjectView(subjectName, 'all');
        } else {
            showToast(data.error || "Failed to delete folder", "error");
        }
    } catch (err) {
        showToast("Error deleting folder", "error");
    }
}

// Upload Documents
function openUploadModal() {
    openUploadModalFor(currentSubject || '', currentFolder || 'General');
}

function openUploadModalFor(subjName, folderName) {
    clearSelectedFiles();
    document.getElementById('docTitle').value = '';
    document.getElementById('docTags').value = '';
    
    const subjSelect = document.getElementById('docSubjectSelect');
    if (subjName) {
        subjSelect.value = subjName;
        onUploadSubjectChange();
        if (folderName && folderName !== 'all') {
            document.getElementById('docFolderSelect').value = folderName;
        }
    }
    document.getElementById('uploadModal').classList.add('active');
}

function closeUploadModal() {
    document.getElementById('uploadModal').classList.remove('active');
    clearSelectedFiles();
}

function setupDropzone() {
    const dropzone = document.getElementById('dropzone');
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            addSelectedFiles(Array.from(files));
        }
    });
}

function handleFilesSelected(event) {
    if (event.target.files && event.target.files.length > 0) {
        addSelectedFiles(Array.from(event.target.files));
        event.target.value = ''; // Reset so the same file can be re-selected if deleted
    }
}

function getCategoryIcon(filename) {
    const fn = (filename || '').toLowerCase();
    if (fn.endsWith('.pdf')) return '📄';
    if (fn.endsWith('.pptx') || fn.endsWith('.ppt')) return '📊';
    if (fn.endsWith('.docx') || fn.endsWith('.doc')) return '📝';
    if (fn.endsWith('.png') || fn.endsWith('.jpg') || fn.endsWith('.jpeg') || fn.endsWith('.webp') || fn.endsWith('.gif')) return '🖼️';
    return '📁';
}

function addSelectedFiles(newFiles) {
    for (const f of newFiles) {
        // Prevent exact duplicates
        const exists = selectedFiles.some(existing => existing.name === f.name && existing.size === f.size);
        if (!exists) {
            selectedFiles.push(f);
        }
    }
    renderSelectedFilesList();
}

function renderSelectedFilesList() {
    const container = document.getElementById('filesListContainer');
    const scrollArea = document.getElementById('filesListScroll');
    const summary = document.getElementById('selectedFilesSummary');
    const submitBtn = document.getElementById('btnUploadSubmit');
    const titleInput = document.getElementById('docTitle');
    const titleHint = document.getElementById('titleHint');

    if (selectedFiles.length === 0) {
        if (container) container.style.display = 'none';
        if (submitBtn) submitBtn.textContent = 'Save Directly to MongoDB';
        if (titleHint) titleHint.textContent = '(optional - defaults to original filenames)';
        return;
    }

    if (container) container.style.display = 'block';

    const totalBytes = selectedFiles.reduce((acc, f) => acc + f.size, 0);
    const countText = `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} selected (${formatBytes(totalBytes)} total)`;
    if (summary) summary.textContent = countText;

    if (submitBtn) {
        submitBtn.textContent = `Save ${selectedFiles.length} File${selectedFiles.length > 1 ? 's' : ''} to MongoDB`;
    }

    if (selectedFiles.length === 1) {
        if (!titleInput.value) {
            titleInput.value = selectedFiles[0].name.replace(/\.[^/.]+$/, "");
        }
        if (titleHint) titleHint.textContent = '(custom title or leave blank for filename)';
    } else {
        if (titleHint) titleHint.textContent = '(optional prefix: each file keeps its name)';
    }

    if (scrollArea) {
        scrollArea.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const row = document.createElement('div');
            row.className = 'upload-file-item';
            row.innerHTML = `
                <div class="upload-file-left">
                    <span class="upload-file-icon">${getCategoryIcon(file.name)}</span>
                    <div class="upload-file-meta">
                        <div class="upload-file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
                        <div class="upload-file-size">${formatBytes(file.size)}</div>
                    </div>
                </div>
                <button type="button" class="upload-file-remove" onclick="removeSelectedFile(${index})" title="Remove file">&times;</button>
            `;
            scrollArea.appendChild(row);
        });
    }
}

function removeSelectedFile(index) {
    selectedFiles.splice(index, 1);
    renderSelectedFilesList();
}

function clearSelectedFiles() {
    selectedFiles = [];
    renderSelectedFilesList();
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    const progressContainer = document.getElementById('uploadProgressContainer');
    if (progressContainer) progressContainer.style.display = 'none';
    const progressBar = document.getElementById('uploadProgressBar');
    if (progressBar) progressBar.style.width = '0%';
}

async function handleUploadSubmit(event) {
    event.preventDefault();
    if (selectedFiles.length === 0) {
        showToast("Please select at least one file to upload", "error");
        return;
    }

    const title = document.getElementById('docTitle').value.trim();
    const subject = document.getElementById('docSubjectSelect').value.trim();
    const folder = document.getElementById('docFolderSelect').value.trim();
    const tags = document.getElementById('docTags').value.trim();

    if (!subject) {
        showToast("Please select a subject", "error");
        return;
    }

    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });
    // Also include 'file' for single-file backwards compatibility
    if (selectedFiles.length > 0) {
        formData.append('file', selectedFiles[0]);
    }
    formData.append('title', title);
    formData.append('subject', subject);
    formData.append('folder', folder || 'General');
    formData.append('tags', tags);

    const submitBtn = document.getElementById('btnUploadSubmit');
    const progressContainer = document.getElementById('uploadProgressContainer');
    const progressBar = document.getElementById('uploadProgressBar');
    const progressPercent = document.getElementById('uploadProgressPercent');
    const progressText = document.getElementById('uploadProgressText');

    submitBtn.disabled = true;
    submitBtn.textContent = `Uploading ${selectedFiles.length} file(s)...`;
    if (progressContainer) progressContainer.style.display = 'block';
    if (progressBar) progressBar.style.width = '10%';
    if (progressPercent) progressPercent.textContent = '10%';
    if (progressText) progressText.textContent = `Uploading ${selectedFiles.length} file(s) to MongoDB...`;

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/documents/upload/');

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percent = Math.min(95, Math.round((e.loaded / e.total) * 100));
            if (progressBar) progressBar.style.width = percent + '%';
            if (progressPercent) progressPercent.textContent = percent + '%';
            if (progressText) progressText.textContent = `Uploading ${selectedFiles.length} file(s)... ${percent}%`;
        }
    };

    xhr.onload = async () => {
        if (progressBar) progressBar.style.width = '100%';
        if (progressPercent) progressPercent.textContent = '100%';

        if (xhr.status >= 200 && xhr.status < 300) {
            try {
                const result = JSON.parse(xhr.responseText);
                if (result.success) {
                    clientDocCache.clear();
                    showToast(result.message || `Successfully stored ${selectedFiles.length} file(s) in MongoDB!`);
                    closeUploadModal();
                    await loadSubjectsData();
                    openSubjectView(subject, folder || 'all');
                } else {
                    showToast(result.error || "Failed to upload files", "error");
                }
            } catch (err) {
                showToast("Server returned an invalid response", "error");
            }
        } else {
            showToast("Error uploading files to database", "error");
        }
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save Directly to MongoDB';
    };

    xhr.onerror = () => {
        showToast("Network error uploading files", "error");
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save Directly to MongoDB';
    };

    xhr.send(formData);
}

async function deleteDocument(id, title) {
    if (!confirm(`Are you sure you want to delete "${title}" from MongoDB?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/documents/${id}/delete/`, {
            method: 'POST'
        });
        const result = await res.json();
        if (result.success) {
            clientDocCache.clear();
            showToast("Document deleted from MongoDB!");
            loadSubjectsData();
            fetchSubjectDocuments(false);
        } else {
            showToast(result.error || "Failed to delete", "error");
        }
    } catch (err) {
        showToast("Error deleting document", "error");
    }
}

// ================= IN-BROWSER LIVE PREVIEW (NO DOWNLOAD NEEDED) =================
async function openPreview(id, title) {
    currentPreviewDocId = id;
    currentPreviewDocTitle = title;
    
    const modal = document.getElementById('previewModal');
    const titleEl = document.getElementById('previewModalTitle');
    const area = document.getElementById('previewContentArea');
    const downloadBtn = document.getElementById('previewDownloadBtn');
    const badge = document.getElementById('previewBadge');

    titleEl.textContent = title;
    downloadBtn.href = `/documents/${id}/download/`;
    
    area.innerHTML = `
        <div class="loading-view">
            <div class="spinner"></div>
            <p>Streaming directly from MongoDB GridFS...</p>
        </div>
    `;
    modal.classList.add('active');

    try {
        const res = await fetch(`/api/documents/${id}/preview-content/`);
        const data = await res.json();

        if (!data.success && data.type === 'unsupported') {
            renderUnsupportedView(data);
            return;
        }

        badge.textContent = data.type.toUpperCase();
        badge.className = `preview-badge badge-type ${data.type}`;

        if (data.type === 'pdf') {
            area.innerHTML = `<iframe class="preview-iframe" src="${data.url}#view=FitH"></iframe>`;
        } else if (data.type === 'image') {
            area.innerHTML = `
                <div class="image-viewer-container">
                    <img class="preview-image" src="${data.url}" alt="${escapeHtml(title)}">
                </div>
            `;
        } else if (data.type === 'docx') {
            renderDocxView(data.html, data.title);
        } else if (data.type === 'pptx') {
            renderPptxView(data.slides);
        } else if (data.type === 'text') {
            renderTextView(data.text);
        } else {
            renderUnsupportedView(data);
        }
    } catch (err) {
        console.error("Preview error:", err);
        area.innerHTML = `
            <div class="loading-view" style="color: #ef4444;">
                <div style="font-size: 40px; margin-bottom: 8px;">⚠️</div>
                <p>Failed to load preview for this document.</p>
                <a href="/documents/${id}/download/" class="btn btn-primary" style="margin-top: 10px;">⬇️ Download File</a>
            </div>
        `;
    }
}

// Render Word DOCX inside PURE WHITE DOCUMENT SHEET
function renderDocxView(htmlContent, title) {
    const area = document.getElementById('previewContentArea');
    area.innerHTML = `
        <div class="docx-scroll-container">
            <article class="docx-paper">
                ${htmlContent || `<p><em>Empty Word document.</em></p>`}
            </article>
        </div>
    `;
}

// Render PowerPoint Interactive Presentation Slider
function renderPptxView(slides) {
    const area = document.getElementById('previewContentArea');
    currentSlides = slides || [];
    activeSlideIndex = 0;

    if (currentSlides.length === 0) {
        area.innerHTML = `
            <div class="loading-view">
                <p>No slides found in this presentation.</p>
            </div>
        `;
        return;
    }

    const thumbnailsHtml = currentSlides.map((s, idx) => `
        <div class="pptx-thumb-card ${idx === 0 ? 'active' : ''}" onclick="goToSlide(${idx})">
            <div class="thumb-num">Slide ${s.slide_number}</div>
            <div class="thumb-title">${escapeHtml(s.title)}</div>
        </div>
    `).join('');

    area.innerHTML = `
        <div class="pptx-viewer">
            <!-- Left Thumbnails Sidebar -->
            <div class="pptx-sidebar" id="pptxSidebar">
                ${thumbnailsHtml}
            </div>

            <!-- Slide Display Canvas & Controls -->
            <div class="pptx-main">
                <div class="pptx-slide-canvas-wrapper">
                    <div class="pptx-slide-card" id="pptxSlideCard">
                        <!-- Active slide injected here -->
                    </div>
                </div>

                <!-- Bottom Controls Bar -->
                <div class="pptx-controls-bar">
                    <button class="btn btn-sm btn-secondary" onclick="prevSlide()" id="btnPrevSlide">
                        ◀ Previous
                    </button>
                    <span id="slideCounterText" style="font-size: 0.9rem; font-weight: 600; color: #cbd5e1;">
                        Slide 1 of ${currentSlides.length}
                    </span>
                    <button class="btn btn-sm btn-primary" onclick="nextSlide()" id="btnNextSlide">
                        Next ▶
                    </button>
                </div>
            </div>
        </div>
    `;

    displayCurrentSlide();
}

function displayCurrentSlide() {
    const slide = currentSlides[activeSlideIndex];
    const card = document.getElementById('pptxSlideCard');
    if (!slide || !card) return;

    let bodyHtml = '';
    if (slide.content && slide.content.length > 0) {
        slide.content.forEach(paragraphGroup => {
            bodyHtml += `<ul class="slide-body-list">`;
            paragraphGroup.forEach(p => {
                const levelClass = p.level > 0 ? `level-${p.level}` : '';
                bodyHtml += `<li class="${levelClass}">${escapeHtml(p.text)}</li>`;
            });
            bodyHtml += `</ul>`;
        });
    }

    let tablesHtml = '';
    if (slide.tables && slide.tables.length > 0) {
        slide.tables.forEach(tbl => {
            tablesHtml += `<table style="width:100%; border-collapse: collapse; margin-top: 16px; border: 1px solid #cbd5e1;">`;
            tbl.forEach((row, rIdx) => {
                tablesHtml += `<tr>`;
                row.forEach(cell => {
                    const tag = rIdx === 0 ? 'th' : 'td';
                    tablesHtml += `<${tag} style="padding: 8px 12px; border: 1px solid #cbd5e1; background: ${rIdx === 0 ? '#f1f5f9' : '#ffffff'}; color: #0f172a;">${escapeHtml(cell)}</${tag}>`;
                });
                tablesHtml += `</tr>`;
            });
            tablesHtml += `</table>`;
        });
    }

    let imagesHtml = '';
    if (slide.images && slide.images.length > 0) {
        imagesHtml = `<div class="slide-images-row">`;
        slide.images.forEach(imgSrc => {
            imagesHtml += `<img src="${imgSrc}" class="slide-img" alt="Slide Image">`;
        });
        imagesHtml += `</div>`;
    }

    card.innerHTML = `
        <div class="slide-title-text">${escapeHtml(slide.title)}</div>
        <div style="flex: 1;">
            ${bodyHtml}
            ${tablesHtml}
            ${imagesHtml}
        </div>
    `;

    document.getElementById('slideCounterText').textContent = `Slide ${activeSlideIndex + 1} of ${currentSlides.length}`;
    
    document.querySelectorAll('.pptx-thumb-card').forEach((el, idx) => {
        if (idx === activeSlideIndex) {
            el.classList.add('active');
            el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            el.classList.remove('active');
        }
    });

    document.getElementById('btnPrevSlide').disabled = activeSlideIndex === 0;
    document.getElementById('btnNextSlide').disabled = activeSlideIndex === currentSlides.length - 1;
}

function nextSlide() {
    if (activeSlideIndex < currentSlides.length - 1) {
        activeSlideIndex++;
        displayCurrentSlide();
    }
}

function prevSlide() {
    if (activeSlideIndex > 0) {
        activeSlideIndex--;
        displayCurrentSlide();
    }
}

function goToSlide(idx) {
    if (idx >= 0 && idx < currentSlides.length) {
        activeSlideIndex = idx;
        displayCurrentSlide();
    }
}

function setupKeyboardNav() {
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById('previewModal');
        if (modal && modal.classList.contains('active')) {
            if (e.key === 'ArrowRight' || e.key === ' ') {
                nextSlide();
            } else if (e.key === 'ArrowLeft') {
                prevSlide();
            } else if (e.key === 'Escape') {
                closePreviewModal();
            }
        }
    });
}

function renderTextView(textContent) {
    const area = document.getElementById('previewContentArea');
    area.innerHTML = `
        <div class="text-viewer-box">
            <pre class="text-code-content">${escapeHtml(textContent)}</pre>
        </div>
    `;
}

function renderUnsupportedView(data) {
    const area = document.getElementById('previewContentArea');
    area.innerHTML = `
        <div class="loading-view" style="padding: 40px; text-align: center;">
            <div style="font-size: 56px; margin-bottom: 12px;">📁</div>
            <h3 style="color: var(--text-main); font-size: 1.2rem; margin-bottom: 8px;">${escapeHtml(data.title || 'Document')}</h3>
            <p style="color: var(--text-muted); max-width: 480px; margin-bottom: 20px;">${escapeHtml(data.error || 'This legacy format cannot be parsed directly in the browser.')}</p>
            <a href="${data.download_url}" class="btn btn-primary" download>
                ⬇️ Download File
            </a>
        </div>
    `;
}

function closePreviewModal() {
    const modal = document.getElementById('previewModal');
    modal.classList.remove('active');
    document.getElementById('previewContentArea').innerHTML = '';
    currentSlides = [];
}

// Helpers
function formatBytes(bytes, decimals = 2) {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeJs(str) {
    if (!str) return '';
    return str.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// ================= GEMINI AI ACADEMIC TUTOR =================

async function checkAiStatus() {
    try {
        const res = await fetch('/api/ai/status/');
        const data = await res.json();
        const sub = document.getElementById('aiStatusSubtitle');
        if (sub) {
            if (data.configured) {
                sub.textContent = `Online • ${data.model || 'Gemini 2.5 Flash'}`;
                sub.style.color = 'var(--success)';
            } else {
                sub.textContent = 'API Key Required (Free in Google AI Studio)';
                sub.style.color = '#ef4444';
            }
        }
    } catch (err) {
        console.warn("Could not check Gemini AI status:", err);
    }
}

function toggleAiDrawer() {
    const drawer = document.getElementById('aiDrawer');
    if (drawer && drawer.classList.contains('open')) {
        closeAiDrawer();
    } else {
        openAiDrawer();
    }
}

function openAiDrawer() {
    const drawer = document.getElementById('aiDrawer');
    const overlay = document.getElementById('aiDrawerOverlay');
    if (drawer) drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
    
    // Auto-focus input after transition
    setTimeout(() => {
        const input = document.getElementById('aiChatInput');
        if (input) input.focus();
    }, 200);
}

function closeAiDrawer() {
    const drawer = document.getElementById('aiDrawer');
    const overlay = document.getElementById('aiDrawerOverlay');
    if (drawer) drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
}

function openAiForCurrentDoc() {
    if (currentPreviewDocId) {
        setAiContext(currentPreviewDocId, currentPreviewDocTitle || 'Active Document');
    }
    openAiDrawer();
}

function setAiContext(fileId, title) {
    activeAiFileId = fileId;
    activeAiDocTitle = title;
    const bar = document.getElementById('aiContextBar');
    const docName = document.getElementById('aiContextDocName');
    if (bar && docName) {
        docName.textContent = title;
        docName.title = title;
        bar.style.display = 'flex';
    }
}

function clearAiContext() {
    activeAiFileId = null;
    activeAiDocTitle = null;
    const bar = document.getElementById('aiContextBar');
    if (bar) {
        bar.style.display = 'none';
    }
}

function handleAiTextareaKey(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleAiChatSubmit(event);
    }
}

async function handleAiChatSubmit(event) {
    if (event) event.preventDefault();
    if (aiIsLoading) return;

    const input = document.getElementById('aiChatInput');
    const promptText = (input.value || '').trim();
    if (!promptText) return;

    input.value = '';
    input.style.height = 'auto';

    await sendAiMessage(promptText, null);
}

async function sendAiAction(action) {
    if (aiIsLoading) return;

    // If no context explicitly set but preview modal is open, attach it
    if (!activeAiFileId && currentPreviewDocId) {
        setAiContext(currentPreviewDocId, currentPreviewDocTitle || 'Active Document');
    }

    let userLabel = "";
    if (action === 'summarize') userLabel = "📝 Summarize Document";
    else if (action === 'quiz') userLabel = "❓ Generate Practice Quiz";
    else if (action === 'explain') userLabel = "💡 Explain Key Concepts";
    else userLabel = "Explain topic";

    await sendAiMessage(userLabel, action);
}

function appendAiMessage(htmlContent, isUser = false) {
    const container = document.getElementById('aiMessagesContainer');
    if (!container) return;

    const bubble = document.createElement('div');
    bubble.className = `ai-bubble ${isUser ? 'ai-bubble-user' : 'ai-bubble-assistant'}`;
    bubble.innerHTML = htmlContent;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

function showAiTypingIndicator() {
    const container = document.getElementById('aiMessagesContainer');
    if (!container) return;

    const indicator = document.createElement('div');
    indicator.id = 'aiTypingIndicator';
    indicator.className = 'ai-typing-indicator';
    indicator.innerHTML = `
        <div class="ai-typing-dot"></div>
        <div class="ai-typing-dot"></div>
        <div class="ai-typing-dot"></div>
    `;
    container.appendChild(indicator);
    container.scrollTop = container.scrollHeight;
}

function removeAiTypingIndicator() {
    const indicator = document.getElementById('aiTypingIndicator');
    if (indicator) indicator.remove();
}

async function sendAiMessage(promptText, action) {
    aiIsLoading = true;
    const sendBtn = document.getElementById('aiSendBtn');
    const input = document.getElementById('aiChatInput');
    if (sendBtn) sendBtn.disabled = true;
    if (input) input.disabled = true;

    // Append user message
    appendAiMessage(escapeHtml(promptText), true);

    // Show typing indicator
    showAiTypingIndicator();

    try {
        const payload = {
            prompt: promptText,
            file_id: activeAiFileId,
            action: action
        };

        const res = await fetch('/api/ai/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        removeAiTypingIndicator();

        if (data.response) {
            const formatted = renderSimpleMarkdown(data.response);
            appendAiMessage(formatted, false);
        } else if (data.error) {
            appendAiMessage(`<p style="color: #ef4444;">⚠️ <strong>Error:</strong> ${escapeHtml(data.error)}</p>`, false);
        } else {
            appendAiMessage(`<p>Sorry, no response received from Gemini.</p>`, false);
        }

        if (data.configured !== undefined) {
            checkAiStatus();
        }

    } catch (err) {
        removeAiTypingIndicator();
        console.error("AI Error:", err);
        appendAiMessage(`<p style="color: #ef4444;">⚠️ <strong>Network Error:</strong> Could not connect to Gemini service.</p>`, false);
    } finally {
        aiIsLoading = false;
        if (sendBtn) sendBtn.disabled = false;
        if (input) {
            input.disabled = false;
            input.focus();
        }
    }
}

// Lightweight Markdown to HTML Renderer
function renderSimpleMarkdown(md) {
    if (!md) return '';

    // First preserve code blocks
    const codeBlocks = [];
    let text = md.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
        const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
        codeBlocks.push(`<pre><code>${escapeHtml(code.trim())}</code></pre>`);
        return placeholder;
    });

    // Escape raw HTML characters outside code blocks
    text = escapeHtml(text);

    // Headings
    text = text.replace(/^#### (.*?)$/gm, '<h4>$1</h4>');
    text = text.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    text = text.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // Horizontal Rule
    text = text.replace(/^---$/gm, '<hr>');

    // Bold and Italic
    text = text.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Blockquotes
    text = text.replace(/^> (.*?)$/gm, '<blockquote>$1</blockquote>');

    // Markdown links [text](url)
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: underline;">$1</a>');

    // Unordered lists
    text = text.replace(/(?:^[ \t]*[\*\-\+] .*(?:\n|$))+/gm, (listMatch) => {
        const items = listMatch.trim().split('\n').map(line => {
            const clean = line.replace(/^[ \t]*[\*\-\+] /, '');
            return `<li>${clean}</li>`;
        }).join('');
        return `<ul>${items}</ul>`;
    });

    // Numbered lists
    text = text.replace(/(?:^[ \t]*\d+\. .*(?:\n|$))+/gm, (listMatch) => {
        const items = listMatch.trim().split('\n').map(line => {
            const clean = line.replace(/^[ \t]*\d+\. /, '');
            return `<li>${clean}</li>`;
        }).join('');
        return `<ol>${items}</ol>`;
    });

    // Paragraphs / line breaks
    text = text.replace(/\n\n+/g, '</p><p>');
    text = `<p>${text}</p>`;
    text = text.replace(/<p><\/p>/g, '');
    text = text.replace(/<p>(<h[1-4]>)/g, '$1');
    text = text.replace(/(<\/h[1-4]>)<\/p>/g, '$1');
    text = text.replace(/<p>(<ul>|<ol>|<pre>|<blockquote>|<hr>)/g, '$1');
    text = text.replace(/(<\/ul>|<\/ol>|<\/pre>|<\/blockquote>|<hr>)<\/p>/g, '$1');
    text = text.replace(/\n/g, '<br>');

    // Restore code blocks
    codeBlocks.forEach((cb, idx) => {
        text = text.replace(`__CODE_BLOCK_${idx}__`, cb);
    });

    return text;
}

