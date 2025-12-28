/**
 * Career Analysis List
 *
 * Handles display and filtering of career-monster analysis results
 */

class CareerAnalysisList {
    constructor() {
        this.results = [];
        this.filteredResults = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadResults();
    }

    setupEventListeners() {
        // Filter inputs
        const filters = [
            'filter-institution',
            'filter-department',
            'filter-phd-institution',
            'filter-min-score',
            'filter-min-pubs',
            'filter-min-citations',
            'filter-hire-year'
        ];

        filters.forEach(filterId => {
            const element = document.getElementById(filterId);
            if (element) {
                element.addEventListener('input', () => this.applyFilters());
            }
        });

        // Sort dropdown
        const sortBy = document.getElementById('career-sort-by');
        if (sortBy) {
            sortBy.addEventListener('change', () => this.applyFilters());
        }

        // Clear filters button
        const clearBtn = document.getElementById('clear-career-filters-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFilters());
        }

        // Export button
        const exportBtn = document.getElementById('export-career-list-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportToCSV());
        }
    }

    async loadResults() {
        try {
            const response = await fetch('/api/career/list');
            const data = await response.json();

            if (data.status === 'success') {
                this.results = data.results || [];
                this.applyFilters();
            } else {
                console.error('Failed to load career analysis results:', data.message);
            }
        } catch (error) {
            console.error('Error loading career analysis results:', error);
        }
    }

    applyFilters() {
        // Get filter values
        const filters = {
            institution: document.getElementById('filter-institution')?.value.toLowerCase() || '',
            department: document.getElementById('filter-department')?.value.toLowerCase() || '',
            phdInstitution: document.getElementById('filter-phd-institution')?.value.toLowerCase() || '',
            minScore: parseFloat(document.getElementById('filter-min-score')?.value) || 0,
            minPubs: parseInt(document.getElementById('filter-min-pubs')?.value) || 0,
            minCitations: parseInt(document.getElementById('filter-min-citations')?.value) || 0,
            hireYear: document.getElementById('filter-hire-year')?.value || ''
        };

        // Apply filters
        this.filteredResults = this.results.filter(result => {
            if (filters.institution && !result.institution.toLowerCase().includes(filters.institution)) {
                return false;
            }
            if (filters.department && !result.department.toLowerCase().includes(filters.department)) {
                return false;
            }
            if (filters.phdInstitution && !result.phd_institution.toLowerCase().includes(filters.phdInstitution)) {
                return false;
            }
            if (filters.minScore && result.overall_score < filters.minScore) {
                return false;
            }
            if (filters.minPubs && result.publications_count < filters.minPubs) {
                return false;
            }
            if (filters.minCitations && result.citations_count < filters.minCitations) {
                return false;
            }
            if (filters.hireYear && !result.hire_date.includes(filters.hireYear)) {
                return false;
            }
            return true;
        });

        // Apply sorting
        this.sortResults();

        // Render results
        this.renderResults();
    }

    sortResults() {
        const sortBy = document.getElementById('career-sort-by')?.value || 'score-desc';

        this.filteredResults.sort((a, b) => {
            switch (sortBy) {
                case 'score-desc':
                    return (b.overall_score || 0) - (a.overall_score || 0);
                case 'score-asc':
                    return (a.overall_score || 0) - (b.overall_score || 0);
                case 'date-desc':
                    return (b.hire_date || '').localeCompare(a.hire_date || '');
                case 'date-asc':
                    return (a.hire_date || '').localeCompare(b.hire_date || '');
                case 'institution-asc':
                    return (a.institution || '').localeCompare(b.institution || '');
                case 'pubs-desc':
                    return (b.publications_count || 0) - (a.publications_count || 0);
                default:
                    return 0;
            }
        });
    }

    renderResults() {
        const tbody = document.getElementById('career-results-tbody');
        const emptyState = document.getElementById('career-empty-state');
        const resultsCount = document.getElementById('career-results-count');

        if (!tbody) return;

        // Update count
        if (resultsCount) {
            resultsCount.textContent = this.filteredResults.length;
        }

        // Show/hide empty state
        if (this.filteredResults.length === 0) {
            tbody.innerHTML = '';
            if (emptyState) {
                emptyState.classList.remove('hidden');
            }
            return;
        }

        if (emptyState) {
            emptyState.classList.add('hidden');
        }

        // Render rows
        tbody.innerHTML = this.filteredResults.map((result, index) => this.renderRow(result, index)).join('');

        // Add event listeners to action buttons
        this.filteredResults.forEach((result, index) => {
            const viewBtn = document.getElementById(`view-result-${index}`);
            if (viewBtn) {
                viewBtn.addEventListener('click', () => this.viewDetails(result));
            }

            const removeBtn = document.getElementById(`remove-result-${index}`);
            if (removeBtn) {
                removeBtn.addEventListener('click', () => this.removeFromList(result.id));
            }
        });
    }

    renderRow(result, index) {
        // Score color coding
        let scoreClass = 'text-yellow-600 dark:text-yellow-400';
        if (result.overall_score >= 8) {
            scoreClass = 'text-green-600 dark:text-green-400';
        } else if (result.overall_score < 6) {
            scoreClass = 'text-red-600 dark:text-red-400';
        }

        return `
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td class="px-4 py-3">
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${result.candidate_name}</div>
                </td>
                <td class="px-4 py-3">
                    <div class="text-sm text-gray-900 dark:text-white">${result.institution}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">${result.department}</div>
                </td>
                <td class="px-4 py-3">
                    <div class="text-sm text-gray-900 dark:text-white">${result.phd_institution || 'N/A'}</div>
                    ${result.phd_year ? `<div class="text-xs text-gray-500 dark:text-gray-400">${result.phd_year}</div>` : ''}
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="text-sm font-semibold ${scoreClass}">${result.overall_score?.toFixed(1) || 'N/A'}</span>
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="text-sm text-gray-900 dark:text-white">${result.publications_count || 0}</span>
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="text-sm text-gray-900 dark:text-white">${result.citations_count || 0}</span>
                </td>
                <td class="px-4 py-3">
                    <span class="text-sm text-gray-900 dark:text-white">${result.hire_date || 'N/A'}</span>
                </td>
                <td class="px-4 py-3 text-center">
                    <div class="flex items-center justify-center space-x-2">
                        <button id="view-result-${index}" class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300" title="View Details">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                            </svg>
                        </button>
                        <button id="remove-result-${index}" class="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300" title="Remove from List">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    async viewDetails(result) {
        // Show details modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-semibold text-gray-900 dark:text-white">Career Analysis Details</h3>
                    <button class="close-modal p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>

                <div class="space-y-4">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Candidate</label>
                            <p class="text-gray-900 dark:text-white">${result.candidate_name}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Institution</label>
                            <p class="text-gray-900 dark:text-white">${result.institution} - ${result.department}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-700 dark:text-gray-300">PhD Institution</label>
                            <p class="text-gray-900 dark:text-white">${result.phd_institution || 'N/A'} (${result.phd_year || 'N/A'})</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Hire Date</label>
                            <p class="text-gray-900 dark:text-white">${result.hire_date || 'N/A'}</p>
                        </div>
                    </div>

                    <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
                        <h4 class="text-lg font-medium text-gray-900 dark:text-white mb-3">Alignment Scores</h4>
                        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                            <div class="text-center">
                                <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">${result.overall_score?.toFixed(1) || 'N/A'}</div>
                                <div class="text-xs text-gray-600 dark:text-gray-400">Overall</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-gray-900 dark:text-white">${result.topic_alignment?.toFixed(1) || 'N/A'}</div>
                                <div class="text-xs text-gray-600 dark:text-gray-400">Topic</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-gray-900 dark:text-white">${result.publication_strength?.toFixed(1) || 'N/A'}</div>
                                <div class="text-xs text-gray-600 dark:text-gray-400">Publications</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-gray-900 dark:text-white">${result.network_overlap?.toFixed(1) || 'N/A'}</div>
                                <div class="text-xs text-gray-600 dark:text-gray-400">Network</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-gray-900 dark:text-white">${result.methodology_match?.toFixed(1) || 'N/A'}</div>
                                <div class="text-xs text-gray-600 dark:text-gray-400">Methodology</div>
                            </div>
                        </div>
                    </div>

                    <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
                        <h4 class="text-lg font-medium text-gray-900 dark:text-white mb-3">Academic Profile</h4>
                        <div class="grid grid-cols-3 gap-4 text-center">
                            <div>
                                <div class="text-xl font-bold text-gray-900 dark:text-white">${result.publications_count || 0}</div>
                                <div class="text-sm text-gray-600 dark:text-gray-400">Publications</div>
                            </div>
                            <div>
                                <div class="text-xl font-bold text-gray-900 dark:text-white">${result.citations_count || 0}</div>
                                <div class="text-sm text-gray-600 dark:text-gray-400">Citations</div>
                            </div>
                            <div>
                                <div class="text-xl font-bold text-gray-900 dark:text-white">${result.confidence_score?.toFixed(2) || 'N/A'}</div>
                                <div class="text-sm text-gray-600 dark:text-gray-400">Confidence</div>
                            </div>
                        </div>
                    </div>

                    ${result.notes ? `
                    <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
                        <h4 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Notes</h4>
                        <p class="text-sm text-gray-700 dark:text-gray-300">${result.notes}</p>
                    </div>
                    ` : ''}
                </div>

                <div class="mt-6 flex justify-end space-x-3">
                    <button class="close-modal px-4 py-2 bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-400 dark:hover:bg-gray-500">
                        Close
                    </button>
                    <button class="view-full-assessment px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                        View Full Assessment
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close handlers
        const closeButtons = modal.querySelectorAll('.close-modal');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                modal.remove();
            });
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        // View Full Assessment handler
        const viewFullBtn = modal.querySelector('.view-full-assessment');
        if (viewFullBtn) {
            viewFullBtn.addEventListener('click', async () => {
                viewFullBtn.disabled = true;
                viewFullBtn.textContent = 'Loading...';

                try {
                    // Fetch full assessment data
                    const response = await fetch(`/api/career/assessments/${result.assessment_id}?full=true`);
                    const data = await response.json();

                    if (data.status === 'success') {
                        const assessment = data.assessment;
                        const narratives = assessment.narratives || {};
                        const successFactors = assessment.success_factors || [];
                        const redFlags = assessment.red_flags || [];

                        // Build full assessment HTML
                        let fullAssessmentHTML = '<div class="mt-6 border-t border-gray-200 dark:border-gray-700 pt-4">';

                        // Narratives
                        if (narratives.optimistic) {
                            fullAssessmentHTML += `
                                <div class="mb-4">
                                    <h4 class="text-md font-semibold text-green-600 dark:text-green-400 mb-2">🌟 Optimistic Perspective</h4>
                                    <p class="text-sm text-gray-700 dark:text-gray-300">${narratives.optimistic}</p>
                                </div>
                            `;
                        }

                        if (narratives.pessimistic) {
                            fullAssessmentHTML += `
                                <div class="mb-4">
                                    <h4 class="text-md font-semibold text-orange-600 dark:text-orange-400 mb-2">⚠️ Critical Perspective</h4>
                                    <p class="text-sm text-gray-700 dark:text-gray-300">${narratives.pessimistic}</p>
                                </div>
                            `;
                        }

                        if (narratives.pragmatic) {
                            fullAssessmentHTML += `
                                <div class="mb-4">
                                    <h4 class="text-md font-semibold text-blue-600 dark:text-blue-400 mb-2">⚖️ Pragmatic Perspective</h4>
                                    <p class="text-sm text-gray-700 dark:text-gray-300">${narratives.pragmatic}</p>
                                </div>
                            `;
                        }

                        if (narratives.speculative) {
                            fullAssessmentHTML += `
                                <div class="mb-4">
                                    <h4 class="text-md font-semibold text-purple-600 dark:text-purple-400 mb-2">🔮 Speculative Perspective</h4>
                                    <p class="text-sm text-gray-700 dark:text-gray-300">${narratives.speculative}</p>
                                </div>
                            `;
                        }

                        // Success Factors
                        if (successFactors.length > 0) {
                            fullAssessmentHTML += `
                                <div class="mb-4">
                                    <h4 class="text-md font-semibold text-green-600 dark:text-green-400 mb-2">✅ Success Factors</h4>
                                    <ul class="list-disc list-inside text-sm text-gray-700 dark:text-gray-300 space-y-1">
                                        ${successFactors.map(f => `<li>${f}</li>`).join('')}
                                    </ul>
                                </div>
                            `;
                        }

                        // Red Flags
                        if (redFlags.length > 0) {
                            fullAssessmentHTML += `
                                <div class="mb-4">
                                    <h4 class="text-md font-semibold text-red-600 dark:text-red-400 mb-2">🚩 Potential Concerns</h4>
                                    <ul class="list-disc list-inside text-sm text-gray-700 dark:text-gray-300 space-y-1">
                                        ${redFlags.map(f => `<li>${f}</li>`).join('')}
                                    </ul>
                                </div>
                            `;
                        }

                        fullAssessmentHTML += '</div>';

                        // Insert the full assessment before the button row
                        const buttonRow = modal.querySelector('.mt-6.flex.justify-end');
                        buttonRow.insertAdjacentHTML('beforebegin', fullAssessmentHTML);

                        // Update button
                        viewFullBtn.textContent = '✓ Full Assessment Loaded';
                        viewFullBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                        viewFullBtn.classList.add('bg-green-600', 'hover:bg-green-700');
                        viewFullBtn.disabled = true;
                    } else {
                        throw new Error(data.message || 'Failed to load assessment');
                    }
                } catch (error) {
                    console.error('Failed to load full assessment:', error);
                    alert('Failed to load full assessment. Please try again.');
                    viewFullBtn.disabled = false;
                    viewFullBtn.textContent = 'View Full Assessment';
                }
            });
        }
    }

    async removeFromList(id) {
        if (!confirm('Remove this result from the list?')) {
            return;
        }

        try {
            const response = await fetch(`/api/career/list/${id}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            if (data.status === 'success') {
                // Reload results
                await this.loadResults();
            } else {
                alert('Failed to remove result: ' + data.message);
            }
        } catch (error) {
            console.error('Error removing result:', error);
            alert('Error removing result');
        }
    }

    clearFilters() {
        document.getElementById('filter-institution').value = '';
        document.getElementById('filter-department').value = '';
        document.getElementById('filter-phd-institution').value = '';
        document.getElementById('filter-min-score').value = '';
        document.getElementById('filter-min-pubs').value = '';
        document.getElementById('filter-min-citations').value = '';
        document.getElementById('filter-hire-year').value = '';
        document.getElementById('career-sort-by').value = 'score-desc';

        this.applyFilters();
    }

    exportToCSV() {
        if (this.filteredResults.length === 0) {
            alert('No results to export');
            return;
        }

        // Create CSV content
        const headers = [
            'Candidate',
            'Institution',
            'Department',
            'PhD Institution',
            'PhD Year',
            'Overall Score',
            'Topic Alignment',
            'Publication Strength',
            'Network Overlap',
            'Methodology Match',
            'Publications',
            'Citations',
            'Hire Date',
            'Confidence'
        ];

        const rows = this.filteredResults.map(r => [
            r.candidate_name,
            r.institution,
            r.department,
            r.phd_institution || '',
            r.phd_year || '',
            r.overall_score?.toFixed(2) || '',
            r.topic_alignment?.toFixed(2) || '',
            r.publication_strength?.toFixed(2) || '',
            r.network_overlap?.toFixed(2) || '',
            r.methodology_match?.toFixed(2) || '',
            r.publications_count || 0,
            r.citations_count || 0,
            r.hire_date || '',
            r.confidence_score?.toFixed(2) || ''
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        // Download file
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `career-analysis-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    // Show the career analysis list area
    showCareerAnalysisList() {
        // Hide all other areas
        document.querySelectorAll('main[id$="-area"]').forEach(area => {
            area.classList.add('hidden');
        });

        // Show career analysis area
        const careerArea = document.getElementById('career-analysis-area');
        if (careerArea) {
            careerArea.classList.remove('hidden');
        }

        // Update page title
        const pageTitle = document.getElementById('page-title');
        if (pageTitle) {
            pageTitle.textContent = 'Career Analysis Results';
        }

        // Reload results
        this.loadResults();
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.careerList = new CareerAnalysisList();
    });
} else {
    window.careerList = new CareerAnalysisList();
}
