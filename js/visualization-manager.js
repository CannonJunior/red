// Visualization Manager
class VisualizationManager {
    constructor() {
        this.currentVisualization = null;
        this.container = null;
        this.init();
    }

    init() {
        this.container = document.getElementById('visualization-container');
        this.setupControls();
    }

    setupControls() {
        const vizTypeSelect = document.getElementById('viz-type');
        const refreshBtn = document.getElementById('refresh-viz');

        if (vizTypeSelect) {
            vizTypeSelect.addEventListener('change', (e) => {
                this.renderVisualization(e.target.value);
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                const vizType = vizTypeSelect ? vizTypeSelect.value : 'knowledge-graph';
                this.renderVisualization(vizType);
            });
        }
    }

    async renderVisualization(type) {
        if (!this.container) return;

        try {
            switch (type) {
                case 'knowledge-graph':
                    await this.renderKnowledgeGraph();
                    break;
                case 'performance-dashboard':
                    await this.renderPerformanceDashboard();
                    break;
                case 'search-explorer':
                    await this.renderSearchExplorer();
                    break;
                default:
                    this.showError('Unknown visualization type');
            }
        } catch (error) {
            console.error('Visualization error:', error);
            this.showError(`Failed to render ${type}: ${error.message}`);
        }
    }

    async renderKnowledgeGraph() {
        const response = await fetch('/api/visualizations/knowledge-graph');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load knowledge graph data');
        }

        this.clearContainer();

        if (data.entities.length === 0) {
            this.showEmptyState('No documents in knowledge base', 'Upload documents to see knowledge relationships');
            return;
        }

        // Create D3.js visualization
        await this.createD3KnowledgeGraph(data);
        this.showDetails(`Knowledge graph with ${data.entities.length} entities and ${data.relationships.length} relationships from ${data.metadata.data_source}`);
    }

    async renderPerformanceDashboard() {
        const response = await fetch('/api/visualizations/performance');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load performance data');
        }

        this.clearContainer();

        const metrics = data.metrics;
        const html = `
            <div class="grid grid-cols-2 md:grid-cols-3 gap-4 h-full">
                <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">${metrics.total_documents}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Documents</div>
                </div>
                <div class="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold text-green-600 dark:text-green-400">${metrics.total_chunks}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Vector Chunks</div>
                </div>
                <div class="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">${metrics.avg_chunks_per_doc.toFixed(1)}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Avg Chunks/Doc</div>
                </div>
                <div class="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg text-center col-span-2 md:col-span-3">
                    <div class="text-lg font-bold text-orange-600 dark:text-orange-400">${metrics.system_health.toUpperCase()}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">System Status • Data: ${metrics.data_source}</div>
                </div>
            </div>
        `;

        this.container.innerHTML = html;
        this.showDetails(`Performance dashboard showing real-time metrics from ${data.data_source}`);
    }

    async renderSearchExplorer() {
        const response = await fetch('/api/visualizations/search-results');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load search results');
        }

        this.clearContainer();

        if (data.search_results.length === 0) {
            this.showEmptyState('No search results available', 'Upload documents to enable search exploration');
            return;
        }

        const html = `
            <div class="h-full overflow-y-auto">
                <div class="mb-4 text-sm text-gray-600 dark:text-gray-400">
                    Query: "${data.query_info.query}" • ${data.search_results.length} results • ${data.query_info.execution_time}s
                </div>
                <div class="space-y-3">
                    ${data.search_results.map(result => `
                        <div class="p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                            <div class="flex items-start justify-between">
                                <div class="flex-1">
                                    <h4 class="font-medium text-gray-900 dark:text-white">${result.title}</h4>
                                    <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">${result.content}</p>
                                    <div class="text-xs text-gray-500 dark:text-gray-500 mt-2">
                                        Source: ${result.source} • Type: ${result.metadata.file_type}
                                    </div>
                                </div>
                                <div class="ml-4 text-right">
                                    <div class="text-sm font-medium text-blue-600 dark:text-blue-400">${(result.score * 100).toFixed(1)}%</div>
                                    <div class="text-xs text-gray-500 dark:text-gray-500">Relevance</div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        this.container.innerHTML = html;
        this.showDetails(`Search results explorer showing ${data.search_results.length} documents from ${data.data_source}`);
    }

    async createD3KnowledgeGraph(data) {
        // Ensure D3 is available
        if (typeof d3 === 'undefined') {
            await this.loadD3();
        }

        const width = 800;
        const height = 400;

        const svg = d3.select(this.container)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .style('border', '1px solid #e5e7eb')
            .style('border-radius', '8px')
            .style('background', 'white')
            .classed('dark:bg-gray-800 dark:border-gray-600', true);

        const nodes = data.entities;
        const links = data.relationships;

        // Create force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));

        // Create links
        const link = svg.append('g')
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.sqrt(d.weight * 5));

        // Create nodes
        const node = svg.append('g')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => this.dragstarted(event, d, simulation))
                .on('drag', this.dragged)
                .on('end', (event, d) => this.dragended(event, d, simulation)));

        // Add circles to nodes
        node.append('circle')
            .attr('r', d => 5 + (d.confidence * 15))
            .attr('fill', d => {
                const colors = {
                    'DOCUMENT': '#3b82f6',
                    'CATEGORY': '#10b981',
                    'CONCEPT': '#f59e0b'
                };
                return colors[d.type] || '#6b7280';
            })
            .attr('opacity', 0.8);

        // Add labels to nodes
        node.append('text')
            .text(d => d.name)
            .attr('dy', -20)
            .attr('text-anchor', 'middle')
            .style('font-family', 'Inter, sans-serif')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .attr('fill', 'currentColor');

        // Update positions on simulation tick
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    async loadD3() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://d3js.org/d3.v7.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    dragstarted(event, d, simulation) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragended(event, d, simulation) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    clearContainer() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }

    showEmptyState(title, message) {
        const html = `
            <div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                <div class="text-center">
                    <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                    </svg>
                    <h3 class="text-lg font-medium mb-2">${title}</h3>
                    <p class="text-sm">${message}</p>
                </div>
            </div>
        `;
        this.container.innerHTML = html;
    }

    showDetails(text) {
        const detailsElement = document.getElementById('details-content');
        const detailsContainer = document.getElementById('visualization-details');

        if (detailsElement && detailsContainer) {
            detailsElement.textContent = text;
            detailsContainer.classList.remove('hidden');
        }
    }

    showError(message) {
        console.error('Visualization error:', message);
        this.showEmptyState('Visualization Error', message);
    }
}
