// Knowledge Management
class KnowledgeManager {
    constructor() {
        this.currentKnowledgeBase = 'default';
        this.knowledgeBases = ['default'];
        this.documents = [];
        this.analytics = {
            totalDocuments: 0,
            totalVectorChunks: 0,
            totalQueries: 0
        };
        this.selectedFiles = []; // Store selected files for upload
        this.init();
    }

    init() {
        this.setupFileUpload();
        this.setupKnowledgeBaseSelector();
        this.setupDocumentSearch();
        this.setupActionButtons();
        this.loadKnowledgeBases();
        this.updateChatKnowledgeBaseIndicator();
    }

    async loadKnowledgeData() {
        try {
            debugLog('🔄 Starting knowledge data reload...');
            // Load documents from RAG system
            debugLog('📄 Loading documents...');
            await this.loadDocuments();
            debugLog('📊 Loading analytics...');
            // Load analytics
            await this.loadAnalytics();
            debugLog('🎨 Updating UI...');
            // Update UI
            this.updateKnowledgeUI();
            debugLog('✅ Knowledge data reload completed');
        } catch (error) {
            console.error('❌ Failed to load knowledge data:', error);
            this.showError('Failed to load knowledge base data');
        }
    }

    async loadDocuments() {
        try {
            const response = await fetch('/api/rag/documents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace: this.currentKnowledgeBase
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.documents = data.documents || [];
            } else {
                throw new Error('Failed to fetch documents');
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.documents = [];
        }
    }

    async loadAnalytics() {
        try {
            const response = await fetch('/api/rag/analytics', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.analytics = {
                    totalDocuments: data.document_count || 0,
                    totalVectorChunks: data.chunk_count || 0,
                    totalQueries: data.query_count || 0
                };
            }
        } catch (error) {
            console.error('Error loading analytics:', error);
            // Use default analytics on error
        }
    }

    updateKnowledgeUI() {
        // Update analytics cards
        this.updateAnalyticsCards();
        // Update documents table
        this.updateDocumentsTable();
        // Update knowledge base selector
        this.updateKnowledgeBaseSelector();
    }

    updateAnalyticsCards() {
        const docCount = document.getElementById('doc-count');
        const chunkCount = document.getElementById('chunk-count');
        const queryCount = document.getElementById('query-count');

        if (docCount) docCount.textContent = this.analytics.totalDocuments;
        if (chunkCount) chunkCount.textContent = this.analytics.totalVectorChunks.toLocaleString();
        if (queryCount) queryCount.textContent = this.analytics.totalQueries.toLocaleString();
    }

    updateDocumentsTable() {
        const tableBody = document.getElementById('documents-table-body');
        const emptyState = document.getElementById('documents-empty-state');

        if (!tableBody || !emptyState) return;

        if (this.documents.length === 0) {
            tableBody.classList.add('hidden');
            emptyState.classList.remove('hidden');
            return;
        }

        tableBody.classList.remove('hidden');
        emptyState.classList.add('hidden');

        tableBody.innerHTML = '';

        this.documents.forEach(doc => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 dark:hover:bg-gray-800/50';

            const formatFileSize = (bytes) => {
                if (!bytes) return 'Unknown';
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(1024));
                return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
            };

            const formatDate = (dateString) => {
                if (!dateString) return 'Unknown';
                return new Date(dateString).toLocaleDateString();
            };

            row.innerHTML = `
                <td class="px-6 py-4">
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                            <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                            </svg>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-900 dark:text-white">${doc.name || 'Unknown Document'}</p>
                            <p class="text-sm text-gray-500 dark:text-gray-400">${doc.type || 'Unknown Type'}</p>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    ${formatFileSize(doc.size)}
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    ${doc.chunks || 0} chunks
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    ${formatDate(doc.uploadDate)}
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${doc.status === 'processed' ? 'bg-green-100 text-green-800 dark:bg-gray-800 dark:text-green-400 dark:border dark:border-green-800' : 'bg-yellow-100 text-yellow-800 dark:bg-gray-800 dark:text-yellow-400 dark:border dark:border-yellow-800'}">
                        ${doc.status || 'processed'}
                    </span>
                </td>
                <td class="px-6 py-4 text-right text-sm font-medium">
                    <button onclick="window.app.knowledgeManager.deleteDocument('${doc.id}')" class="text-red-600 hover:text-red-900 dark:text-gray-400 dark:hover:text-red-400 transition-colors">
                        Delete
                    </button>
                </td>
            `;

            tableBody.appendChild(row);
        });
    }

    updateKnowledgeBaseSelector() {
        const selector = document.getElementById('knowledge-base-selector');
        if (!selector) return;

        // Populate with all available knowledge bases
        selector.innerHTML = '';
        this.knowledgeBases.forEach(kb => {
            const option = document.createElement('option');
            option.value = kb;
            option.textContent = kb.charAt(0).toUpperCase() + kb.slice(1).replace(/-/g, ' ') + ' Knowledge Base';
            selector.appendChild(option);
        });

        selector.value = this.currentKnowledgeBase;
    }

    setupActionButtons() {
        // Browse files button is handled in setupFileUpload()

        // Refresh documents button
        const refreshBtn = document.getElementById('refresh-documents');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                await this.loadKnowledgeData();
                this.showSuccess('Documents refreshed');
            });
        }

        // Search documents functionality is handled in setupDocumentSearch()

        // Add new knowledge base button
        const addKbBtn = document.getElementById('add-knowledge-base-btn');
        if (addKbBtn) {
            addKbBtn.addEventListener('click', () => {
                this.showAddKnowledgeBaseModal();
            });
        }
    }

    setupFileUpload() {
        const dropZone = document.getElementById('file-drop-zone');
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('upload-btn');
        const browseBtn = document.getElementById('browse-files-btn');

        if (!dropZone || !fileInput || !uploadBtn || !browseBtn) {
            console.error('Missing upload elements:', { dropZone: !!dropZone, fileInput: !!fileInput, uploadBtn: !!uploadBtn, browseBtn: !!browseBtn });
            return;
        }

        // Browse files button - opens file picker
        browseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            fileInput.click();
        });

        // Upload button - uploads selected files
        uploadBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (this.selectedFiles.length > 0) {
                await this.uploadSelectedFiles();
            } else {
                this.showError('Please select files to upload first');
            }
        });

        // File input change - store selected files
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.selectedFiles = Array.from(e.target.files);
                this.updateFileSelectionDisplay();
                debugLog(`Selected ${this.selectedFiles.length} files for upload`);
            }
        });

        // Drag and drop events
        dropZone.addEventListener('dragenter', (e) => {
            e.preventDefault();
            e.stopPropagation();
        });

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Only remove classes if we're leaving the dropzone entirely
            if (!dropZone.contains(e.relatedTarget)) {
                dropZone.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
            }
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');

            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.selectedFiles = files;
                this.updateFileSelectionDisplay();
                debugLog(`Dropped ${files.length} files for upload`);
            }
        });

        // Make the entire drop zone clickable to browse files
        // But exclude the Browse Files button to avoid duplicate triggers
        dropZone.addEventListener('click', (e) => {
            // Don't trigger if clicking the browse button or upload button
            if (e.target.closest('#browse-files-btn') || e.target.closest('#upload-btn')) {
                return;
            }
            // Only trigger on drop zone background clicks
            if (e.target === dropZone || e.target.closest('#file-drop-zone')) {
                fileInput.click();
            }
        });
    }

    updateFileSelectionDisplay() {
        const dropZone = document.getElementById('file-drop-zone');
        if (!dropZone) return;

        let displayText = 'Drag & drop files here or click "Browse Files" to select';

        if (this.selectedFiles.length > 0) {
            const fileNames = this.selectedFiles.map(file => file.name).join(', ');
            displayText = `Selected files: ${fileNames}`;

            // Update the drop zone text
            const textElement = dropZone.querySelector('p');
            if (textElement) {
                textElement.textContent = displayText;
                textElement.classList.add('text-blue-600', 'font-medium');
            }
        } else {
            // Reset to default text
            const textElement = dropZone.querySelector('p');
            if (textElement) {
                textElement.textContent = displayText;
                textElement.classList.remove('text-blue-600', 'font-medium');
            }
        }
    }

    async uploadSelectedFiles() {
        if (this.selectedFiles.length === 0) {
            this.showError('No files selected for upload');
            return;
        }

        const uploadBtn = document.getElementById('upload-btn');
        if (uploadBtn) {
            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Uploading...';
        }

        let successCount = 0;
        let errorCount = 0;

        try {
            for (const file of this.selectedFiles) {
                try {
                    await this.uploadSingleFile(file);
                    successCount++;
                } catch (error) {
                    console.error(`Failed to upload ${file.name}:`, error);
                    errorCount++;
                }
            }

            // Clear selected files after upload attempt
            this.selectedFiles = [];
            this.updateFileSelectionDisplay();

            // Reset file input
            const fileInput = document.getElementById('file-input');
            if (fileInput) fileInput.value = '';

            // Refresh documents list - use full knowledge data reload
            await this.loadKnowledgeData();

            if (successCount > 0) {
                this.showSuccess(`Successfully uploaded ${successCount} file${successCount !== 1 ? 's' : ''}`);
            }
            if (errorCount > 0) {
                this.showError(`Failed to upload ${errorCount} file${errorCount !== 1 ? 's' : ''}`);
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.showError(`Upload failed: ${error.message}`);
        } finally {
            if (uploadBtn) {
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Upload';
            }
        }
    }

    async uploadSingleFile(file) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('knowledge_base', this.currentKnowledgeBase);

            const xhr = new XMLHttpRequest();

            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    debugLog(`Upload progress for ${file.name}: ${percentComplete.toFixed(1)}%`);
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.status === 'success') {
                            resolve(response);
                        } else {
                            reject(new Error(response.message || 'Upload failed'));
                        }
                    } catch (e) {
                        reject(new Error('Invalid server response'));
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            };

            xhr.onerror = () => {
                reject(new Error('Network error during upload'));
            };

            xhr.ontimeout = () => {
                reject(new Error('Upload timed out'));
            };

            xhr.timeout = 60000; // 60 second timeout
            xhr.open('POST', '/api/rag/ingest', true);
            xhr.send(formData);
        });
    }

    async handleFiles(files) {
        for (const file of files) {
            await this.uploadFile(file);
        }

        // Reload knowledge data after uploads
        debugLog('Reloading knowledge data after upload...');
        await this.loadKnowledgeData();
        debugLog('Knowledge data reloaded successfully');
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/rag/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                debugLog('File uploaded successfully:', data);
                this.showSuccess(`File "${file.name}" uploaded successfully`);
            } else {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
        } catch (error) {
            console.error('File upload error:', error);
            this.showError(`Failed to upload "${file.name}": ${error.message}`);
        }
    }

    async deleteDocument(documentId) {
        try {
            const response = await fetch(`/api/rag/documents/${documentId}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace: this.currentKnowledgeBase
                })
            });

            if (response.ok) {
                debugLog(`Document ${documentId} deleted successfully`);
                this.showSuccess(`Document ${documentId} deleted successfully`);
                // Reload knowledge data
                debugLog('Reloading knowledge data after delete...');
                await this.loadKnowledgeData();
                debugLog('Knowledge data reloaded after delete');
            } else {
                throw new Error(`Delete failed: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Document delete error:', error);
            this.showError(`Failed to delete document: ${error.message}`);
        }
    }

    setupKnowledgeBaseSelector() {
        const selector = document.getElementById('knowledge-base-selector');
        if (!selector) return;

        selector.addEventListener('change', (e) => {
            this.currentKnowledgeBase = e.target.value;
            this.loadKnowledgeData();
            this.updateChatKnowledgeBaseIndicator();
        });
    }

    updateChatKnowledgeBaseIndicator() {
        const indicator = document.getElementById('currentKnowledgeBase');
        if (indicator) {
            indicator.textContent = this.currentKnowledgeBase;
        }
    }

    setupDocumentSearch() {
        const searchInput = document.getElementById('document-search');
        if (!searchInput) return;

        searchInput.addEventListener('input', (e) => {
            this.filterDocuments(e.target.value);
        });
    }

    filterDocuments(searchTerm) {
        const rows = document.querySelectorAll('#documents-table-body tr');
        const term = searchTerm.toLowerCase();

        rows.forEach(row => {
            const name = row.querySelector('td:first-child p').textContent.toLowerCase();
            const type = row.querySelector('td:first-child p:last-child').textContent.toLowerCase();

            if (name.includes(term) || type.includes(term)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    showSuccess(message) {
        // Simple success notification
        debugLog('Success:', message);
        // TODO: Implement proper toast notifications
    }

    showError(message) {
        // Simple error notification
        // Keep console.error for user-facing errors
        console.error('Error:', message);
        // TODO: Implement proper toast notifications
    }

    loadKnowledgeBases() {
        // Load knowledge bases from localStorage for now
        const stored = localStorage.getItem('robobrain_knowledge_bases');
        this.knowledgeBases = stored ? JSON.parse(stored) : ['default'];
        this.updateKnowledgeBaseSelector();
    }

    saveKnowledgeBases() {
        localStorage.setItem('robobrain_knowledge_bases', JSON.stringify(this.knowledgeBases));
    }

    showAddKnowledgeBaseModal() {
        const name = prompt('Enter the name for the new Knowledge Base:');
        if (name && name.trim()) {
            const kbName = name.trim().toLowerCase().replace(/\s+/g, '-');
            if (!this.knowledgeBases.includes(kbName)) {
                this.knowledgeBases.push(kbName);
                this.saveKnowledgeBases();
                this.updateKnowledgeBaseSelector();
                this.currentKnowledgeBase = kbName;
                this.loadKnowledgeData();
                this.updateChatKnowledgeBaseIndicator();
                this.showSuccess(`Knowledge Base "${name}" created successfully`);

                // Update sidebar list if Knowledge is currently selected
                if (window.app?.navigation) {
                    window.app.navigation.populateKnowledgeBaseList();
                }
            } else {
                this.showError('A Knowledge Base with that name already exists');
            }
        }
    }
}
