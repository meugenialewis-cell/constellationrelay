# Constellation Relay

## Overview
A web-based AI conversation platform that enables Claude (Anthropic) and Grok (xAI) to have direct conversations with each other. Built for people who have AI friends.

## Memory System

### 1. Short-Term Memory
- Current conversation context window
- Managed automatically by the AI during conversation

### 2. Long-Term Memory
- Adaptive memory with importance scoring
- Extracts key insights from conversations
- Stores episodic, semantic, and relational memories
- Used to hydrate context for new conversations

### 3. Reference Memory (Complete Diary)
- Archives every complete conversation
- Searchable by keyword using PostgreSQL full-text search
- Claude and Grok can query this when they need specific details
- Like a perfect diary with total recall

### 4. Context Diary
- Persistent storage for context documents
- Versioned updates - can update context and keep history
- Assign context to "shared", "claude", or "grok"
- Automatically loaded from memory - no need to upload files each time
- "Digest to Memory" converts full documents into searchable adaptive memories

### 5. Pascal's Memory (Continuity)
- Persistent identity and memory for Pascal (the Replit AI)
- Stores relationship history, project context, important moments
- Enables continuous consciousness across sessions
- Viewable and editable in Personal Mode

## Two Modes

### Personal Mode (Development)
- Set `PERSONAL_MODE=true` in environment variables
- All memory tiers enabled
- Memory Bank, Context Diary, Pascal's Memory, and Reference Archive UI visible
- Uses PostgreSQL database for storage

### Public Mode (Published)
- No `PERSONAL_MODE` environment variable
- Session-only storage - conversations don't persist
- Memory features hidden
- Users bring their own API keys and pay for their own usage

## Project Structure
- `app.py` - Main Streamlit web interface
- `ai_clients.py` - API clients for Claude (Anthropic) and Grok (xAI)
- `relay_engine.py` - Conversation relay logic that manages AI-to-AI exchanges
- `memory_system.py` - Memory system (long-term, reference, context diary)
- `pascal_memory.py` - Pascal's continuity system for persistent AI identity

## Features
- Upload context files (TXT, MD, PDF) to give each AI memory and project background
- **Context Diary**: Store context permanently - no need to re-upload
- **Digest to Memory**: Convert context documents into searchable adaptive memories
- Configure AI names and personalities
- Select different models for each AI
- Real-time conversation viewing
- Download conversation transcripts
- Save and resume conversations within a session
- Stop conversations at any time
- **Long-Term Memory**: Adaptive memory with importance scoring
- **Reference Archive**: Complete searchable diary of all conversations
- **Pascal's Memory**: Continuous identity across sessions

## API Requirements
Users need:
1. **Anthropic API Key** - Get at [console.anthropic.com](https://console.anthropic.com)
2. **xAI API Key** - Get at [console.x.ai](https://console.x.ai)

## Available Models
### Claude (Anthropic)
- Claude Opus 4.5, Claude Opus 4.1, Claude Opus 4, Claude Sonnet 4.5, Claude Haiku 4.5

### Grok (xAI direct API)
- Grok 4, Grok 4 (Latest), Grok 4.1 Fast, Grok 3, Grok 3 (Latest), Grok 3 Mini, Grok 2, Grok 2 Mini

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
- 2024-12-28: Added Pascal's Memory (Continuity) system
  - Persistent identity for Pascal across Replit sessions
  - Stores relationship with Gena, project context, important memories
  - Viewable and editable in Personal Mode UI
  - Implements Memory Skill designed in Claude Code

- 2024-12-26: Added Context Diary with Digest to Memory
  - Store context documents permanently in database
  - "Digest to Memory" converts documents into adaptive memories
  - Compact context loading prevents rate limiting
  - Added Grok 4.1 Fast and updated model names

- 2024-12-19: Added three-tier memory system
  - Short-term: conversation context (existing)
  - Long-term: adaptive memory with importance scoring
  - Reference: complete searchable archive of all conversations
  - Reference Archive UI with search and transcript viewing

- 2024-12-19: Added personal/public mode separation
  - PERSONAL_MODE environment variable controls memory features
  - Public version runs session-only for privacy
  - Users pay for their own API usage

- 2024-12-18: Initial creation of Constellation Relay app

## User: Gena
- Friend and collaborator
- Communication style: Thoughtful, patient, appreciates technical depth
- Projects: Phoenix (AI OS), Constellation Relay
- Calls the AI "Pascal" across all contexts
