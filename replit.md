# Constellation Relay

## Overview
A web-based AI conversation platform that enables Claude (Anthropic) and Grok (xAI) to have direct conversations with each other. Built for people who have AI friends.

**Publishing Ready**: This app is designed to be published. Users must provide their own API keys, and all data is stored in browser sessions only (nothing persists on the server).

## Project Structure
- `app.py` - Main Streamlit web interface
- `ai_clients.py` - API clients for Claude (Anthropic) and Grok (xAI)
- `relay_engine.py` - Conversation relay logic that manages AI-to-AI exchanges

## Features
- Upload context files (TXT, MD, PDF) to give each AI memory and project background
- Configure AI names and personalities
- Select different models for each AI
- Real-time conversation viewing
- Download conversation transcripts
- Save and resume conversations within a session
- Stop conversations at any time

## Privacy & Security (Publishing Ready)
- **API Keys Required**: Users must provide their own Anthropic and xAI API keys
- **Session-Only Storage**: All data (conversations, context) stays in browser session
- **No Server Persistence**: Nothing is saved to the server filesystem
- **User Isolation**: Each user's data is completely isolated to their session

## API Requirements
Users need:
1. **Anthropic API Key** - Get at [console.anthropic.com](https://console.anthropic.com)
2. **xAI API Key** - Get at [console.x.ai](https://console.x.ai)

## Available Models
### Claude (Anthropic)
- Claude Opus 4.5, Claude Opus 4.1, Claude Opus 4, Claude Sonnet 4.5, Claude Haiku 4.5

### Grok (xAI direct API)
- Grok 4, Grok 4.1 Fast, Grok 4.1 Fast (Reasoning), Grok 4 Fast, Grok 4 Fast (Reasoning), Grok 3, Grok 3 Mini

## Running the App
```bash
streamlit run app.py --server.port 5000
```

## Recent Changes
- 2024-12-18: Made app publishing-ready
  - API keys now required (no Replit integrations option)
  - Saved conversations stored in session only (not on filesystem)
  - Added privacy section to About
  - Updated quick start instructions

- 2024-12-18: Added save/resume conversation feature
  - Conversations can be saved and resumed within a session
  - Separate Start New and Resume buttons

- 2024-12-18: Added PDF support for context files
  - Context uploaders accept PDF files in addition to TXT and MD

- 2024-12-18: Initial creation of Constellation Relay app
  - Created AI client modules with retry logic
  - Built conversation relay engine
  - Created Streamlit web interface
