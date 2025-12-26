# Dynamic SVG Calendar - Technical Documentation

**Created:** 2025-12-13
**Based on:** Sarah Drasner's SVG animation techniques and modern data visualization patterns

---

## Overview

A fully dynamic, SVG-based calendar application with real-time Opportunities integration. Built using pure SVG and JavaScript with no external dependencies, inspired by Sarah Drasner's work on interactive data visualization.

## Research Foundation

### Sources
- [Interactive Data Visualization: Animating the viewBox | CSS-Tricks](https://css-tricks.com/interactive-data-visualization-animating-viewbox/)
- [SVG Animations - Sarah Drasner](https://www.oreilly.com/library/view/svg-animations/9781491939697/)
- [Frontend Masters - SVG Essentials & Animation](https://frontendmasters.com/courses/svg-essentials-animation/)
- [Dynamic SVG - data.europa.eu](https://data.europa.eu/apps/data-visualisation-guide/dynamic-svg)
- [Angular SVG Components](https://briantree.se/dynamic-and-interactive-angular-svg-components/)

### Key Principles Applied
1. **SVG as Math-Based Graphics** - Enables precise data-driven positioning
2. **viewBox for Responsiveness** - Scalable across devices without quality loss
3. **DOM Manipulation** - Real-time updates via JavaScript
4. **Data Binding** - Opportunities API integration
5. **Performance** - Minimal redraws, efficient event handling

---

## Architecture

### File Structure
```
/home/junior/src/red/
├── svg_calendar_manager.js    (900+ lines) - Main calendar engine
├── index.html                  (updated) - Calendar container
└── app.js                      (updated) - Integration layer
```

### Core Components

#### 1. SVGCalendarManager Class
```javascript
class SVGCalendarManager {
    constructor(containerId)
    viewMode: 'week' | 'month' | 'year'
    opportunities: Array
    colors: Object
    svgNS: 'http://www.w3.org/2000/svg'
}
```

#### 2. SVG Structure
```
<svg viewBox="0 0 1200 800">
  <g id="header-group">     <!-- Title, date display -->
  <g id="calendar-group">   <!-- Grid, cells, dates -->
  <g id="events-group">     <!-- Opportunity markers -->
  <g id="controls-group">   <!-- Navigation buttons -->
  <g id="dropdown-group">   <!-- Configuration menus -->
</svg>
```

---

## Features

### 1. Three View Modes

#### Week View
- **Grid:** 7 columns (Sun-Sat) × 10 hours (8 AM - 6 PM)
- **Cell Size:** 160px × 40px
- **Features:**
  - Hourly time slots
  - Current day highlighting
  - Event positioning by hour
  - Click cells to create events

#### Month View
- **Grid:** 7 columns × 5-6 rows
- **Cell Size:** 160px × 100px
- **Features:**
  - Full month calendar
  - Date navigation
  - Opportunity count badges
  - Today highlighting (blue background)
  - Current month vs. other month styling

#### Year View
- **Grid:** 4 columns × 3 rows (12 months)
- **Cell Size:** 280px × 200px (each mini-month)
- **Features:**
  - Mini calendars for each month
  - Opportunity indicators (dots)
  - Quick month overview
  - Year-at-a-glance view

### 2. Live Data Integration

#### Real-Time Opportunities
```javascript
async loadOpportunities() {
    const response = await fetch('/api/opportunities', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
    });
    this.opportunities = data.opportunities;
    this.render();
}
```

#### Auto-Refresh
```javascript
startAutoRefresh(intervalMs = 30000) // Every 30 seconds
```

#### Event Rendering
- **Color Coding:**
  - Open: Blue (#3B82F6)
  - In Progress: Amber (#F59E0B)
  - Won: Green (#10B981)
  - Lost: Red (#EF4444)

### 3. Interactive Dropdowns

When clicking an opportunity event, a dropdown appears with:

#### Configuration Options
1. **Status Selector**
   - 4 status buttons (open, in_progress, won, lost)
   - Immediate API update on click
   - Visual feedback with active state

2. **Color Picker**
   - 5 preset colors
   - Stored in opportunity metadata
   - Instant visual update

3. **Icons & Actions**
   - Edit Details button → Opens full opportunity editor
   - Close button (× icon)
   - Delete confirmation

#### Dropdown Implementation
```javascript
showEventDropdown(opp, x, y) {
    // Dropdown with shadow, rounded corners
    // Position-aware (stays within viewport)
    // Click handlers for each option
    // Auto-close on outside click
}
```

### 4. Navigation Controls

#### View Mode Switcher
```
[Week] [Month] [Year]
```
- Active state highlighting
- Smooth transitions
- Preserves current date context

#### Date Navigation
```
[← Prev]  [Today]  [Next →]
```
- Week: ±7 days
- Month: ±1 month
- Year: ±1 year

---

## Technical Implementation

### SVG Element Creation Pattern

```javascript
createRect(x, y, width, height, fill, stroke, opacity) {
    const rect = document.createElementNS(this.svgNS, 'rect');
    rect.setAttribute('x', x);
    rect.setAttribute('y', y);
    // ... set attributes
    return rect;
}
```

### Event Positioning Algorithm

#### Month View
```javascript
calendar.forEach((week, weekIndex) => {
    week.forEach((day, dayIndex) => {
        const x = startX + dayIndex * cellWidth;
        const y = startY + weekIndex * cellHeight;
        // Position events within cell
    });
});
```

#### Week View
```javascript
const hour = date.getHours();
const y = startY + (hour - 8) * hourHeight;
// Position events by time
```

### Data Binding Strategy

1. **Fetch** - Load opportunities from API
2. **Map** - Match opportunities to date cells
3. **Render** - Create SVG elements for each event
4. **Update** - Re-render on data changes

### Performance Optimizations

1. **Grouped Rendering** - Use SVG groups for batch operations
2. **Selective Redraws** - Only update changed sections
3. **Event Delegation** - Minimal event listeners
4. **ViewBox Scaling** - Hardware-accelerated transforms

---

## Usage

### Basic Integration

```javascript
// Initialize in OpportunitiesManager
this.calendarManager = new SVGCalendarManager('svg-calendar-container');
this.calendarManager.startAutoRefresh();
```

### Toggle Between Views

```javascript
toggleCalendarView() {
    if (!this.calendarManager) {
        this.calendarManager = new SVGCalendarManager();
    }
    // Show/hide calendar vs list view
}
```

### Access from Browser Console

```javascript
// Switch views
app.opportunitiesManager.calendarManager.viewMode = 'year';
app.opportunitiesManager.calendarManager.render();

// Navigate
app.opportunitiesManager.calendarManager.navigate(1); // Next period

// Load fresh data
app.opportunitiesManager.calendarManager.loadOpportunities();
```

---

## API Integration

### Opportunities Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/opportunities` | Load all opportunities |
| POST | `/api/opportunities/{id}` | Update opportunity |
| POST | `/api/opportunities` | Create new opportunity |

### Data Structure Expected

```javascript
{
    id: "uuid",
    name: "Opportunity Name",
    status: "open|in_progress|won|lost",
    priority: "low|medium|high",
    value: 100000,
    tags: ["tag1", "tag2"],
    metadata: { color: "#3B82F6" },
    created_at: "2025-12-13T08:33:39.962099",
    updated_at: "2025-12-13T08:33:39.962099"
}
```

---

## Advanced Features

### Responsive Design

```javascript
viewBox="0 0 1200 800"
preserveAspectRatio="xMidYMid meet"
```
- Scales to any container size
- Maintains aspect ratio
- Works on mobile/tablet/desktop

### Animation Potential

Ready for future enhancements:
- Transition between view modes
- Event drag-and-drop
- Hover effects with CSS
- Loading states

### Extensibility

Easy to add:
- Recurring events
- Multi-day events
- Custom color schemes
- Export to iCal
- Print view
- Keyboard navigation

---

## Debugging

### Console Commands

```javascript
// Check current state
console.log(app.opportunitiesManager.calendarManager.viewMode);
console.log(app.opportunitiesManager.calendarManager.opportunities);

// Force render
app.opportunitiesManager.calendarManager.render();

// Inspect SVG
document.querySelector('#svg-calendar-container svg');
```

### Common Issues

1. **Events not showing**
   - Check date parsing: `new Date(opp.created_at)`
   - Verify opportunities loaded: `this.opportunities.length`

2. **Dropdown positioning off-screen**
   - Auto-adjusted: `dropX = Math.min(x, 950)`

3. **Auto-refresh not working**
   - Check if started: `this.refreshInterval`
   - Restart: `startAutoRefresh()`

---

## Future Enhancements

### Planned Features
1. **Drag-and-Drop** - Move events between dates/times
2. **Multi-Select** - Bulk operations on events
3. **Filters** - By status, priority, tags
4. **Search** - Find specific opportunities
5. **Export** - Download as iCal, PDF, PNG
6. **Themes** - Dark mode, color schemes
7. **Animations** - Smooth transitions using Sarah Drasner's techniques

### Code Improvements
1. Virtual scrolling for year view
2. Web Workers for large datasets
3. SVG sprite sheets for icons
4. CSS animations for hover effects

---

## Credits & References

**Inspired by:**
- Sarah Drasner's SVG Animations work
- CSS-Tricks interactive data visualization tutorials
- Modern data-driven SVG techniques

**Technologies:**
- Pure JavaScript (ES6+)
- SVG 2.0
- Fetch API
- DOM manipulation

---

## License

Part of the RED RAG system - Zero-cost, locally-running architecture.

**Last Updated:** 2025-12-13
**Status:** ✅ Production Ready
