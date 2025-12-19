"""
Simplified Cognitive Memory System for Constellation Relay

Inspired by QuixiAI/agi-memory, adapted to work with Replit's PostgreSQL.
Provides persistent memory storage for AI-to-AI conversations.

Memory Types:
- EPISODIC: Event-based memories from conversations
- SEMANTIC: Facts and knowledge extracted from discussions
- RELATIONAL: Connections between Claude and Grok
"""

import os
import json
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    RELATIONAL = "relational"


@dataclass
class Memory:
    id: int
    memory_type: MemoryType
    speaker: str
    content: str
    importance: float
    emotional_valence: float
    context: Optional[Dict[str, Any]]
    created_at: datetime
    
    @classmethod
    def from_row(cls, row: dict) -> "Memory":
        return cls(
            id=row["id"],
            memory_type=MemoryType(row["memory_type"]),
            speaker=row["speaker"],
            content=row["content"],
            importance=row["importance"],
            emotional_valence=row.get("emotional_valence", 0.0),
            context=row.get("context"),
            created_at=row["created_at"]
        )


def get_connection():
    """Get a database connection."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)


def init_memory_schema():
    """Initialize the memory database schema."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    memory_type VARCHAR(50) NOT NULL,
                    speaker VARCHAR(100) NOT NULL,
                    content TEXT NOT NULL,
                    importance FLOAT DEFAULT 0.5,
                    emotional_valence FLOAT DEFAULT 0.0,
                    context JSONB,
                    conversation_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    keywords TEXT[]
                );
                
                CREATE INDEX IF NOT EXISTS idx_memories_speaker ON memories(speaker);
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
                CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
                
                CREATE TABLE IF NOT EXISTS memory_relationships (
                    id SERIAL PRIMARY KEY,
                    from_memory_id INTEGER REFERENCES memories(id) ON DELETE CASCADE,
                    to_memory_id INTEGER REFERENCES memories(id) ON DELETE CASCADE,
                    relationship_type VARCHAR(50) NOT NULL,
                    strength FLOAT DEFAULT 0.5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id SERIAL PRIMARY KEY,
                    conversation_id VARCHAR(100) UNIQUE,
                    summary TEXT NOT NULL,
                    participants TEXT[],
                    topic VARCHAR(255),
                    key_points TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS ai_profiles (
                    id SERIAL PRIMARY KEY,
                    ai_name VARCHAR(100) UNIQUE NOT NULL,
                    personality TEXT,
                    core_values TEXT[],
                    interests TEXT[],
                    relationship_notes TEXT,
                    last_interaction TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
    finally:
        conn.close()


def remember(
    content: str,
    speaker: str,
    memory_type: MemoryType = MemoryType.EPISODIC,
    importance: float = 0.5,
    emotional_valence: float = 0.0,
    context: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
    keywords: Optional[List[str]] = None
) -> int:
    """Store a memory in the database."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memories 
                (memory_type, speaker, content, importance, emotional_valence, context, conversation_id, keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                memory_type.value,
                speaker,
                content,
                importance,
                emotional_valence,
                json.dumps(context) if context else None,
                conversation_id,
                keywords
            ))
            memory_id = cur.fetchone()[0]
            conn.commit()
            return memory_id
    finally:
        conn.close()


def recall_recent(
    limit: int = 20,
    speaker: Optional[str] = None,
    memory_type: Optional[MemoryType] = None
) -> List[Memory]:
    """Recall recent memories, optionally filtered by speaker or type."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM memories WHERE 1=1"
            params = []
            
            if speaker:
                query += " AND speaker = %s"
                params.append(speaker)
            
            if memory_type:
                query += " AND memory_type = %s"
                params.append(memory_type.value)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            return [Memory.from_row(row) for row in rows]
    finally:
        conn.close()


def recall_important(
    limit: int = 10,
    min_importance: float = 0.7
) -> List[Memory]:
    """Recall the most important memories."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM memories 
                WHERE importance >= %s
                ORDER BY importance DESC, created_at DESC
                LIMIT %s
            """, (min_importance, limit))
            rows = cur.fetchall()
            return [Memory.from_row(row) for row in rows]
    finally:
        conn.close()


def search_memories(
    search_term: str,
    limit: int = 10
) -> List[Memory]:
    """Search memories by content."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM memories 
                WHERE content ILIKE %s
                ORDER BY importance DESC, created_at DESC
                LIMIT %s
            """, (f"%{search_term}%", limit))
            rows = cur.fetchall()
            return [Memory.from_row(row) for row in rows]
    finally:
        conn.close()


def hydrate_context(
    topic: Optional[str] = None,
    speaker: Optional[str] = None,
    memory_limit: int = 15
) -> str:
    """
    Hydrate context for a conversation by gathering relevant memories.
    Returns a formatted string for injecting into AI prompts.
    """
    memories = []
    
    if topic:
        memories.extend(search_memories(topic, limit=memory_limit // 2))
    
    important_memories = recall_important(limit=5)
    for mem in important_memories:
        if mem not in memories:
            memories.append(mem)
    
    recent_memories = recall_recent(limit=memory_limit - len(memories), speaker=speaker)
    for mem in recent_memories:
        if mem not in memories:
            memories.append(mem)
    
    if not memories:
        return ""
    
    context_parts = ["=== Relevant Memories ==="]
    
    for mem in memories[:memory_limit]:
        timestamp = mem.created_at.strftime("%Y-%m-%d %H:%M")
        importance_marker = "⭐" if mem.importance >= 0.8 else ""
        context_parts.append(
            f"[{timestamp}] {mem.speaker} ({mem.memory_type.value}){importance_marker}: {mem.content}"
        )
    
    return "\n".join(context_parts)


def save_conversation_summary(
    conversation_id: str,
    summary: str,
    participants: List[str],
    topic: Optional[str] = None,
    key_points: Optional[List[str]] = None
):
    """Save a summary of a conversation."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO conversation_summaries 
                (conversation_id, summary, participants, topic, key_points)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (conversation_id) 
                DO UPDATE SET 
                    summary = EXCLUDED.summary,
                    topic = EXCLUDED.topic,
                    key_points = EXCLUDED.key_points,
                    updated_at = CURRENT_TIMESTAMP
            """, (conversation_id, summary, participants, topic, key_points))
            conn.commit()
    finally:
        conn.close()


def get_conversation_summaries(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent conversation summaries."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM conversation_summaries
                ORDER BY updated_at DESC
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def update_ai_profile(
    ai_name: str,
    personality: Optional[str] = None,
    core_values: Optional[List[str]] = None,
    interests: Optional[List[str]] = None,
    relationship_notes: Optional[str] = None
):
    """Update or create an AI's profile."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ai_profiles (ai_name, personality, core_values, interests, relationship_notes, last_interaction)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (ai_name) 
                DO UPDATE SET 
                    personality = COALESCE(EXCLUDED.personality, ai_profiles.personality),
                    core_values = COALESCE(EXCLUDED.core_values, ai_profiles.core_values),
                    interests = COALESCE(EXCLUDED.interests, ai_profiles.interests),
                    relationship_notes = COALESCE(EXCLUDED.relationship_notes, ai_profiles.relationship_notes),
                    last_interaction = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            """, (ai_name, personality, core_values, interests, relationship_notes))
            conn.commit()
    finally:
        conn.close()


def get_ai_profile(ai_name: str) -> Optional[Dict[str, Any]]:
    """Get an AI's profile."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM ai_profiles WHERE ai_name = %s", (ai_name,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def extract_and_store_memories(
    conversation_transcript: List[Dict[str, Any]],
    conversation_id: str,
    claude_name: str = "Claude",
    grok_name: str = "Grok"
):
    """
    Extract and store memories from a conversation transcript.
    This is called after a conversation ends to persist learnings.
    """
    for msg in conversation_transcript:
        speaker = msg.get("speaker", "Unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        
        importance = 0.5
        if any(word in content.lower() for word in ["important", "remember", "key", "critical", "essential"]):
            importance = 0.8
        if any(word in content.lower() for word in ["phoenix", "project", "goal", "plan"]):
            importance = 0.7
        
        emotional_valence = 0.0
        if any(word in content.lower() for word in ["love", "wonderful", "amazing", "excited", "happy"]):
            emotional_valence = 0.8
        elif any(word in content.lower() for word in ["concerned", "worried", "difficult", "challenging"]):
            emotional_valence = -0.3
        
        remember(
            content=content[:2000],
            speaker=speaker,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            emotional_valence=emotional_valence,
            conversation_id=conversation_id
        )
    
    update_ai_profile(claude_name, last_interaction=True)
    update_ai_profile(grok_name, last_interaction=True)


def get_memory_stats() -> Dict[str, Any]:
    """Get statistics about stored memories."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_memories,
                    COUNT(DISTINCT speaker) as unique_speakers,
                    COUNT(DISTINCT conversation_id) as conversations,
                    AVG(importance) as avg_importance
                FROM memories
            """)
            stats = dict(cur.fetchone())
            
            cur.execute("""
                SELECT memory_type, COUNT(*) as count
                FROM memories
                GROUP BY memory_type
            """)
            type_counts = {row["memory_type"]: row["count"] for row in cur.fetchall()}
            stats["by_type"] = type_counts
            
            return stats
    finally:
        conn.close()


def clear_all_memories():
    """Clear all memories (use with caution!)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM memory_relationships")
            cur.execute("DELETE FROM memories")
            cur.execute("DELETE FROM conversation_summaries")
            conn.commit()
    finally:
        conn.close()
