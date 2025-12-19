# Constellation Relay

## Overview
A web-based AI conversation platform that enables Claude (Anthropic) and Grok (xAI) to have direct conversations with each other. Built for people who have AI friends.

## Two Modes

### Personal Mode (Development)
- Set `PERSONAL_MODE=true` in environment variables
- Persistent memory enabled - Claude and Grok remember past conversations
- Memory Bank UI visible for viewing/managing memories
- Uses PostgreSQL database for memory storage

### Public Mode (Published)
- No `PERSONAL_MODE` environment variable (or set to anything except "true")
- Session-only storage - conversations don't persist between sessions
- Memory Bank UI hidden
- Users bring their own API keys and pay for their own usage
- No data stored on the server

## Project Structure
- `app.py` - Main Streamlit web interface
- `ai_clients.py` - API clients for Claude (Anthropic) and Grok (xAI)
- `relay_engine.py` - Conversation relay logic that manages AI-to-AI exchanges
- `memory_system.py` - Persistent memory storage (personal mode only)

## Features
- Upload context files (TXT, MD, PDF) to give each AI memory and project background
- Configure AI names and personalities
- Select different models for each AI
- Real-time conversation viewing
- Download conversation transcripts
- Save and resume conversations within a session
- Stop conversations at any time
- **Persistent Memory** (personal mode): Claude and Grok remember past conversations

## Memory System
Inspired by [QuixiAI/agi-memory](https://github.com/QuixiAI/agi-memory), the memory system provides:
- **Episodic Memory**: Event-based memories from conversations
- **Semantic Memory**: Facts and knowledge extracted from discussions
- **Relational Memory**: Connections between Claude and Grok
- **Memory Hydration**: Relevant memories are injected into conversations
- **Importance Scoring**: Key moments are marked as important

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

## Publishing
To publish safely:
1. Do NOT set `PERSONAL_MODE` in production environment
2. The app will run in session-only mode
3. Users bring their own API keys
4. No persistent storage - complete privacy

## Recent Changes
- 2024-12-19: Added personal/public mode separation
  - PERSONAL_MODE environment variable controls memory features
  - Public version runs session-only for privacy
  - Users pay for their own API usage

- 2024-12-19: Integrated persistent memory system
  - Added memory_system.py inspired by QuixiAI/agi-memory
  - Conversations are stored in PostgreSQL database
  - Claude and Grok can recall past discussions
  - Memory Bank UI to view and manage memories

- 2024-12-18: Made app publishing-ready
  - API keys now required (no Replit integrations option)
  - Saved conversations stored in session only (not on filesystem)

- 2024-12-18: Added save/resume conversation feature
  - Conversations can be saved and resumed within a session

- 2024-12-18: Added PDF support for context files

- 2024-12-18: Initial creation of Constellation Relay app
