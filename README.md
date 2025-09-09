# Robobrain - Web Application: Red features

A basic web application with Open WebUI's look and feel, designed to add agentic UI features for day-to-day work assistance.

## Features

- **Modern UI Design**: Based on Open WebUI's clean, responsive interface
- **Dark/Light Mode**: Automatic theme detection with manual toggle
- **Responsive Layout**: Works on desktop and mobile devices
- **Chat Interface**: Ready for AI assistant integration
- **Modular Architecture**: Structured for easy extension

## Quick Start

1. **Start the server:**
   ```bash
   ./start.sh
   ```
   
   Or manually:
   ```bash
   uv run server.py
   ```

2. **Open in browser:**
   - Navigate to http://localhost:9090
   - The application will load automatically

## Architecture

### Frontend Structure
- `index.html` - Main application layout
- `styles.css` - Tailwind CSS with custom styling
- `app.js` - JavaScript application logic
- `robobrain.svg` - Logo and favicon

### Key Components
- **ThemeManager**: Handles dark/light mode switching
- **ChatInterface**: Manages message input and display
- **Navigation**: Sidebar navigation handling
- **IntegrationManager**: Placeholder for future API integrations

### Design System
- **Framework**: Tailwind CSS
- **Typography**: Inter font family
- **Colors**: Neutral grays with blue accents
- **Layout**: Sidebar + main content area
- **Responsive**: Mobile-first design

## Development

### File Structure
```
/home/junior/src/red/
├── index.html          # Main HTML file
├── styles.css          # Custom CSS styles
├── app.js             # JavaScript application
├── server.py          # Development server
├── start.sh           # Server start script (with port cleanup)
├── robobrain.svg      # Logo/favicon
├── MEMOIZE.md         # Project inputs
├── CLAUDE.md          # Development instructions
└── README.md          # This file
```

### Integration Points
The application includes placeholder functions for:
- API endpoint calls
- WebSocket connections
- Agent interactions
- File upload handling

### Server Configuration
- **Port**: 9090 (web application port)
- **CORS**: Enabled for development
- **Static Files**: Served from current directory
- **Routing**: Basic SPA routing support

## Future Enhancements

The application is structured to support:
- Real-time chat with AI agents
- File upload and processing
- Multi-modal interactions
- Advanced workflow commands
- Backend API integration

## Browser Compatibility

- Modern browsers with ES6+ support
- Chrome, Firefox, Safari, Edge
- Mobile browsers (iOS Safari, Chrome Mobile)

## Notes

This is a basic implementation focusing on UI/UX foundations. Backend integration and advanced features are structured but not implemented, following the requirement to add only what's necessary for the basic web application.
