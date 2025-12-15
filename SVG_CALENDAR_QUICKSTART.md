# SVG Calendar - Quick Start Guide

**Get started with the dynamic SVG calendar in 2 minutes!**

---

## Access the Calendar

1. **Start the server:**
   ```bash
   uv run server.py
   ```

2. **Open browser:**
   ```
   http://localhost:9090
   ```

3. **Navigate to Opportunities:**
   - Click "Lists" in the sidebar (to expand)
   - Click "Opportunities" (shows expand arrow)
   - The Opportunities area will open

4. **Toggle Calendar View:**
   - Click the "Calendar View" button (top-right)
   - The SVG calendar will render!

---

## Using the Calendar

### Switch Views

Click the view mode buttons at the top:
- **Week** - See hourly schedule for 7 days
- **Month** - See full month with opportunity badges
- **Year** - See all 12 months at once

### Navigate Time

Use the navigation buttons:
- **← Prev** - Go back one period
- **Today** - Jump to current date
- **Next →** - Go forward one period

### Interact with Events

1. **Click any opportunity** (colored rectangle) to open dropdown
2. **Dropdown options:**
   - Change status (open, in progress, won, lost)
   - Pick a custom color
   - Edit full details
   - Close dropdown

### Visual Guide

**Color Meanings:**
- 🔵 Blue = Open
- 🟡 Amber = In Progress
- 🟢 Green = Won
- 🔴 Red = Lost

**Badges:**
- Small circles with numbers = Count of opportunities that day

---

## Create Test Opportunities

**Via API:**
```bash
curl -X POST http://localhost:9090/api/opportunities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q4 Enterprise Deal",
    "status": "open",
    "priority": "high",
    "value": 250000,
    "tags": ["enterprise", "high-value"]
  }'
```

**Via UI:**
1. Click "New Opportunity" button
2. Fill in the form
3. Click "Save Opportunity"
4. Calendar auto-updates!

---

## Tips & Tricks

### Real-Time Updates
- Calendar auto-refreshes every 30 seconds
- Create opportunities and watch them appear!

### Quick Navigation
```javascript
// In browser console:
app.opportunitiesManager.calendarManager.viewMode = 'year';
app.opportunitiesManager.calendarManager.render();
```

### Today Highlighting
- Current day has blue background (month view)
- Current day has blue text (week view)
- Current day has blue circle (year view)

### Click Interactions
- **Month view cells** - Click date to see details
- **Week view cells** - Click time slot to create event
- **Year view** - Visual overview only

---

## Troubleshooting

**Calendar not showing?**
- Check console for errors: `F12 > Console`
- Verify script loaded: Look for `svg_calendar_manager.js` in Network tab
- Refresh page: `Ctrl+R` or `Cmd+R`

**Events not appearing?**
- Check opportunities exist: `curl http://localhost:9090/api/opportunities`
- Check date matching: Events show on their `created_at` date
- Force reload: Click "Calendar View" twice (toggle off/on)

**Dropdown not working?**
- Check if opportunity has valid ID
- Look for JavaScript errors in console
- Try refreshing page

---

## Browser Support

✅ **Supported:**
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

⚠️ **Partial:**
- Internet Explorer (SVG support limited)

---

## Next Steps

1. **Customize colors** - Edit `this.colors` in `svg_calendar_manager.js`
2. **Add more opportunities** - Use the API or UI
3. **Explore views** - Try week/month/year modes
4. **Read full docs** - See `SVG_CALENDAR_DOCUMENTATION.md`

---

## Quick Reference

### Keyboard Shortcuts (Future)
*To be implemented:*
- `←/→` - Navigate prev/next
- `T` - Jump to today
- `W/M/Y` - Switch to week/month/year
- `Esc` - Close dropdown

### API Quick Reference
```bash
# List all
GET /api/opportunities

# Create
POST /api/opportunities
Body: { name, description, status, priority, value, tags }

# Update
POST /api/opportunities/{id}
Body: { field: value }

# Delete
DELETE /api/opportunities/{id}
```

---

**Ready to build? The calendar is live at http://localhost:9090!**

🎨 Built with SVG, JavaScript, and zero dependencies.
📚 Based on Sarah Drasner's interactive data visualization techniques.
