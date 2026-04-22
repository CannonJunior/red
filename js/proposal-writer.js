/**
 * js/proposal-writer.js — Proposal document writing UI.
 *
 * Three-column layout:
 *   [Document Navigator] | [Section Editor] | [LLM Assistant]
 *
 * Depends on: proposal-comments.js (loaded after this file)
 */

const ProposalWriter = (() => {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let _proposalId = null;
  let _proposalTitle = '';
  let _winThemes = [];
  let _opportunityId = '';
  let _documents = [];
  let _activeDoc = null;
  let _activeSection = null;
  let _autoSaveTimer = null;
  let _docTypes = [];
  let _llmActions = [];

  // ---------------------------------------------------------------------------
  // API helpers
  // ---------------------------------------------------------------------------
  async function _api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    return res.json();
  }
  const _get = (p) => _api('GET', p);
  const _post = (p, b) => _api('POST', p, b);
  const _put = (p, b) => _api('PUT', p, b);
  const _del = (p) => _api('DELETE', p);

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  async function init(proposalId, proposalTitle = '', winThemes = [], opportunityId = '') {
    _proposalId = proposalId;
    _proposalTitle = proposalTitle;
    _winThemes = winThemes;
    _opportunityId = opportunityId;

    const [dtRes, actRes] = await Promise.all([
      _get('/api/proposal-doc-types'),
      _get('/api/proposal-llm-actions'),
    ]);
    _docTypes = dtRes.doc_types || [];
    _llmActions = actRes.actions || [];

    await _loadDocuments();
    _render();
  }

  async function _loadDocuments() {
    const res = await _get(`/api/proposal-docs?proposal_id=${_proposalId}`);
    _documents = res.documents || [];
  }

  // ---------------------------------------------------------------------------
  // Render: full panel
  // ---------------------------------------------------------------------------
  function _render() {
    const container = document.getElementById('proposal-writer-panel');
    if (!container) return;

    container.innerHTML = `
      <div class="flex h-full gap-0 overflow-hidden">
        <!-- Navigator -->
        <div id="pw-navigator" class="w-56 flex-shrink-0 border-r border-zinc-700 bg-zinc-900 flex flex-col">
          ${_renderNavigator()}
        </div>
        <!-- Editor -->
        <div id="pw-editor" class="flex-1 flex flex-col min-w-0 bg-zinc-950 overflow-hidden">
          ${_renderEditor()}
        </div>
        <!-- LLM sidebar -->
        <div id="pw-llm" class="w-72 flex-shrink-0 border-l border-zinc-700 bg-zinc-900 flex flex-col overflow-hidden">
          ${_renderLlmPanel()}
        </div>
      </div>`;
    _attachHandlers();
  }

  // ---------------------------------------------------------------------------
  // Navigator
  // ---------------------------------------------------------------------------
  function _renderNavigator() {
    const docList = _documents.map(d => `
      <div class="pw-doc-item cursor-pointer px-3 py-2 rounded text-sm hover:bg-zinc-700
                  ${_activeDoc?.id === d.id ? 'bg-zinc-700 text-white' : 'text-zinc-300'}"
           data-doc-id="${d.id}">
        <div class="font-medium truncate">${_esc(d.title)}</div>
        <div class="text-xs text-zinc-500">${_esc(d.doc_type)}</div>
      </div>`).join('');

    return `
      <div class="p-3 border-b border-zinc-700 flex items-center justify-between">
        <span class="text-xs font-semibold text-zinc-400 uppercase tracking-wide">Documents</span>
        <button id="pw-add-doc" class="text-blue-400 hover:text-blue-300 text-lg leading-none" title="Add document">+</button>
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-1">${docList}</div>`;
  }

  // ---------------------------------------------------------------------------
  // Editor
  // ---------------------------------------------------------------------------
  function _renderEditor() {
    if (!_activeDoc) {
      return `<div class="flex-1 flex items-center justify-center text-zinc-500 text-sm">
                Select or create a document to begin writing.
              </div>`;
    }

    const sections = _activeDoc.sections || [];
    const sectionTree = _renderSectionTree(sections, 0);

    const editorArea = _activeSection ? `
      <div class="flex-1 flex flex-col p-4 overflow-hidden">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xs text-zinc-500">${_esc(_activeSection.section_number)}</span>
          <h3 class="font-semibold text-white text-sm">${_esc(_activeSection.title)}</h3>
          <span class="ml-auto flex gap-2">
            <button class="pw-save-section text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded">Save</button>
            <button class="pw-version-section text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 px-3 py-1 rounded" title="Save version snapshot">Snapshot</button>
            <button class="pw-comments-toggle text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 px-3 py-1 rounded">Comments</button>
          </span>
        </div>
        ${_activeSection.guidance ? `<div class="text-xs text-amber-400/80 bg-amber-950/30 border border-amber-900/50 rounded p-2 mb-3">${_esc(_activeSection.guidance)}</div>` : ''}
        <textarea id="pw-section-content"
          class="flex-1 bg-zinc-900 border border-zinc-700 rounded p-3 text-sm text-zinc-100 resize-none focus:outline-none focus:border-blue-500 font-mono leading-relaxed"
          placeholder="Begin writing…">${_esc(_activeSection.content || '')}</textarea>
        <div class="mt-2 flex items-center gap-3 text-xs text-zinc-500">
          <span id="pw-word-count">${_wordCount(_activeSection.content)} words</span>
          ${_activeSection.word_limit ? `<span>/ ~${_activeSection.word_limit} limit</span>` : ''}
          <span id="pw-save-status" class="ml-auto"></span>
        </div>
        <!-- Comments panel (hidden by default) -->
        <div id="pw-comments-panel" class="hidden mt-3 border-t border-zinc-700 pt-3 max-h-64 overflow-y-auto">
          <div id="pw-comments-list">Loading…</div>
          <div class="mt-2 flex gap-2">
            <input id="pw-new-comment" type="text" placeholder="Add a comment…"
              class="flex-1 bg-zinc-800 border border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100 focus:outline-none focus:border-blue-500"/>
            <button id="pw-post-comment" class="text-xs bg-zinc-700 hover:bg-zinc-600 text-white px-3 py-1 rounded">Post</button>
          </div>
        </div>
      </div>` : `
      <div class="flex-1 flex items-center justify-center text-zinc-500 text-sm">
        Select a section to start editing.
      </div>`;

    return `
      <div class="border-b border-zinc-700 px-4 py-2 flex items-center justify-between bg-zinc-900">
        <div>
          <span class="font-semibold text-white text-sm">${_esc(_activeDoc.title)}</span>
          <span class="ml-2 text-xs text-zinc-500">${_esc(_activeDoc.doc_type)}</span>
        </div>
        <div class="flex gap-2">
          <button id="pw-add-section" class="text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 px-3 py-1 rounded">+ Section</button>
          <button id="pw-apply-template" class="text-xs bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1 rounded">Apply Template</button>
          <button id="pw-stage-snapshot-btn" class="text-xs bg-violet-800 hover:bg-violet-700 text-white px-3 py-1 rounded" title="Snapshot all sections at a review gate">Stage Snapshot</button>
          <button id="pw-export-btn" class="text-xs bg-teal-800 hover:bg-teal-700 text-white px-3 py-1 rounded" title="Export document as .docx">Export DOCX</button>
          <button id="pw-color-team-upload-btn" class="text-xs bg-rose-800 hover:bg-rose-700 text-white px-3 py-1 rounded" title="Upload color team review (.docx)">Color Team Review</button>
          <button id="pw-color-team-export-btn" class="text-xs bg-rose-900 hover:bg-rose-800 text-zinc-300 px-3 py-1 rounded" title="Export document with color-team comments as .docx">CT Export</button>
          <button id="pw-compliance-btn" class="text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 px-3 py-1 rounded" title="View compliance assessment">Compliance</button>
          <input type="file" id="pw-color-team-file-input" accept=".docx" class="hidden"/>
        </div>
      </div>
      <!-- Compliance assessment panel (hidden by default) -->
      <div id="pw-compliance-panel" class="hidden border-b border-zinc-700 bg-zinc-900/80 px-4 py-3 max-h-64 overflow-y-auto">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold text-zinc-300 uppercase tracking-wide">Compliance Assessment</span>
          <button id="pw-compliance-close" class="text-zinc-500 hover:text-zinc-300 text-lg leading-none">&times;</button>
        </div>
        <div id="pw-compliance-content" class="text-xs text-zinc-400">Loading…</div>
      </div>
      <div class="flex flex-1 overflow-hidden">
        <div class="w-48 flex-shrink-0 border-r border-zinc-800 bg-zinc-900/50 overflow-y-auto p-2">
          ${sectionTree}
        </div>
        <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
          ${editorArea}
        </div>
      </div>`;
  }

  function _renderSectionTree(sections, depth) {
    return sections.map(s => `
      <div class="pw-section-item cursor-pointer px-2 py-1 rounded text-xs hover:bg-zinc-700
                  ${_activeSection?.id === s.id ? 'bg-zinc-700 text-white' : 'text-zinc-400'}"
           style="padding-left:${8 + depth * 12}px"
           data-section-id="${s.id}">
        <span class="text-zinc-600 mr-1">${_esc(s.section_number)}</span>${_esc(s.title)}
      </div>
      ${s.children?.length ? _renderSectionTree(s.children, depth + 1) : ''}`
    ).join('');
  }

  // ---------------------------------------------------------------------------
  // LLM Panel
  // ---------------------------------------------------------------------------
  function _renderLlmPanel() {
    const actionBtns = _llmActions.map(a => `
      <button class="pw-llm-action w-full text-left text-xs px-3 py-2 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
              data-action="${a.key}" title="${_esc(a.description)}">
        ${_esc(a.label)}
      </button>`).join('');

    return `
      <div class="p-3 border-b border-zinc-700">
        <span class="text-xs font-semibold text-zinc-400 uppercase tracking-wide">LLM Assistant</span>
      </div>
      <div class="p-3 flex flex-col gap-2 flex-1 overflow-y-auto">
        <div class="text-xs text-zinc-500 mb-1">Select a section then run an action:</div>
        <div class="space-y-1.5">${actionBtns}</div>
        <div id="pw-llm-status" class="text-xs text-zinc-500 mt-2"></div>
        <div id="pw-llm-result" class="hidden mt-2 text-xs text-zinc-200 bg-zinc-800 border border-zinc-700 rounded p-3 max-h-64 overflow-y-auto whitespace-pre-wrap leading-relaxed"></div>
        <div id="pw-llm-result-actions" class="hidden flex gap-2 mt-1">
          <button id="pw-llm-apply" class="text-xs bg-green-700 hover:bg-green-600 text-white px-3 py-1 rounded">Apply to Section</button>
          <button id="pw-llm-dismiss" class="text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 px-3 py-1 rounded">Dismiss</button>
        </div>
      </div>`;
  }

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------
  function _attachHandlers() {
    // Doc selection
    document.querySelectorAll('.pw-doc-item').forEach(el => {
      el.addEventListener('click', () => _selectDoc(el.dataset.docId));
    });

    // Section selection
    document.querySelectorAll('.pw-section-item').forEach(el => {
      el.addEventListener('click', () => _selectSection(el.dataset.sectionId));
    });

    // Add document
    document.getElementById('pw-add-doc')?.addEventListener('click', _showAddDocModal);

    // Add section
    document.getElementById('pw-add-section')?.addEventListener('click', _showAddSectionModal);

    // Apply template
    document.getElementById('pw-apply-template')?.addEventListener('click', async () => {
      if (!_activeDoc) return;
      if (!confirm('Apply the built-in template? Existing sections will not be removed.')) return;
      await _post(`/api/proposal-docs/${_activeDoc.id}/apply-template`,
                  { doc_type: _activeDoc.doc_type });
      await _reloadDoc();
    });

    // Stage snapshot
    document.getElementById('pw-stage-snapshot-btn')?.addEventListener('click', _showStageSnapshotModal);

    // Export DOCX
    document.getElementById('pw-export-btn')?.addEventListener('click', () => {
      if (!_activeDoc) return;
      window.location.href = `/api/proposal-docs/${_activeDoc.id}/export`;
    });

    // Color team export DOCX
    document.getElementById('pw-color-team-export-btn')?.addEventListener('click', () => {
      if (!_activeDoc) return;
      window.location.href = `/api/proposal-docs/${_activeDoc.id}/color-team-export`;
    });

    // Color team upload — trigger file picker
    document.getElementById('pw-color-team-upload-btn')?.addEventListener('click', () => {
      document.getElementById('pw-color-team-file-input')?.click();
    });

    // Color team file selected — show stage modal then upload
    document.getElementById('pw-color-team-file-input')?.addEventListener('change', async (e) => {
      const file = e.target.files?.[0];
      if (!file || !_activeDoc) return;
      e.target.value = ''; // reset so same file can be re-selected
      await _showColorTeamUploadModal(file);
    });

    // Compliance assessment panel toggle
    document.getElementById('pw-compliance-btn')?.addEventListener('click', async () => {
      const panel = document.getElementById('pw-compliance-panel');
      if (!panel) return;
      const isHidden = panel.classList.contains('hidden');
      if (isHidden) {
        panel.classList.remove('hidden');
        await _loadComplianceAssessment();
      } else {
        panel.classList.add('hidden');
      }
    });
    document.getElementById('pw-compliance-close')?.addEventListener('click', () => {
      document.getElementById('pw-compliance-panel')?.classList.add('hidden');
    });

    // Save section
    document.querySelector('.pw-save-section')?.addEventListener('click', _saveActiveSection);

    // Snapshot
    document.querySelector('.pw-version-section')?.addEventListener('click', async () => {
      if (!_activeSection) return;
      const content = document.getElementById('pw-section-content')?.value || '';
      const summary = prompt('Change summary (optional):') || '';
      await _post(`/api/proposal-sections/${_activeSection.id}/versions`,
                  { content, change_summary: summary });
      _showSaveStatus('Snapshot saved');
    });

    // Auto-save on typing
    document.getElementById('pw-section-content')?.addEventListener('input', (e) => {
      _updateWordCount(e.target.value);
      clearTimeout(_autoSaveTimer);
      _autoSaveTimer = setTimeout(_saveActiveSection, 3000);
    });

    // Comments toggle
    document.querySelector('.pw-comments-toggle')?.addEventListener('click', () => {
      const panel = document.getElementById('pw-comments-panel');
      if (panel) {
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden') && _activeSection) {
          ProposalComments?.loadForSection(_activeSection.id);
        }
      }
    });

    // Post comment
    document.getElementById('pw-post-comment')?.addEventListener('click', async () => {
      const input = document.getElementById('pw-new-comment');
      const text = input?.value?.trim();
      if (!text || !_activeSection) return;
      await _post(`/api/proposal-sections/${_activeSection.id}/comments`,
                  { author: 'User', content: text });
      if (input) input.value = '';
      ProposalComments?.loadForSection(_activeSection.id);
    });

    // LLM actions
    document.querySelectorAll('.pw-llm-action').forEach(btn => {
      btn.addEventListener('click', () => _runLlmAction(btn.dataset.action));
    });

    // Apply LLM result to section
    document.getElementById('pw-llm-apply')?.addEventListener('click', () => {
      const result = document.getElementById('pw-llm-result')?.textContent || '';
      const ta = document.getElementById('pw-section-content');
      if (ta && result) {
        ta.value = result;
        _updateWordCount(result);
        document.getElementById('pw-llm-result')?.classList.add('hidden');
        document.getElementById('pw-llm-result-actions')?.classList.add('hidden');
        _saveActiveSection();
      }
    });

    // Dismiss LLM result
    document.getElementById('pw-llm-dismiss')?.addEventListener('click', () => {
      document.getElementById('pw-llm-result')?.classList.add('hidden');
      document.getElementById('pw-llm-result-actions')?.classList.add('hidden');
    });
  }

  // ---------------------------------------------------------------------------
  // Document actions
  // ---------------------------------------------------------------------------
  async function _selectDoc(docId) {
    const res = await _get(`/api/proposal-docs/${docId}`);
    _activeDoc = res.document || null;
    _activeSection = null;
    _render();
  }

  async function _reloadDoc() {
    if (!_activeDoc) return;
    await _selectDoc(_activeDoc.id);
  }

  function _showAddDocModal() {
    const typeOptions = _docTypes.map(t =>
      `<option value="${t.key}">${_esc(t.label)}</option>`).join('');
    const html = `
      <div class="space-y-3">
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Document Title</label>
          <input id="pw-new-doc-title" type="text" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500" placeholder="e.g. Technical Volume"/>
        </div>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Document Type</label>
          <select id="pw-new-doc-type" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500">
            ${typeOptions}
          </select>
        </div>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Word Limit (optional)</label>
          <input id="pw-new-doc-limit" type="number" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none" placeholder="e.g. 5000"/>
        </div>
      </div>`;
    _showModal('New Proposal Document', html, async () => {
      const title = document.getElementById('pw-new-doc-title')?.value?.trim();
      const docType = document.getElementById('pw-new-doc-type')?.value;
      const wordLimit = parseInt(document.getElementById('pw-new-doc-limit')?.value || '0') || null;
      if (!title) return;
      await _post('/api/proposal-docs', {
        proposal_id: _proposalId, doc_type: docType, title, word_limit: wordLimit
      });
      await _loadDocuments();
      _render();
    });
  }

  function _showAddSectionModal() {
    const html = `
      <div class="space-y-3">
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Section Title</label>
          <input id="pw-new-sec-title" type="text" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"/>
        </div>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Section Number (e.g. 1.2)</label>
          <input id="pw-new-sec-num" type="text" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none"/>
        </div>
      </div>`;
    _showModal('New Section', html, async () => {
      const title = document.getElementById('pw-new-sec-title')?.value?.trim();
      const secNum = document.getElementById('pw-new-sec-num')?.value?.trim();
      if (!title || !_activeDoc) return;
      await _post(`/api/proposal-docs/${_activeDoc.id}/sections`, {
        title, section_number: secNum
      });
      await _reloadDoc();
    });
  }

  // ---------------------------------------------------------------------------
  // Stage snapshot
  // ---------------------------------------------------------------------------
  function _showStageSnapshotModal() {
    if (!_activeDoc) return;
    const html = `
      <div class="space-y-3">
        <p class="text-xs text-zinc-400">Snapshot every section in <strong class="text-zinc-200">${_esc(_activeDoc.title)}</strong> at the selected review stage. Only sections with content are snapshotted.</p>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Review Stage</label>
          <select id="pw-snap-stage" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none">
            <option value="pink">Pink Team</option>
            <option value="red" selected>Red Team</option>
            <option value="gold">Gold Team</option>
            <option value="final">Final</option>
          </select>
        </div>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Author (optional)</label>
          <input id="pw-snap-author" type="text" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none" placeholder="e.g. Red Team Lead"/>
        </div>
      </div>`;
    _showModal('Stage Snapshot', html, async () => {
      const stage = document.getElementById('pw-snap-stage')?.value || 'red';
      const author = document.getElementById('pw-snap-author')?.value?.trim() || '';
      const res = await _post(`/api/proposal-docs/${_activeDoc.id}/stage-snapshot`, {
        review_stage: stage, created_by: author
      });
      _showSaveStatus(`Snapshotted ${res.sections_snapshotted ?? 0} section(s) @ ${stage}`);
    });
  }

  // ---------------------------------------------------------------------------
  // Color team review upload
  // ---------------------------------------------------------------------------
  async function _showColorTeamUploadModal(file) {
    const html = `
      <div class="space-y-3">
        <div class="text-xs text-zinc-400 bg-zinc-800 rounded p-2">File: <strong class="text-zinc-200">${_esc(file.name)}</strong></div>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Review Stage</label>
          <select id="pw-ct-stage" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none">
            <option value="pink">Pink Team</option>
            <option value="red" selected>Red Team</option>
            <option value="gold">Gold Team</option>
            <option value="final">Final Review</option>
          </select>
        </div>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Author Prefix (optional)</label>
          <input id="pw-ct-prefix" type="text" placeholder="e.g. Red Team" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none"/>
        </div>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Ollama Model</label>
          <input id="pw-ct-model" type="text" value="qwen2.5:3b" class="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none"/>
        </div>
        <p class="text-xs text-zinc-500">Comments will be extracted, matched to sections, linked to compliance requirements, and rated automatically.</p>
      </div>`;
    _showModal('Upload Color Team Review', html, async () => {
      const stage = document.getElementById('pw-ct-stage')?.value || 'red';
      const prefix = document.getElementById('pw-ct-prefix')?.value?.trim() || '';
      const model = document.getElementById('pw-ct-model')?.value?.trim() || 'llama3';
      await _doColorTeamUpload(file, stage, prefix, model);
    });
  }

  async function _doColorTeamUpload(file, stage, prefix, model) {
    if (!_activeDoc) return;
    const form = new FormData();
    form.append('file', file);
    form.append('opportunity_id', _opportunityId);
    form.append('review_stage', stage);
    form.append('author_prefix', prefix);
    form.append('model', model);

    // Show progress indicator in compliance panel
    const panel = document.getElementById('pw-compliance-panel');
    const content = document.getElementById('pw-compliance-content');
    if (panel && content) {
      panel.classList.remove('hidden');
      content.innerHTML = '<span class="text-zinc-500">Uploading…</span>';
    }

    try {
      const res = await fetch(`/api/proposal-docs/${_activeDoc.id}/color-team-upload`, {
        method: 'POST', body: form
      });
      const data = await res.json();

      if (data.status === 'accepted' && data.job_id) {
        // Server accepted the job — poll until done
        if (content) content.innerHTML = '<span class="text-zinc-400">Processing review comments…</span>';
        await _pollColorTeamJob(data.job_id, file.name, content);
      } else if (data.error) {
        if (content) content.innerHTML = `<span class="text-red-400">Error: ${_esc(data.error)}</span>`;
      }
    } catch (err) {
      if (content) content.innerHTML = `<span class="text-red-400">Network error: ${_esc(String(err))}</span>`;
    }
  }

  async function _pollColorTeamJob(jobId, filename, contentEl) {
    const MAX_POLLS = 120;   // 2 minutes at 1s interval
    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise(r => setTimeout(r, 1000));
      try {
        const job = await _get(`/api/color-team-jobs/${jobId}`);
        if (contentEl) {
          contentEl.innerHTML = `<span class="text-zinc-400">${_esc(job.progress || 'Processing…')}</span>`;
        }
        if (job.status === 'done') {
          const result = job.result || {};
          await _loadComplianceAssessment();
          if (contentEl) {
            contentEl.insertAdjacentHTML('afterbegin',
              `<div class="mb-2 text-green-400 font-medium">Ingested ${result.ingested ?? 0} comment(s) from ${_esc(filename)}. ${result.skipped ?? 0} skipped.</div>`
            );
          }
          return;
        }
        if (job.status === 'error') {
          if (contentEl) contentEl.innerHTML = `<span class="text-red-400">Error: ${_esc(job.error || 'Unknown error')}</span>`;
          return;
        }
      } catch { /* network blip — keep polling */ }
    }
    if (contentEl) contentEl.innerHTML = '<span class="text-amber-400">Timed out waiting for results. Refresh to check compliance panel.</span>';
  }

  // ---------------------------------------------------------------------------
  // Compliance assessment
  // ---------------------------------------------------------------------------

  const _RATING_COLORS = {
    Outstanding:   'text-emerald-400 bg-emerald-950/40 border-emerald-800/50',
    Good:          'text-blue-400 bg-blue-950/40 border-blue-800/50',
    Acceptable:    'text-zinc-300 bg-zinc-800 border-zinc-600',
    Marginal:      'text-amber-400 bg-amber-950/40 border-amber-800/50',
    Unacceptable:  'text-red-400 bg-red-950/40 border-red-800/50',
  };

  async function _loadComplianceAssessment() {
    if (!_activeDoc) return;
    const content = document.getElementById('pw-compliance-content');
    if (!content) return;
    content.innerHTML = '<span class="text-zinc-500">Loading…</span>';

    const data = await _get(`/api/proposal-docs/${_activeDoc.id}/compliance-assessment`);
    if (data.error) {
      content.innerHTML = `<span class="text-red-400">${_esc(data.error)}</span>`;
      return;
    }

    const assessment = data.assessment || [];
    const summary = data.summary || {};
    const byRating = summary.by_rating || {};

    if (assessment.length === 0) {
      content.innerHTML = '<span class="text-zinc-500">No color team review comments yet. Upload a reviewed .docx to generate an assessment.</span>';
      return;
    }

    // Summary bar
    const ratingOrder = ['Unacceptable', 'Marginal', 'Acceptable', 'Good', 'Outstanding'];
    const summaryHtml = ratingOrder
      .filter(r => (byRating[r] || 0) > 0)
      .map(r => {
        const cls = _RATING_COLORS[r] || 'text-zinc-400';
        return `<span class="px-2 py-0.5 rounded border text-xs font-medium ${cls}">${byRating[r]} ${r}</span>`;
      }).join(' ');

    // Requirement rows
    const rowsHtml = assessment.map(entry => {
      const cls = _RATING_COLORS[entry.worst_rating] || 'text-zinc-400 bg-zinc-800 border-zinc-600';
      const reqText = entry.requirement_text
        ? `<div class="text-zinc-400 mt-0.5 truncate">${_esc(entry.requirement_text.substring(0, 120))}…</div>`
        : '';
      return `
        <div class="border rounded p-2 ${cls}">
          <div class="flex items-center gap-2">
            <span class="font-semibold text-xs">${_esc(entry.worst_rating)}</span>
            ${entry.section ? `<span class="text-xs opacity-70">${_esc(entry.section)}</span>` : ''}
            <span class="ml-auto text-xs opacity-60">${entry.comment_count} comment${entry.comment_count !== 1 ? 's' : ''}</span>
          </div>
          ${reqText}
        </div>`;
    }).join('');

    content.innerHTML = `
      <div class="flex flex-wrap gap-1 mb-3">${summaryHtml}</div>
      <div class="space-y-1.5">${rowsHtml}</div>`;
  }

  // ---------------------------------------------------------------------------
  // Section actions
  // ---------------------------------------------------------------------------
  async function _selectSection(sectionId) {
    const flat = _flatSections(_activeDoc?.sections || []);
    _activeSection = flat.find(s => s.id === sectionId) || null;
    _render();
    if (_activeSection) {
      ProposalComments?.reset();
    }
  }

  function _flatSections(sections) {
    const out = [];
    const walk = (list) => list.forEach(s => { out.push(s); walk(s.children || []); });
    walk(sections);
    return out;
  }

  async function _saveActiveSection() {
    if (!_activeSection) return;
    const content = document.getElementById('pw-section-content')?.value || '';
    const res = await _put(`/api/proposal-sections/${_activeSection.id}`, { content });
    if (res.section) {
      _activeSection = res.section;
      _showSaveStatus('Saved');
    }
  }

  // ---------------------------------------------------------------------------
  // LLM
  // ---------------------------------------------------------------------------
  async function _fetchComplianceRequirements() {
    if (!_opportunityId) return [];
    try {
      const res = await _get(`/api/shredding/requirements/${_opportunityId}?limit=50`);
      const reqs = res.requirements || [];
      // Return source_text strings for the LLM prompt
      return reqs.map(r => `[${r.section || '?'}] ${r.source_text || ''}`).filter(Boolean);
    } catch {
      return [];
    }
  }

  async function _runLlmAction(action) {
    if (!_activeSection) {
      _setLlmStatus('Select a section first.');
      return;
    }
    _setLlmStatus(`Running ${action}…`);
    document.getElementById('pw-llm-result')?.classList.add('hidden');
    document.getElementById('pw-llm-result-actions')?.classList.add('hidden');

    // For compliance_check, auto-populate requirements from shredding output
    let complianceRequirements = [];
    if (action === 'compliance_check') {
      _setLlmStatus('Loading RFP requirements…');
      complianceRequirements = await _fetchComplianceRequirements();
      _setLlmStatus(`Running ${action} (${complianceRequirements.length} requirements)…`);
    }

    const res = await _post(`/api/proposal-sections/${_activeSection.id}/llm`, {
      action,
      proposal_title: _proposalTitle,
      doc_type: _activeDoc?.doc_type || '',
      win_themes: _winThemes,
      compliance_requirements: complianceRequirements,
    });

    _setLlmStatus('');
    const resultEl = document.getElementById('pw-llm-result');
    const actionsEl = document.getElementById('pw-llm-result-actions');
    if (res.result && resultEl) {
      resultEl.textContent = res.result;
      resultEl.classList.remove('hidden');
      if (action !== 'plan' && action !== 'compliance_check' && actionsEl) {
        actionsEl.classList.remove('hidden');
      }
    } else if (res.error) {
      _setLlmStatus(`Error: ${res.error}`);
    }
  }

  function _setLlmStatus(msg) {
    const el = document.getElementById('pw-llm-status');
    if (el) el.textContent = msg;
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function _updateWordCount(text) {
    const wc = _wordCount(text);
    const el = document.getElementById('pw-word-count');
    if (el) el.textContent = `${wc} words`;
  }

  function _wordCount(text) {
    return text ? text.trim().split(/\s+/).filter(Boolean).length : 0;
  }

  function _showSaveStatus(msg) {
    const el = document.getElementById('pw-save-status');
    if (!el) return;
    el.textContent = msg;
    setTimeout(() => { el.textContent = ''; }, 2000);
  }

  function _esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Generic modal (reuses any existing modal infra; falls back to a simple overlay)
  function _showModal(title, bodyHtml, onConfirm) {
    const id = 'pw-generic-modal';
    document.getElementById(id)?.remove();
    const el = document.createElement('div');
    el.id = id;
    el.className = 'fixed inset-0 bg-black/60 flex items-center justify-center z-50';
    el.innerHTML = `
      <div class="bg-zinc-900 border border-zinc-700 rounded-xl p-6 w-full max-w-md shadow-xl">
        <h3 class="font-semibold text-white mb-4">${_esc(title)}</h3>
        ${bodyHtml}
        <div class="flex gap-2 mt-4 justify-end">
          <button id="pw-modal-cancel" class="text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-300 px-4 py-2 rounded">Cancel</button>
          <button id="pw-modal-confirm" class="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">Create</button>
        </div>
      </div>`;
    document.body.appendChild(el);
    document.getElementById('pw-modal-cancel').addEventListener('click', () => el.remove());
    document.getElementById('pw-modal-confirm').addEventListener('click', async () => {
      await onConfirm();
      el.remove();
    });
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return { init };
})();
