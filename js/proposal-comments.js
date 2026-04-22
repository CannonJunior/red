/**
 * js/proposal-comments.js — Threaded comment panel for proposal sections.
 *
 * Works alongside proposal-writer.js.
 * Renders into #pw-comments-list.
 */

const ProposalComments = (() => {
  let _sectionId = null;
  let _comments = [];

  // ---------------------------------------------------------------------------
  // Load & render
  // ---------------------------------------------------------------------------
  async function loadForSection(sectionId) {
    _sectionId = sectionId;
    const res = await fetch(`/api/proposal-sections/${sectionId}/comments`);
    const data = await res.json();
    _comments = data.comments || [];
    _render();
  }

  function reset() {
    _sectionId = null;
    _comments = [];
  }

  function _render() {
    const container = document.getElementById('pw-comments-list');
    if (!container) return;

    if (_comments.length === 0) {
      container.innerHTML = '<p class="text-xs text-zinc-500">No comments yet.</p>';
      return;
    }

    container.innerHTML = _comments.map(c => _renderComment(c, 0)).join('');
    _attachHandlers(container);
  }

  function _renderComment(c, depth) {
    const replies = (c.replies || []).map(r => _renderComment(r, depth + 1)).join('');
    const resolvedClass = c.resolved ? 'opacity-50' : '';
    const borderColor = depth === 0 ? 'border-zinc-600' : 'border-zinc-700';
    const indent = depth * 12;

    return `
      <div class="prc-comment ${resolvedClass} border-l-2 ${borderColor} pl-2 mb-2 text-xs"
           style="margin-left:${indent}px" data-comment-id="${c.id}">
        <div class="flex items-center gap-2 mb-0.5">
          <span class="font-semibold text-zinc-300">${_esc(c.author)}</span>
          <span class="text-zinc-600">${_ts(c.created_at)}</span>
          ${c.review_stage ? `<span class="px-1 py-0.5 rounded text-zinc-400 bg-zinc-800">${_esc(c.review_stage)}</span>` : ''}
          ${c.resolved ? '<span class="text-green-500 text-xs">✓ resolved</span>' : ''}
        </div>
        ${c.anchor_text ? `<div class="text-zinc-500 italic mb-1">"${_esc(c.anchor_text)}"</div>` : ''}
        <div class="text-zinc-200 mb-1">${_esc(c.content)}</div>
        ${c.suggested_replacement ? `<div class="bg-green-950/40 border border-green-800/50 rounded p-1 mb-1 text-green-300">Suggestion: ${_esc(c.suggested_replacement)}</div>` : ''}
        <div class="flex gap-2 text-zinc-500">
          ${!c.resolved ? `<button class="prc-resolve hover:text-green-400" data-id="${c.id}">Resolve</button>` : ''}
          <button class="prc-reply hover:text-blue-400" data-id="${c.id}">Reply</button>
          <button class="prc-delete hover:text-red-400" data-id="${c.id}">Delete</button>
        </div>
        ${replies}
      </div>`;
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------
  function _attachHandlers(container) {
    container.querySelectorAll('.prc-resolve').forEach(btn => {
      btn.addEventListener('click', async () => {
        await fetch(`/api/proposal-comments/${btn.dataset.id}/resolve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ resolved_by: 'User' })
        });
        await loadForSection(_sectionId);
      });
    });

    container.querySelectorAll('.prc-delete').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Delete this comment?')) return;
        await fetch(`/api/proposal-comments/${btn.dataset.id}`, { method: 'DELETE' });
        await loadForSection(_sectionId);
      });
    });

    container.querySelectorAll('.prc-reply').forEach(btn => {
      btn.addEventListener('click', () => _showReplyInput(btn.dataset.id));
    });
  }

  function _showReplyInput(parentId) {
    // Remove any existing reply input
    document.querySelectorAll('.prc-reply-input-row').forEach(el => el.remove());

    const parentEl = document.querySelector(`[data-comment-id="${parentId}"]`);
    if (!parentEl) return;

    const row = document.createElement('div');
    row.className = 'prc-reply-input-row flex gap-1 mt-1 ml-3';
    row.innerHTML = `
      <input type="text" placeholder="Write a reply…"
             class="flex-1 bg-zinc-800 border border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100 focus:outline-none focus:border-blue-500"/>
      <button class="prc-send-reply text-xs bg-zinc-700 hover:bg-zinc-600 text-white px-2 py-1 rounded">Send</button>
      <button class="prc-cancel-reply text-xs text-zinc-500 hover:text-zinc-300 px-1">✕</button>`;
    parentEl.appendChild(row);

    row.querySelector('.prc-cancel-reply').addEventListener('click', () => row.remove());
    row.querySelector('.prc-send-reply').addEventListener('click', async () => {
      const text = row.querySelector('input').value.trim();
      if (!text) return;
      await fetch(`/api/proposal-sections/${_sectionId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          author: 'User',
          content: text,
          parent_comment_id: parentId,
        })
      });
      await loadForSection(_sectionId);
    });
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function _esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _ts(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return iso;
    }
  }

  // ---------------------------------------------------------------------------
  // Public
  // ---------------------------------------------------------------------------
  return { loadForSection, reset };
})();
