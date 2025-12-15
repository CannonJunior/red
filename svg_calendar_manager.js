/**
 * SVG Calendar Manager
 *
 * Dynamic SVG-based calendar with real-time data integration.
 * Inspired by Sarah Drasner's work on interactive data visualization.
 *
 * Features:
 * - Week/Month/Year views
 * - Live Opportunities integration
 * - Interactive dropdowns for configuration
 * - Animated transitions
 * - Event editing capabilities
 */

class SVGCalendarManager {
    constructor(containerId = 'svg-calendar-container') {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.viewMode = 'month'; // 'week', 'month', 'year'
        this.currentDate = new Date();
        this.opportunities = [];
        this.selectedEvent = null;
        this.colors = {
            open: '#3B82F6',      // Blue
            in_progress: '#F59E0B', // Amber
            won: '#10B981',        // Green
            lost: '#EF4444'        // Red
        };
        this.svgNS = 'http://www.w3.org/2000/svg';
        this.init();
    }

    init() {
        if (!this.container) {
            console.error(`Container ${this.containerId} not found`);
            return;
        }
        this.createSVGStructure();
        this.setupEventListeners();
        this.loadOpportunities();
        this.render();
    }

    createSVGStructure() {
        // Create main SVG element with viewBox for responsiveness
        this.svg = document.createElementNS(this.svgNS, 'svg');
        this.svg.setAttribute('viewBox', '0 0 1200 800');
        this.svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
        this.svg.style.width = '100%';
        this.svg.style.height = '100%';
        this.svg.style.border = '1px solid #e5e7eb';
        this.svg.style.borderRadius = '8px';
        this.svg.style.background = '#ffffff';

        // Create groups for organization
        this.headerGroup = this.createGroup('header-group');
        this.calendarGroup = this.createGroup('calendar-group');
        this.eventsGroup = this.createGroup('events-group');
        this.controlsGroup = this.createGroup('controls-group');
        this.dropdownGroup = this.createGroup('dropdown-group');

        this.svg.appendChild(this.headerGroup);
        this.svg.appendChild(this.calendarGroup);
        this.svg.appendChild(this.eventsGroup);
        this.svg.appendChild(this.controlsGroup);
        this.svg.appendChild(this.dropdownGroup);

        this.container.appendChild(this.svg);
    }

    createGroup(id) {
        const group = document.createElementNS(this.svgNS, 'g');
        group.setAttribute('id', id);
        return group;
    }

    setupEventListeners() {
        // Will be populated with specific event handlers
    }

    async loadOpportunities() {
        try {
            const response = await fetch('/api/opportunities', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.opportunities = data.opportunities || [];
                this.render();
            }
        } catch (error) {
            console.error('Error loading opportunities:', error);
        }
    }

    render() {
        this.clearGroups();
        this.renderHeader();
        this.renderControls();

        switch(this.viewMode) {
            case 'week':
                this.renderWeekView();
                break;
            case 'month':
                this.renderMonthView();
                break;
            case 'year':
                this.renderYearView();
                break;
        }

        this.renderEvents();
    }

    clearGroups() {
        this.headerGroup.innerHTML = '';
        this.calendarGroup.innerHTML = '';
        this.eventsGroup.innerHTML = '';
        this.controlsGroup.innerHTML = '';
        this.dropdownGroup.innerHTML = '';
    }

    renderHeader() {
        // Background rectangle
        const headerBg = this.createRect(0, 0, 1200, 80, '#1F2937');
        this.headerGroup.appendChild(headerBg);

        // Title text
        const title = this.getHeaderTitle();
        const titleText = this.createText(title, 60, 50, {
            fontSize: '32px',
            fontWeight: 'bold',
            fill: '#FFFFFF',
            fontFamily: 'system-ui, -apple-system, sans-serif'
        });
        this.headerGroup.appendChild(titleText);

        // Current date display
        const dateStr = this.currentDate.toLocaleDateString('en-US', {
            month: 'long',
            year: 'numeric'
        });
        const dateText = this.createText(dateStr, 60, 70, {
            fontSize: '16px',
            fill: '#9CA3AF',
            fontFamily: 'system-ui, -apple-system, sans-serif'
        });
        this.headerGroup.appendChild(dateText);
    }

    renderControls() {
        const controlsY = 15;
        const buttonWidth = 100;
        const buttonHeight = 40;
        const gap = 10;
        let startX = 800;

        // View mode buttons
        const modes = ['Week', 'Month', 'Year'];
        modes.forEach((mode, index) => {
            const x = startX + (buttonWidth + gap) * index;
            const isActive = this.viewMode === mode.toLowerCase();

            const button = this.createButton(
                x, controlsY, buttonWidth, buttonHeight,
                mode, isActive
            );

            button.addEventListener('click', () => {
                this.viewMode = mode.toLowerCase();
                this.render();
            });

            this.controlsGroup.appendChild(button);
        });

        // Navigation buttons
        const navY = controlsY + 50;
        const prevButton = this.createNavButton(startX, navY, '← Prev');
        prevButton.addEventListener('click', () => this.navigate(-1));
        this.controlsGroup.appendChild(prevButton);

        const todayButton = this.createNavButton(startX + 110, navY, 'Today');
        todayButton.addEventListener('click', () => {
            this.currentDate = new Date();
            this.render();
        });
        this.controlsGroup.appendChild(todayButton);

        const nextButton = this.createNavButton(startX + 220, navY, 'Next →');
        nextButton.addEventListener('click', () => this.navigate(1));
        this.controlsGroup.appendChild(nextButton);
    }

    createButton(x, y, width, height, text, isActive = false) {
        const group = document.createElementNS(this.svgNS, 'g');
        group.style.cursor = 'pointer';

        const rect = this.createRect(x, y, width, height,
            isActive ? '#3B82F6' : '#FFFFFF',
            isActive ? '' : '#D1D5DB'
        );
        rect.setAttribute('rx', '6');

        const textEl = this.createText(text, x + width / 2, y + height / 2 + 6, {
            fontSize: '14px',
            fill: isActive ? '#FFFFFF' : '#374151',
            textAnchor: 'middle',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontWeight: '500'
        });

        group.appendChild(rect);
        group.appendChild(textEl);

        // Hover effect
        group.addEventListener('mouseenter', () => {
            if (!isActive) {
                rect.setAttribute('fill', '#F3F4F6');
            }
        });
        group.addEventListener('mouseleave', () => {
            if (!isActive) {
                rect.setAttribute('fill', '#FFFFFF');
            }
        });

        return group;
    }

    createNavButton(x, y, text) {
        return this.createButton(x, y, 100, 36, text, false);
    }

    renderWeekView() {
        const startX = 60;
        const startY = 140;
        const dayWidth = 160;
        const hourHeight = 40;
        const days = this.getWeekDays();

        // Draw day headers
        days.forEach((day, index) => {
            const x = startX + index * dayWidth;

            // Header background
            const headerRect = this.createRect(x, startY, dayWidth - 2, 60, '#F3F4F6', '#E5E7EB');
            this.calendarGroup.appendChild(headerRect);

            // Day name
            const dayText = this.createText(day.name, x + dayWidth / 2, startY + 25, {
                fontSize: '14px',
                fontWeight: '600',
                textAnchor: 'middle',
                fill: '#374151'
            });
            this.calendarGroup.appendChild(dayText);

            // Date number
            const dateText = this.createText(day.date.toString(), x + dayWidth / 2, startY + 48, {
                fontSize: '20px',
                fontWeight: 'bold',
                textAnchor: 'middle',
                fill: day.isToday ? '#3B82F6' : '#111827'
            });
            this.calendarGroup.appendChild(dateText);
        });

        // Draw time grid (8 AM to 6 PM)
        const hours = Array.from({length: 11}, (_, i) => i + 8);
        const gridY = startY + 60;

        hours.forEach((hour, index) => {
            const y = gridY + index * hourHeight;

            // Time label
            const timeText = this.createText(
                `${hour % 12 || 12}${hour >= 12 ? 'PM' : 'AM'}`,
                35, y + 25, {
                    fontSize: '12px',
                    fill: '#6B7280',
                    textAnchor: 'end'
                }
            );
            this.calendarGroup.appendChild(timeText);

            // Grid lines
            days.forEach((day, dayIndex) => {
                const x = startX + dayIndex * dayWidth;
                const cell = this.createRect(x, y, dayWidth - 2, hourHeight, '#FFFFFF', '#E5E7EB');
                cell.style.cursor = 'pointer';

                // Click to create event
                cell.addEventListener('click', () => {
                    this.showEventCreator(day.date, hour);
                });

                this.calendarGroup.appendChild(cell);
            });
        });
    }

    renderMonthView() {
        const startX = 60;
        const startY = 140;
        const cellWidth = 160;
        const cellHeight = 100;
        const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

        // Draw day of week headers
        daysOfWeek.forEach((day, index) => {
            const x = startX + index * cellWidth;
            const text = this.createText(day, x + cellWidth / 2, startY + 25, {
                fontSize: '14px',
                fontWeight: '600',
                textAnchor: 'middle',
                fill: '#6B7280'
            });
            this.calendarGroup.appendChild(text);
        });

        // Get calendar grid for current month
        const calendar = this.getMonthCalendar();
        const gridStartY = startY + 40;

        calendar.forEach((week, weekIndex) => {
            week.forEach((day, dayIndex) => {
                const x = startX + dayIndex * cellWidth;
                const y = gridStartY + weekIndex * cellHeight;

                // Cell background
                const isCurrentMonth = day.month === this.currentDate.getMonth();
                const isToday = this.isToday(day.date);

                const cell = this.createRect(x, y, cellWidth - 2, cellHeight - 2,
                    isToday ? '#EFF6FF' : '#FFFFFF',
                    '#E5E7EB'
                );
                cell.style.cursor = 'pointer';

                cell.addEventListener('click', () => {
                    this.showDayDetails(day.date);
                });

                this.calendarGroup.appendChild(cell);

                // Date number
                const dateText = this.createText(day.date.getDate().toString(),
                    x + 15, y + 25, {
                        fontSize: isToday ? '18px' : '16px',
                        fontWeight: isToday ? 'bold' : '500',
                        fill: isCurrentMonth ? (isToday ? '#3B82F6' : '#111827') : '#9CA3AF'
                    });
                this.calendarGroup.appendChild(dateText);

                // Count opportunities for this day
                const dayOpportunities = this.getOpportunitiesForDate(day.date);
                if (dayOpportunities.length > 0) {
                    const badge = this.createCircle(x + cellWidth - 20, y + 15, 10, this.colors.open);
                    const badgeText = this.createText(
                        dayOpportunities.length.toString(),
                        x + cellWidth - 20, y + 19, {
                            fontSize: '10px',
                            fill: '#FFFFFF',
                            textAnchor: 'middle',
                            fontWeight: 'bold'
                        }
                    );
                    this.calendarGroup.appendChild(badge);
                    this.calendarGroup.appendChild(badgeText);
                }
            });
        });
    }

    renderYearView() {
        const startX = 40;
        const startY = 140;
        const monthWidth = 280;
        const monthHeight = 200;
        const months = 12;
        const cols = 4;

        for (let month = 0; month < months; month++) {
            const col = month % cols;
            const row = Math.floor(month / cols);
            const x = startX + col * monthWidth;
            const y = startY + row * monthHeight;

            this.renderMiniMonth(x, y, month, monthWidth - 20, monthHeight - 20);
        }
    }

    renderMiniMonth(x, y, monthIndex, width, height) {
        // Month background
        const bg = this.createRect(x, y, width, height, '#FAFAFA', '#E5E7EB');
        bg.setAttribute('rx', '8');
        this.calendarGroup.appendChild(bg);

        // Month name
        const monthName = new Date(this.currentDate.getFullYear(), monthIndex, 1)
            .toLocaleDateString('en-US', { month: 'long' });
        const title = this.createText(monthName, x + width / 2, y + 25, {
            fontSize: '14px',
            fontWeight: '600',
            textAnchor: 'middle',
            fill: '#111827'
        });
        this.calendarGroup.appendChild(title);

        // Mini calendar grid
        const cellWidth = width / 7;
        const cellHeight = (height - 40) / 6;
        const gridY = y + 35;

        // Day headers
        const days = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
        days.forEach((day, index) => {
            const dayText = this.createText(day, x + (index + 0.5) * cellWidth, gridY + 12, {
                fontSize: '10px',
                fill: '#6B7280',
                textAnchor: 'middle'
            });
            this.calendarGroup.appendChild(dayText);
        });

        // Get calendar for this month
        const tempDate = new Date(this.currentDate.getFullYear(), monthIndex, 1);
        const calendar = this.getMonthCalendarForDate(tempDate);

        calendar.forEach((week, weekIndex) => {
            week.forEach((day, dayIndex) => {
                const cellX = x + dayIndex * cellWidth;
                const cellY = gridY + 20 + weekIndex * cellHeight;

                if (day.month === monthIndex) {
                    const isToday = this.isToday(day.date);

                    // Day cell
                    if (isToday) {
                        const circle = this.createCircle(
                            cellX + cellWidth / 2,
                            cellY + cellHeight / 2,
                            8,
                            '#3B82F6'
                        );
                        this.calendarGroup.appendChild(circle);
                    }

                    const dateText = this.createText(
                        day.date.getDate().toString(),
                        cellX + cellWidth / 2,
                        cellY + cellHeight / 2 + 4,
                        {
                            fontSize: '11px',
                            fill: isToday ? '#FFFFFF' : '#374151',
                            textAnchor: 'middle'
                        }
                    );
                    this.calendarGroup.appendChild(dateText);

                    // Opportunity indicator
                    const dayOpps = this.getOpportunitiesForDate(day.date);
                    if (dayOpps.length > 0) {
                        const dot = this.createCircle(
                            cellX + cellWidth / 2,
                            cellY + cellHeight - 5,
                            2,
                            this.colors.open
                        );
                        this.calendarGroup.appendChild(dot);
                    }
                }
            });
        });
    }

    renderEvents() {
        // Render opportunities as events on the calendar
        this.opportunities.forEach(opp => {
            const oppDate = new Date(opp.created_at);

            if (this.viewMode === 'month' && this.isDateInCurrentMonth(oppDate)) {
                this.renderMonthEvent(opp, oppDate);
            } else if (this.viewMode === 'week' && this.isDateInCurrentWeek(oppDate)) {
                this.renderWeekEvent(opp, oppDate);
            }
        });
    }

    renderMonthEvent(opp, date) {
        // Find the cell position for this date
        const calendar = this.getMonthCalendar();
        const startX = 60;
        const startY = 180;
        const cellWidth = 160;
        const cellHeight = 100;

        calendar.forEach((week, weekIndex) => {
            week.forEach((day, dayIndex) => {
                if (this.isSameDay(day.date, date)) {
                    const x = startX + dayIndex * cellWidth + 5;
                    const y = startY + weekIndex * cellHeight + 35;

                    // Event rectangle
                    const eventRect = this.createRect(x, y, cellWidth - 12, 20,
                        this.colors[opp.status], '', 0.9);
                    eventRect.setAttribute('rx', '4');
                    eventRect.style.cursor = 'pointer';

                    // Event text
                    const eventText = this.createText(
                        this.truncate(opp.name, 18),
                        x + 5, y + 14, {
                            fontSize: '11px',
                            fill: '#FFFFFF',
                            fontWeight: '500'
                        }
                    );

                    eventRect.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this.showEventDropdown(opp, x, y);
                    });

                    this.eventsGroup.appendChild(eventRect);
                    this.eventsGroup.appendChild(eventText);
                }
            });
        });
    }

    renderWeekEvent(opp, date) {
        // Similar to month event but positioned in week grid
        const days = this.getWeekDays();
        const startX = 60;
        const startY = 200;
        const dayWidth = 160;
        const hourHeight = 40;

        days.forEach((day, index) => {
            if (this.isSameDay(day.fullDate, date)) {
                const x = startX + index * dayWidth + 5;
                const hour = date.getHours();
                const y = startY + (hour - 8) * hourHeight + 5;

                const eventRect = this.createRect(x, y, dayWidth - 12, 30,
                    this.colors[opp.status], '', 0.9);
                eventRect.setAttribute('rx', '4');
                eventRect.style.cursor = 'pointer';

                const eventText = this.createText(
                    this.truncate(opp.name, 16),
                    x + 5, y + 20, {
                        fontSize: '12px',
                        fill: '#FFFFFF',
                        fontWeight: '500'
                    }
                );

                eventRect.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.showEventDropdown(opp, x, y);
                });

                this.eventsGroup.appendChild(eventRect);
                this.eventsGroup.appendChild(eventText);
            }
        });
    }

    showEventDropdown(opp, x, y) {
        this.dropdownGroup.innerHTML = '';
        this.selectedEvent = opp;

        // Dropdown background
        const dropdownWidth = 250;
        const dropdownHeight = 200;
        const dropX = Math.min(x, 950);
        const dropY = Math.min(y, 600);

        // Background
        const bg = this.createRect(dropX, dropY, dropdownWidth, dropdownHeight, '#FFFFFF', '#D1D5DB');
        bg.setAttribute('rx', '8');
        bg.setAttribute('filter', 'drop-shadow(0 4px 6px rgba(0,0,0,0.1))');
        this.dropdownGroup.appendChild(bg);

        // Close button
        const closeBtn = this.createText('×', dropX + dropdownWidth - 20, dropY + 25, {
            fontSize: '24px',
            fill: '#6B7280',
            cursor: 'pointer',
            fontWeight: 'bold'
        });
        closeBtn.addEventListener('click', () => {
            this.dropdownGroup.innerHTML = '';
        });
        this.dropdownGroup.appendChild(closeBtn);

        // Title
        const titleText = this.createText(opp.name, dropX + 15, dropY + 30, {
            fontSize: '16px',
            fontWeight: 'bold',
            fill: '#111827'
        });
        this.dropdownGroup.appendChild(titleText);

        // Status selector
        const statusLabel = this.createText('Status:', dropX + 15, dropY + 60, {
            fontSize: '12px',
            fill: '#6B7280'
        });
        this.dropdownGroup.appendChild(statusLabel);

        const statuses = ['open', 'in_progress', 'won', 'lost'];
        statuses.forEach((status, index) => {
            const statusBtn = this.createButton(
                dropX + 15 + index * 55,
                dropY + 70,
                50,
                24,
                status.replace('_', ' '),
                opp.status === status
            );

            statusBtn.addEventListener('click', async () => {
                await this.updateOpportunity(opp.id, { status });
                this.dropdownGroup.innerHTML = '';
                await this.loadOpportunities();
            });

            this.dropdownGroup.appendChild(statusBtn);
        });

        // Color picker
        const colorLabel = this.createText('Color:', dropX + 15, dropY + 110, {
            fontSize: '12px',
            fill: '#6B7280'
        });
        this.dropdownGroup.appendChild(colorLabel);

        const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];
        colors.forEach((color, index) => {
            const colorCircle = this.createCircle(
                dropX + 25 + index * 40,
                dropY + 130,
                10,
                color
            );
            colorCircle.style.cursor = 'pointer';
            colorCircle.addEventListener('click', () => {
                // Update color in metadata
                this.updateOpportunity(opp.id, {
                    metadata: { ...opp.metadata, color }
                });
            });
            this.dropdownGroup.appendChild(colorCircle);
        });

        // View/Edit button
        const editBtn = this.createButton(dropX + 15, dropY + 155, 100, 30, 'Edit Details', false);
        editBtn.addEventListener('click', () => {
            if (window.app?.opportunitiesManager) {
                window.app.opportunitiesManager.editCurrentOpportunity();
                window.app.navigation.navigateTo('opportunities');
            }
        });
        this.dropdownGroup.appendChild(editBtn);
    }

    async updateOpportunity(id, updates) {
        try {
            const response = await fetch(`/api/opportunities/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });

            if (response.ok) {
                await this.loadOpportunities();
            }
        } catch (error) {
            console.error('Error updating opportunity:', error);
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

    createCircle(cx, cy, r, fill = '#3B82F6') {
        const circle = document.createElementNS(this.svgNS, 'circle');
        circle.setAttribute('cx', cx);
        circle.setAttribute('cy', cy);
        circle.setAttribute('r', r);
        circle.setAttribute('fill', fill);
        return circle;
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

    getHeaderTitle() {
        switch(this.viewMode) {
            case 'week': return 'Week View';
            case 'month': return 'Month View';
            case 'year': return 'Year View';
            default: return 'Calendar';
        }
    }

    getWeekDays() {
        const start = this.getWeekStart(this.currentDate);
        const days = [];

        for (let i = 0; i < 7; i++) {
            const date = new Date(start);
            date.setDate(start.getDate() + i);
            days.push({
                name: date.toLocaleDateString('en-US', { weekday: 'short' }),
                date: date.getDate(),
                fullDate: date,
                isToday: this.isToday(date)
            });
        }

        return days;
    }

    getWeekStart(date) {
        const d = new Date(date);
        const day = d.getDay();
        const diff = d.getDate() - day;
        return new Date(d.setDate(diff));
    }

    getMonthCalendar() {
        return this.getMonthCalendarForDate(this.currentDate);
    }

    getMonthCalendarForDate(date) {
        const year = date.getFullYear();
        const month = date.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);

        const calendar = [];
        let week = [];

        // Fill beginning of first week
        const startDay = firstDay.getDay();
        for (let i = startDay - 1; i >= 0; i--) {
            const d = new Date(year, month, -i);
            week.push({ date: d, month: d.getMonth() });
        }

        // Fill month days
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const d = new Date(year, month, day);
            week.push({ date: d, month });

            if (week.length === 7) {
                calendar.push(week);
                week = [];
            }
        }

        // Fill end of last week
        let nextMonthDay = 1;
        while (week.length < 7 && week.length > 0) {
            const d = new Date(year, month + 1, nextMonthDay++);
            week.push({ date: d, month: d.getMonth() });
        }
        if (week.length > 0) calendar.push(week);

        return calendar;
    }

    getOpportunitiesForDate(date) {
        return this.opportunities.filter(opp => {
            const oppDate = new Date(opp.created_at);
            return this.isSameDay(oppDate, date);
        });
    }

    isSameDay(date1, date2) {
        return date1.getDate() === date2.getDate() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getFullYear() === date2.getFullYear();
    }

    isToday(date) {
        return this.isSameDay(date, new Date());
    }

    isDateInCurrentMonth(date) {
        return date.getMonth() === this.currentDate.getMonth() &&
               date.getFullYear() === this.currentDate.getFullYear();
    }

    isDateInCurrentWeek(date) {
        const weekStart = this.getWeekStart(this.currentDate);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 7);
        return date >= weekStart && date < weekEnd;
    }

    navigate(direction) {
        switch(this.viewMode) {
            case 'week':
                this.currentDate.setDate(this.currentDate.getDate() + (direction * 7));
                break;
            case 'month':
                this.currentDate.setMonth(this.currentDate.getMonth() + direction);
                break;
            case 'year':
                this.currentDate.setFullYear(this.currentDate.getFullYear() + direction);
                break;
        }
        this.render();
    }

    truncate(str, maxLength) {
        return str.length > maxLength ? str.substring(0, maxLength - 3) + '...' : str;
    }

    showDayDetails(date) {
        const opportunities = this.getOpportunitiesForDate(date);
        console.log(`${date.toDateString()}: ${opportunities.length} opportunities`);
        // Could expand this to show a detail panel
    }

    showEventCreator(date, hour) {
        console.log(`Create event for ${date} at ${hour}:00`);
        // Could show a form to create new opportunity
    }

    // Auto-refresh for real-time updates
    startAutoRefresh(intervalMs = 30000) {
        this.refreshInterval = setInterval(() => {
            this.loadOpportunities();
        }, intervalMs);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.SVGCalendarManager = SVGCalendarManager;
}
