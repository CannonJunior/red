# Project Memoization

## Project Overview
This project will add agentic UI features to help any user with their day-to-day work.

## Current Task Input
- Start with a very basic web application running locally
- Analyze HTML and CSS from https://github.com/open-webui/open-webui
- Implement basic web application with Open WebUI look and feel
- Structure JavaScript and integration functions (but don't implement beyond necessary)
- Add robobrain.svg to both display and favicon
- Run locally on port 9090 (changed from 8000)
- Use "uv run" command instead of "python3" for this project
- **Implement Chat interface with locally hosted Ollama model**
- Ollama service is already running with available models: qwen2.5:3b, incept5/llama3.1-claude:latest

## Chat Implementation Details
- Added `/api/chat` endpoint to server.py for Ollama integration
- Added `/api/models` endpoint to list available models
- Implemented real-time chat interface with message display
- Features: typing indicators, error handling, message history
- Uses qwen2.5:3b as default model for faster responses

## New UI Features Added
- **Models Page**: Complete model management interface with cards, descriptions, and selection
- **Settings Page**: Comprehensive settings with theme selection and chat configuration
- **Enhanced Theme Toggle**: Sun/moon icons with smooth transitions between light/dark modes
- **Navigation System**: Single-page app with smooth transitions between Chat, Models, and Settings
- **New Chat Button**: Clears conversation and starts fresh chat session
- **Responsive Design**: Mobile-friendly layout with grid adjustments

## Theme Toggle Implementation
- **Fixed Click Functionality**: Theme toggle button now properly switches between light and dark modes
- **Dynamic Icons**: Sun icon (☀️) appears in dark mode to switch to light, Moon icon (🌙) appears in light mode to switch to dark
- **Smooth Animations**: Icons rotate and fade with smooth transitions during theme switching
- **Consistent State**: Theme state persists in localStorage and syncs across all UI elements
- **Settings Integration**: Theme can be changed via toggle button or Settings page dropdown

## Refined Dark Mode Styling System
- **Montserrat Typography**: Clean, modern font family for better readability
- **Subtle Color Palette**: Elegant dark theme (#292c35 primary) inspired by professional design
- **Clean Transitions**: Simple 0.2s linear transitions for smooth, fast theme switching
- **Minimalist Design**: Removed overly aggressive effects for professional appearance
- **CSS Variables**: Comprehensive theming system with clean, readable color scheme
- **Balanced Contrast**: Proper text contrast ratios for accessibility
- **Refined Components**: All UI elements styled with subtle, clean aesthetics
- **Professional Toggle**: Theme button styled like a proper on/off switch
- **Consistent Spacing**: Clean borders, shadows, and spacing throughout interface

## Design Analysis from Open WebUI
- Uses Tailwind CSS framework
- Svelte frontend framework
- Modern, clean design with dark/light mode support
- Responsive layout with sidebar and main content area
- Typography: Inter, Archivo, Mona Sans fonts
- Color scheme: Neutral grays with blue accents
- PWA with mobile-responsive design

## Instructions
- Memoize any input given in this MEMOIZE.md file
- Memoize instructions in CLAUDE.md file