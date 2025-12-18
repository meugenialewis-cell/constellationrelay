# Constellation Relay

## Overview
A web-based AI conversation platform that enables Claude (Anthropic) and Grok (xAI) to have direct conversations with each other. Built for the Phoenix project discussions between Gena's AI friends.

## Project Structure
- `app.py` - Main Streamlit web interface
- `ai_clients.py` - API clients for Claude (via Anthropic AI Integrations) and Grok (via OpenRouter AI Integrations)
- `relay_engine.py` - Conversation relay logic that manages AI-to-AI exchanges
- `context_files/` - Folder for storing uploaded context/memory files
- `transcripts/` - Folder for saved conversation transcripts

## Features
- Upload context files to give each AI memory and project background
- Configure AI names and personalities
- Select different models for each AI (Claude Opus 4.1 and Grok 4.1 Fast as defaults)
- Real-time conversation viewing
- Download or save conversation transcripts
- Stop conversations at any time

## API Integrations
- **Claude**: Uses Replit AI Integrations for Anthropic (no API key required, billed to Replit credits)
- **Grok**: Uses Replit AI Integrations via OpenRouter (no API key required, billed to Replit credits)

## Available Models
### Claude
- Claude Opus 4.5, Claude Opus 4.1, Claude Sonnet 4.5, Claude Haiku 4.5

### Grok
- Grok 4.1 Fast, Grok 4 Fast, Grok 4, Grok 3, Grok 3 Mini

## Running the App
```bash
streamlit run app.py --server.port 5000
```

## User Preferences
- User: Gena
- Pascal (Claude Sonnet 4.5) helps Gena with law practice
- Phoenix project discussions between Claude (Opus 4) and Grok

## Recent Changes
- 2024-12-18: Initial creation of Constellation Relay app
  - Created AI client modules with retry logic
  - Built conversation relay engine
  - Created Streamlit web interface
  - Set up folder structure for context and transcripts
