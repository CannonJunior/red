/**
 * CAG (Cache-Augmented Generation) Manager
 *
 * Manages in-memory context caching for zero-latency LLM responses.
 * Unlike RAG which retrieves chunks, CAG preloads entire documents
 * into the model's context window for instant access.
 */

class CAGManager {
    constructor() {
        this.selectedFiles = [];
        this.setupEventListeners();
        this.loadCAGStatus();
    }

    setupEventListeners() {
        // Browse files button
        const browseBtn = document.getElementById('cag-browse-files-btn');
        const fileInput = document.getElementById('cag-file-input');

        if (browseBtn && fileInput) {
            browseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                fileInput.click();
            });

            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.selectedFiles = Array.from(e.target.files);
                    this.updateFileSelectionDisplay();
                }
            });
        }

        // Load to cache button
        const loadBtn = document.getElementById('cag-load-btn');
        if (loadBtn) {
            loadBtn.addEventListener('click', async () => {
                if (this.selectedFiles.length > 0) {
                    await this.loadFilesToCache();
                } else {
                    this.showError('Please select files first');
                }
            });
        }

        // Clear cache button
        const dumpBtn = document.getElementById('cag-dump-btn');
        if (dumpBtn) {
            dumpBtn.addEventListener('click', async () => {
                if (confirm('Are you sure you want to clear all cached documents? This cannot be undone.')) {
                    await this.clearCache();
                }
            });
        }

        // Refresh documents button
        const refreshBtn = document.getElementById('cag-refresh-documents');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                await this.loadCAGStatus();
                this.showSuccess('Status refreshed');
            });
        }

        // Drop zone
        const dropZone = document.getElementById('cag-drop-zone');
        if (dropZone) {
            dropZone.addEventListener('dragenter', (e) => {
                e.preventDefault();
                e.stopPropagation();
            });

            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('border-purple-500', 'bg-purple-50', 'dark:bg-purple-900/20');
            });

            dropZone.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (!dropZone.contains(e.relatedTarget)) {
                    dropZone.classList.remove('border-purple-500', 'bg-purple-50', 'dark:bg-purple-900/20');
                }
            });

            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('border-purple-500', 'bg-purple-50', 'dark:bg-purple-900/20');

                const files = Array.from(e.dataTransfer.files);
                if (files.length > 0) {
                    this.selectedFiles = files;
                    this.updateFileSelectionDisplay();
                }
            });

            // Make drop zone clickable (but exclude buttons)
            dropZone.addEventListener('click', (e) => {
                if (e.target.closest('#cag-browse-files-btn') || e.target.closest('#cag-load-btn')) {
                    return;
                }
                if (fileInput) {
                    fileInput.click();
                }
            });
        }

        // Knowledge mode selector
        const modeSelector = document.getElementById('knowledge-mode-selector');
        if (modeSelector) {
            modeSelector.addEventListener('change', (e) => {
                this.handleKnowledgeModeChange(e.target.value);
            });
        }
    }

    handleKnowledgeModeChange(mode) {
        const ragContainer = document.getElementById('rag-kb-selector-container');
        const cagContainer = document.getElementById('cag-status-container');

        // Hide all containers
        if (ragContainer) ragContainer.classList.add('hidden');
        if (cagContainer) cagContainer.classList.add('hidden');

        // Show appropriate container
        if (mode === 'rag' && ragContainer) {
            ragContainer.classList.remove('hidden');
        } else if (mode === 'cag' && cagContainer) {
            cagContainer.classList.remove('hidden');
            this.updateCAGStatusIndicator();
        }
    }

    updateFileSelectionDisplay() {
        const dropZone = document.getElementById('cag-drop-zone');
        if (!dropZone) return;

        const textElement = dropZone.querySelector('p');
        if (!textElement) return;

        if (this.selectedFiles.length > 0) {
            const fileNames = this.selectedFiles.map(f => f.name).join(', ');
            textElement.textContent = `Selected: ${fileNames}`;
            textElement.classList.add('text-purple-600', 'font-medium');
        } else {
            textElement.textContent = 'Drag & drop files to preload into context';
            textElement.classList.remove('text-purple-600', 'font-medium');
        }
    }

    async loadFilesToCache() {
        const progressDiv = document.getElementById('cag-load-progress');
        const loadBar = document.getElementById('cag-load-bar');
        const loadPercent = document.getElementById('cag-load-percent');
        const progressText = progressDiv.querySelector('span.text-sm');

        try {
            progressDiv.classList.remove('hidden');

            for (let i = 0; i < this.selectedFiles.length; i++) {
                const file = this.selectedFiles[i];
                const fileNum = i + 1;
                const totalFiles = this.selectedFiles.length;

                // Calculate base progress for this file
                const baseProgress = (i / totalFiles) * 100;
                const fileProgressRange = 100 / totalFiles;

                // Update text to show current file
                progressText.textContent = `Processing file ${fileNum} of ${totalFiles}: ${file.name}`;

                // Load file with detailed progress tracking
                await this.loadSingleFileWithProgress(
                    file,
                    baseProgress,
                    fileProgressRange,
                    loadBar,
                    loadPercent
                );
            }

            this.showSuccess(`Loaded ${this.selectedFiles.length} file(s) to cache`);
            this.selectedFiles = [];
            this.updateFileSelectionDisplay();

            // Reset file input
            const fileInput = document.getElementById('cag-file-input');
            if (fileInput) fileInput.value = '';

            // Refresh status
            await this.loadCAGStatus();

        } catch (error) {
            console.error('CAG load error:', error);
            this.showError(`Failed to load files: ${error.message}`);
        } finally {
            progressDiv.classList.add('hidden');
            loadBar.style.width = '0%';
            loadPercent.textContent = '0%';
            progressText.textContent = 'Loading to cache...';

            const detailsText = document.getElementById('cag-load-details');
            if (detailsText) {
                detailsText.textContent = 'Initializing upload...';
            }
        }
    }

    loadSingleFileWithProgress(file, baseProgress, fileProgressRange, loadBar, loadPercent) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);

            const detailsText = document.getElementById('cag-load-details');
            const formatSize = (bytes) => {
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            };

            // Track upload progress (0-40% of file progress)
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const uploadPercent = (e.loaded / e.total) * 40; // Upload is 40% of file progress
                    const totalProgress = baseProgress + (uploadPercent / 100) * fileProgressRange;
                    loadBar.style.width = `${totalProgress}%`;
                    loadPercent.textContent = `${Math.round(totalProgress)}%`;

                    if (detailsText) {
                        detailsText.textContent = `📤 Uploading: ${formatSize(e.loaded)} / ${formatSize(e.total)}`;
                    }
                }
            });

            // Track overall progress stages
            xhr.addEventListener('loadstart', () => {
                // Starting upload (0% of file range)
                const totalProgress = baseProgress;
                loadBar.style.width = `${totalProgress}%`;
                loadPercent.textContent = `${Math.round(totalProgress)}%`;

                if (detailsText) {
                    detailsText.textContent = `📂 Preparing upload: ${file.name} (${formatSize(file.size)})`;
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    // Upload complete, now processing (40-100% of file progress)
                    const processingProgress = baseProgress + 0.4 * fileProgressRange;
                    loadBar.style.width = `${processingProgress}%`;
                    loadPercent.textContent = `${Math.round(processingProgress)}%`;

                    if (detailsText) {
                        detailsText.textContent = `📄 Processing document with Docling...`;
                    }

                    // Simulate processing phases
                    setTimeout(() => {
                        // Tokenizing (70% of file progress)
                        const tokenizingProgress = baseProgress + 0.7 * fileProgressRange;
                        loadBar.style.width = `${tokenizingProgress}%`;
                        loadPercent.textContent = `${Math.round(tokenizingProgress)}%`;

                        if (detailsText) {
                            detailsText.textContent = `🔢 Counting tokens and analyzing content...`;
                        }

                        setTimeout(() => {
                            // Caching (90% of file progress)
                            const cachingProgress = baseProgress + 0.9 * fileProgressRange;
                            loadBar.style.width = `${cachingProgress}%`;
                            loadPercent.textContent = `${Math.round(cachingProgress)}%`;

                            if (detailsText) {
                                detailsText.textContent = `💾 Storing in context cache...`;
                            }

                            setTimeout(() => {
                                // Complete (100% of file progress)
                                const completeProgress = baseProgress + fileProgressRange;
                                loadBar.style.width = `${completeProgress}%`;
                                loadPercent.textContent = `${Math.round(completeProgress)}%`;

                                const result = JSON.parse(xhr.responseText);

                                if (detailsText && result.status === 'success') {
                                    detailsText.textContent = `✅ Cached ${result.tokens?.toLocaleString() || 0} tokens from ${result.filename}`;
                                }

                                if (result.status === 'success') {
                                    resolve(result);
                                } else {
                                    reject(new Error(result.error || 'Load failed'));
                                }
                            }, 200);
                        }, 200);
                    }, 200);
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            });

            xhr.addEventListener('error', () => {
                if (detailsText) {
                    detailsText.textContent = `❌ Network error during upload`;
                }
                reject(new Error('Network error during upload'));
            });

            xhr.addEventListener('abort', () => {
                if (detailsText) {
                    detailsText.textContent = `⚠️ Upload aborted`;
                }
                reject(new Error('Upload aborted'));
            });

            xhr.open('POST', '/api/cag/load');
            xhr.send(formData);
        });
    }

    async clearCache() {
        try {
            const response = await fetch('/api/cag/clear', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.showSuccess(`Cleared ${result.documents_removed} document(s), freed ${result.tokens_freed} tokens`);
                await this.loadCAGStatus();
            } else {
                throw new Error(result.error || 'Clear failed');
            }

        } catch (error) {
            console.error('CAG clear error:', error);
            this.showError(`Failed to clear cache: ${error.message}`);
        }
    }

    async loadCAGStatus() {
        try {
            const response = await fetch('/api/cag/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });

            const status = await response.json();

            // Update metrics
            document.getElementById('cag-loaded-tokens').textContent = status.total_tokens.toLocaleString();
            document.getElementById('cag-available-tokens').textContent = status.available_tokens.toLocaleString();
            document.getElementById('cag-usage-percent').textContent = `${Math.round(status.usage_percent)}%`;

            // Update memory bar
            const memoryBar = document.getElementById('cag-memory-bar');
            const memoryBarText = document.getElementById('cag-memory-bar-text');
            memoryBar.style.width = `${status.usage_percent}%`;
            memoryBarText.textContent = `${status.total_tokens.toLocaleString()} / ${(status.max_tokens / 1000).toFixed(0)}K tokens`;

            // Update max capacity description
            const maxCapacityText = document.getElementById('cag-max-capacity-text');
            if (maxCapacityText) {
                const maxTokensFormatted = status.max_tokens.toLocaleString();
                const approxWords = Math.round(status.max_tokens * 0.75).toLocaleString();
                maxCapacityText.textContent = `Maximum context window: ${maxTokensFormatted} tokens (~${approxWords} words)`;
            }

            // Update table
            this.updateDocumentsTable(status.documents);

            // Update chat status indicator
            this.updateCAGStatusIndicator();

        } catch (error) {
            console.error('Failed to load CAG status:', error);
        }
    }

    updateDocumentsTable(documents) {
        const tbody = document.getElementById('cag-documents-table-body');
        const emptyState = document.getElementById('cag-documents-empty-state');

        if (!tbody || !emptyState) return;

        if (documents.length === 0) {
            tbody.innerHTML = '';
            emptyState.classList.remove('hidden');
            return;
        }

        emptyState.classList.add('hidden');

        tbody.innerHTML = documents.map(doc => {
            const loadedDate = new Date(doc.loaded_at).toLocaleDateString();
            return `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900 dark:text-white">${doc.filename}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        ${doc.tokens.toLocaleString()}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-gray-800 dark:text-purple-400 dark:border dark:border-purple-800">
                            ${doc.status}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        ${loadedDate}
                    </td>
                    <td class="px-6 py-4 text-right text-sm font-medium">
                        <button onclick="window.app.cagManager.deleteDocument('${doc.id}')" class="text-red-600 hover:text-red-900 dark:text-gray-400 dark:hover:text-red-400 transition-colors">
                            Remove
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async deleteDocument(docId) {
        if (!confirm('Remove this document from cache?')) return;

        try {
            const response = await fetch(`/api/cag/documents/${docId}`, {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'}
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.showSuccess(`Removed ${result.removed}`);
                await this.loadCAGStatus();
            } else {
                throw new Error(result.error || 'Delete failed');
            }

        } catch (error) {
            console.error('CAG delete error:', error);
            this.showError(`Failed to remove document: ${error.message}`);
        }
    }

    updateCAGStatusIndicator() {
        const statusElement = document.getElementById('cag-cache-status');
        if (!statusElement) return;

        const loadedTokens = parseInt(document.getElementById('cag-loaded-tokens')?.textContent.replace(/,/g, '') || '0');
        statusElement.textContent = `${loadedTokens.toLocaleString()} tokens loaded`;
    }

    showSuccess(message) {
        // Use the main app's notification system if available
        if (window.app && window.app.knowledgeManager) {
            window.app.knowledgeManager.showSuccess(message);
        } else {
            console.log('✅', message);
        }
    }

    showError(message) {
        // Use the main app's notification system if available
        if (window.app && window.app.knowledgeManager) {
            window.app.knowledgeManager.showError(message);
        } else {
            console.error('❌', message);
        }
    }
}

// Initialize when DOM is ready
if (typeof window !== 'undefined') {
    window.CAGManager = CAGManager;
}
