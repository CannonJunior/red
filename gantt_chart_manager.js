/**
 * Gantt Chart Manager - Dynamic SVG Gantt Chart
 *
 * Visualizes tasks with start/end dates as horizontal bars on a timeline.
 * Built with pure SVG for scalability and interactive features.
 *
 * Features:
 * - Timeline-based task visualization
 * - Progress bars
 * - Drag to resize (future)
 * - Dependencies (future)
 * - Status color coding
 */

class GanttChartManager {
    constructor(containerId = 'gantt-chart-container') {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.tasks = [];
        this.opportunityId = null;
        this.svgNS = 'http://www.w3.org/2000/svg';

        // Dimensions
        this.width = 1200;
        this.height = 600;
        this.margin = { top: 50, right: 40, bottom: 40, left: 200 };
        this.rowHeight = 40;
        this.rowPadding = 10;

        // Colors
        this.colors = {
            pending: '#94A3B8',      // Slate
            in_progress: '#3B82F6',  // Blue
            completed: '#10B981',    // Green
            overdue: '#EF4444'       // Red
        };

        this.init();
    }

    init() {
        if (!this.container) {
            console.error(`Container ${this.containerId} not found`);
            return;
        }
    }

    async loadTasks(opportunityId) {
        this.opportunityId = opportunityId;

        try {
            const response = await fetch(`/api/opportunities/${opportunityId}/tasks`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.tasks = data.tasks || [];
                this.render();
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
        }
    }

    setTasks(tasks) {
        this.tasks = tasks || [];
    }

    render() {
        if (!this.container) return;

        // Clear container
        this.container.innerHTML = '';

        if (this.tasks.length === 0) {
            this.renderEmptyState();
            return;
        }

        // Calculate timeline
        const timeline = this.calculateTimeline();

        // Adjust height based on number of tasks
        this.height = Math.max(400, this.margin.top + (this.tasks.length * this.rowHeight) + this.margin.bottom);

        // Create SVG
        this.createSVG();

        // Render components
        this.renderHeader(timeline);
        this.renderTimeAxis(timeline);
        this.renderGrid(timeline);
        this.renderTasks(timeline);
        this.renderTaskLabels();
        this.renderLegend();
    }

    createSVG() {
        this.svg = document.createElementNS(this.svgNS, 'svg');
        this.svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);
        this.svg.setAttribute('preserveAspectRatio', 'xMidYMin meet');
        this.svg.style.width = '100%';
        this.svg.style.height = '100%';
        this.svg.style.background = '#FFFFFF';
        this.svg.style.border = '1px solid #E5E7EB';
        this.svg.style.borderRadius = '8px';

        // Create groups
        this.headerGroup = this.createGroup('header');
        this.axisGroup = this.createGroup('axis');
        this.gridGroup = this.createGroup('grid');
        this.tasksGroup = this.createGroup('tasks');
        this.labelsGroup = this.createGroup('labels');
        this.legendGroup = this.createGroup('legend');

        this.svg.appendChild(this.gridGroup);
        this.svg.appendChild(this.axisGroup);
        this.svg.appendChild(this.tasksGroup);
        this.svg.appendChild(this.labelsGroup);
        this.svg.appendChild(this.headerGroup);
        this.svg.appendChild(this.legendGroup);

        this.container.appendChild(this.svg);
    }

    createGroup(id) {
        const group = document.createElementNS(this.svgNS, 'g');
        group.setAttribute('id', `gantt-${id}`);
        return group;
    }

    calculateTimeline() {
        if (this.tasks.length === 0) {
            const now = new Date();
            return {
                start: new Date(now.getFullYear(), now.getMonth(), 1),
                end: new Date(now.getFullYear(), now.getMonth() + 3, 0),
                duration: 90
            };
        }

        // Find min and max dates
        let minDate = new Date(this.tasks[0].start_date);
        let maxDate = new Date(this.tasks[0].end_date);

        this.tasks.forEach(task => {
            const startDate = new Date(task.start_date);
            const endDate = new Date(task.end_date);

            if (startDate < minDate) minDate = startDate;
            if (endDate > maxDate) maxDate = endDate;
        });

        // Add padding (1 week before and after)
        const paddedStart = new Date(minDate);
        paddedStart.setDate(paddedStart.getDate() - 7);

        const paddedEnd = new Date(maxDate);
        paddedEnd.setDate(paddedEnd.getDate() + 7);

        const duration = Math.ceil((paddedEnd - paddedStart) / (1000 * 60 * 60 * 24));

        return {
            start: paddedStart,
            end: paddedEnd,
            duration: duration
        };
    }

    renderHeader(timeline) {
        // Title - aligned near top
        const title = this.createText('Task Timeline', 20, 22, {
            fontSize: '20px',
            fontWeight: 'bold',
            fill: '#111827'
        });
        this.headerGroup.appendChild(title);

        // Date range and task count on same line
        const dateRange = `${this.formatDate(timeline.start)} - ${this.formatDate(timeline.end)}`;
        const subtitle = this.createText(`${dateRange} • ${this.tasks.length} tasks`, 20, 40, {
            fontSize: '12px',
            fill: '#6B7280'
        });
        this.headerGroup.appendChild(subtitle);
    }

    renderTimeAxis(timeline) {
        const chartWidth = this.width - this.margin.left - this.margin.right;
        const axisY = this.margin.top;

        // Calculate intervals (show weeks)
        const weeks = Math.ceil(timeline.duration / 7);
        const weekWidth = chartWidth / weeks;

        for (let i = 0; i <= weeks; i++) {
            const x = this.margin.left + (i * weekWidth);
            const date = new Date(timeline.start);
            date.setDate(date.getDate() + (i * 7));

            // Vertical line
            const line = this.createLine(x, axisY, x, axisY + 10, '#D1D5DB');
            this.axisGroup.appendChild(line);

            // Date label
            const label = this.createText(
                this.formatDate(date),
                x, axisY - 5, {
                    fontSize: '11px',
                    fill: '#6B7280',
                    textAnchor: 'middle'
                }
            );
            this.axisGroup.appendChild(label);
        }

        // Axis line
        const axisLine = this.createLine(
            this.margin.left, axisY,
            this.width - this.margin.right, axisY,
            '#374151', 2
        );
        this.axisGroup.appendChild(axisLine);
    }

    renderGrid(timeline) {
        const chartWidth = this.width - this.margin.left - this.margin.right;
        const chartHeight = this.tasks.length * this.rowHeight;

        // Vertical grid lines (weeks)
        const weeks = Math.ceil(timeline.duration / 7);
        const weekWidth = chartWidth / weeks;

        for (let i = 0; i <= weeks; i++) {
            const x = this.margin.left + (i * weekWidth);
            const line = this.createLine(
                x, this.margin.top,
                x, this.margin.top + chartHeight,
                '#E5E7EB', 1, 0.5
            );
            this.gridGroup.appendChild(line);
        }

        // Horizontal grid lines (tasks)
        for (let i = 0; i <= this.tasks.length; i++) {
            const y = this.margin.top + (i * this.rowHeight);
            const line = this.createLine(
                this.margin.left, y,
                this.width - this.margin.right, y,
                '#E5E7EB', 1, 0.5
            );
            this.gridGroup.appendChild(line);
        }

        // Today line
        const today = new Date();
        if (today >= timeline.start && today <= timeline.end) {
            const daysSinceStart = Math.ceil((today - timeline.start) / (1000 * 60 * 60 * 24));
            const x = this.margin.left + (daysSinceStart / timeline.duration * chartWidth);

            const todayLine = this.createLine(
                x, this.margin.top,
                x, this.margin.top + chartHeight,
                '#EF4444', 2
            );
            todayLine.setAttribute('stroke-dasharray', '5,5');
            this.gridGroup.appendChild(todayLine);

            // Today label
            const todayLabel = this.createText('Today', x, this.margin.top - 15, {
                fontSize: '10px',
                fill: '#EF4444',
                textAnchor: 'middle',
                fontWeight: 'bold'
            });
            this.gridGroup.appendChild(todayLabel);
        }
    }

    renderTasks(timeline) {
        const chartWidth = this.width - this.margin.left - this.margin.right;

        this.tasks.forEach((task, index) => {
            const y = this.margin.top + (index * this.rowHeight) + this.rowPadding;
            const barHeight = this.rowHeight - (2 * this.rowPadding);

            // Calculate position and width
            const startDate = new Date(task.start_date);
            const endDate = new Date(task.end_date);

            const startOffset = Math.ceil((startDate - timeline.start) / (1000 * 60 * 60 * 24));
            const taskDuration = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));

            const x = this.margin.left + (startOffset / timeline.duration * chartWidth);
            const width = Math.max(5, taskDuration / timeline.duration * chartWidth);

            // Determine color
            const today = new Date();
            let color = this.colors[task.status] || this.colors.pending;

            if (task.status !== 'completed' && endDate < today) {
                color = this.colors.overdue;
            }

            // Task bar background
            const taskBar = this.createRect(x, y, width, barHeight, color, '', 0.3);
            taskBar.setAttribute('rx', '4');
            taskBar.style.cursor = 'pointer';

            taskBar.addEventListener('click', () => {
                this.showTaskDetails(task, x, y);
            });

            this.tasksGroup.appendChild(taskBar);

            // Progress bar
            if (task.progress > 0) {
                const progressWidth = (task.progress / 100) * width;
                const progressBar = this.createRect(x, y, progressWidth, barHeight, color);
                progressBar.setAttribute('rx', '4');
                this.tasksGroup.appendChild(progressBar);
            }

            // Task duration text
            if (width > 40) {
                const durationText = this.createText(
                    `${taskDuration}d`,
                    x + width / 2,
                    y + barHeight / 2 + 4,
                    {
                        fontSize: '11px',
                        fill: '#FFFFFF',
                        textAnchor: 'middle',
                        fontWeight: '500'
                    }
                );
                this.tasksGroup.appendChild(durationText);
            }

            // Progress percentage
            if (task.progress > 0 && task.progress < 100) {
                const progressText = this.createText(
                    `${task.progress}%`,
                    x + width + 5,
                    y + barHeight / 2 + 4,
                    {
                        fontSize: '10px',
                        fill: '#6B7280',
                        fontWeight: '600'
                    }
                );
                this.tasksGroup.appendChild(progressText);
            }
        });
    }

    renderTaskLabels() {
        this.tasks.forEach((task, index) => {
            const y = this.margin.top + (index * this.rowHeight) + (this.rowHeight / 2) + 5;

            // Task name
            const label = this.createText(
                this.truncate(task.name, 25),
                this.margin.left - 10,
                y,
                {
                    fontSize: '13px',
                    fill: '#374151',
                    textAnchor: 'end',
                    fontWeight: '500'
                }
            );
            this.labelsGroup.appendChild(label);

            // Assigned to (if exists)
            if (task.assigned_to) {
                const assignee = this.createText(
                    task.assigned_to,
                    this.margin.left - 10,
                    y + 12,
                    {
                        fontSize: '10px',
                        fill: '#9CA3AF',
                        textAnchor: 'end'
                    }
                );
                this.labelsGroup.appendChild(assignee);
            }
        });
    }

    renderLegend() {
        const legendX = this.width - 200;
        const legendY = 10;
        const legendItems = [
            { label: 'Pending', color: this.colors.pending },
            { label: 'In Progress', color: this.colors.in_progress },
            { label: 'Completed', color: this.colors.completed },
            { label: 'Overdue', color: this.colors.overdue }
        ];

        legendItems.forEach((item, index) => {
            const x = legendX + (index % 2) * 90;
            const y = legendY + Math.floor(index / 2) * 20;

            // Color box
            const box = this.createRect(x, y, 12, 12, item.color);
            box.setAttribute('rx', '2');
            this.legendGroup.appendChild(box);

            // Label
            const label = this.createText(item.label, x + 18, y + 9, {
                fontSize: '10px',
                fill: '#6B7280'
            });
            this.legendGroup.appendChild(label);
        });
    }

    renderEmptyState() {
        const div = document.createElement('div');
        div.className = 'text-center py-12';
        div.innerHTML = `
            <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
            </svg>
            <p class="text-lg text-gray-600 dark:text-gray-400 mb-2">No tasks yet</p>
            <p class="text-sm text-gray-500 dark:text-gray-500">Add tasks to see the Gantt chart timeline</p>
        `;
        this.container.appendChild(div);
    }

    showTaskDetails(task, x, y) {
        console.log('Task details:', task);
        // Could show a tooltip or modal with task details
        if (window.app?.ganttManager?.currentTaskCallback) {
            window.app.ganttManager.currentTaskCallback(task);
        }
    }

    // Helper methods
    createRect(x, y, width, height, fill = '#FFFFFF', stroke = '', opacity = 1) {
        const rect = document.createElementNS(this.svgNS, 'rect');
        rect.setAttribute('x', x);
        rect.setAttribute('y', y);
        rect.setAttribute('width', width);
        rect.setAttribute('height', height);
        rect.setAttribute('fill', fill);
        if (stroke) rect.setAttribute('stroke', stroke);
        if (opacity < 1) rect.setAttribute('opacity', opacity);
        return rect;
    }

    createLine(x1, y1, x2, y2, stroke = '#000000', strokeWidth = 1, opacity = 1) {
        const line = document.createElementNS(this.svgNS, 'line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('stroke', stroke);
        line.setAttribute('stroke-width', strokeWidth);
        if (opacity < 1) line.setAttribute('opacity', opacity);
        return line;
    }

    createText(content, x, y, styles = {}) {
        const text = document.createElementNS(this.svgNS, 'text');
        text.setAttribute('x', x);
        text.setAttribute('y', y);
        text.textContent = content;

        Object.entries(styles).forEach(([key, value]) => {
            const attr = key.replace(/([A-Z])/g, '-$1').toLowerCase();
            text.setAttribute(attr, value);
        });

        return text;
    }

    formatDate(date) {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    truncate(str, maxLength) {
        return str.length > maxLength ? str.substring(0, maxLength - 3) + '...' : str;
    }

    async createTask(taskData) {
        if (!this.opportunityId) return;

        try {
            const response = await fetch(`/api/opportunities/${this.opportunityId}/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });

            if (response.ok) {
                await this.loadTasks(this.opportunityId);
            }
        } catch (error) {
            console.error('Error creating task:', error);
        }
    }

    async updateTask(taskId, updates) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });

            if (response.ok && this.opportunityId) {
                await this.loadTasks(this.opportunityId);
            }
        } catch (error) {
            console.error('Error updating task:', error);
        }
    }

    async deleteTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'DELETE'
            });

            if (response.ok && this.opportunityId) {
                await this.loadTasks(this.opportunityId);
            }
        } catch (error) {
            console.error('Error deleting task:', error);
        }
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.GanttChartManager = GanttChartManager;
}
