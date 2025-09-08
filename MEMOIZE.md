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