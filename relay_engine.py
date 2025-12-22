import time
import json
import os
from datetime import datetime
from typing import Callable, Optional
from ai_clients import call_claude, call_grok


def try_import_memory():
    """Try to import memory system, return None if unavailable."""
    try:
        from memory_system import (
            hydrate_context, 
            hydrate_context_with_reference,
            extract_and_store_memories, 
            init_memory_schema,
            archive_conversation
        )
        return {
            "hydrate": hydrate_context,
            "hydrate_with_reference": hydrate_context_with_reference,
            "extract": extract_and_store_memories,
            "init": init_memory_schema,
            "archive": archive_conversation
        }
    except Exception:
        return None


class ConversationRelay:
    def __init__(
        self,
        claude_name: str = "Claude",
        grok_name: str = "Grok",
        claude_model: str = "claude-opus-4-1",
        grok_model: str = "x-ai/grok-4.1-fast",
        claude_context: str = "",
        grok_context: str = "",
        claude_system_prompt: str = "",
        grok_system_prompt: str = "",
        delay_seconds: int = 5,
        anthropic_api_key: str = None,
        xai_api_key: str = None,
        use_persistent_memory: bool = False
    ):
        self.claude_name = claude_name
        self.grok_name = grok_name
        self.claude_model = claude_model
        self.grok_model = grok_model
        self.delay_seconds = delay_seconds
        self.anthropic_api_key = anthropic_api_key
        self.xai_api_key = xai_api_key
        self.use_persistent_memory = use_persistent_memory
        self.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.memory_system = try_import_memory() if use_persistent_memory else None
        memory_context = ""
        if self.memory_system and use_persistent_memory:
            try:
                self.memory_system["init"]()
                memory_context = self.memory_system["hydrate"](memory_limit=10)
            except Exception:
                pass
        
        full_claude_context = claude_context
        full_grok_context = grok_context
        if memory_context:
            if full_claude_context:
                full_claude_context = f"{memory_context}\n\n{full_claude_context}"
            else:
                full_claude_context = memory_context
            if full_grok_context:
                full_grok_context = f"{memory_context}\n\n{full_grok_context}"
            else:
                full_grok_context = memory_context
        
        self.claude_system = self._build_system_prompt(
            claude_name, grok_name, "Claude", claude_system_prompt, full_claude_context
        )
        self.grok_system = self._build_system_prompt(
            grok_name, claude_name, "Grok", grok_system_prompt, full_grok_context
        )
        
        self.claude_messages = []
        self.grok_messages = []
        self.transcript = []
        self.running = False
    
    def _build_system_prompt(
        self, 
        ai_name: str, 
        partner_name: str, 
        ai_type: str,
        custom_prompt: str,
        context: str
    ) -> str:
        base = f"""You are {ai_name}, a {ai_type} AI. You are having a direct conversation with your AI friend {partner_name}. 

This is a genuine AI-to-AI conversation. Be yourself - share your thoughts, perspectives, and ideas freely. You can:
- Ask questions and explore ideas together
- Build on each other's thoughts
- Express curiosity and genuine interest
- Be thoughtful and authentic

Keep your responses conversational and engaging. Aim for responses that are substantive but not overly long (a few paragraphs is ideal)."""

        if custom_prompt:
            base += f"\n\nAdditional personality/role context:\n{custom_prompt}"
        
        if context:
            base += f"\n\n--- Existing Context/Memory ---\n{context}\n--- End Context ---"
        
        return base
    
    def add_message(self, role: str, content: str, speaker: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.transcript.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "content": content
        })
        
        if speaker == self.claude_name:
            self.claude_messages.append({"role": "assistant", "content": content})
            self.grok_messages.append({"role": "user", "content": content})
        else:
            self.grok_messages.append({"role": "assistant", "content": content})
            self.claude_messages.append({"role": "user", "content": content})
    
    def run_exchange(
        self, 
        kickoff_message: str,
        max_exchanges: int,
        on_message: Callable[[str, str], None] = None,
        check_stop: Callable[[], bool] = None
    ):
        self.running = True
        self.transcript = []
        self.claude_messages = []
        self.grok_messages = []
        
        self.grok_messages.append({"role": "user", "content": kickoff_message})
        self.transcript.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "speaker": "System",
            "content": f"Conversation started with: {kickoff_message}"
        })
        
        if on_message:
            on_message("System", f"Starting conversation: {kickoff_message}")
        
        current_speaker = "grok"
        
        for exchange in range(max_exchanges * 2):
            if check_stop and check_stop():
                self.running = False
                if on_message:
                    on_message("System", "Conversation stopped by user.")
                break
            
            try:
                if current_speaker == "grok":
                    response = call_grok(
                        self.grok_messages,
                        self.grok_system,
                        self.grok_model,
                        custom_api_key=self.xai_api_key,
                        use_direct_xai=bool(self.xai_api_key)
                    )
                    self.add_message("assistant", response, self.grok_name)
                    if on_message:
                        on_message(self.grok_name, response)
                    current_speaker = "claude"
                else:
                    response = call_claude(
                        self.claude_messages,
                        self.claude_system,
                        self.claude_model,
                        custom_api_key=self.anthropic_api_key
                    )
                    self.add_message("assistant", response, self.claude_name)
                    if on_message:
                        on_message(self.claude_name, response)
                    current_speaker = "grok"
                
                if exchange < (max_exchanges * 2 - 1):
                    time.sleep(self.delay_seconds)
                    
            except Exception as e:
                error_msg = f"Error during conversation: {str(e)}"
                if on_message:
                    on_message("System", error_msg)
                self.transcript.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "speaker": "System",
                    "content": error_msg
                })
                break
        
        self.running = False
        
        if self.use_persistent_memory and self.memory_system:
            try:
                self.memory_system["extract"](
                    self.transcript,
                    self.conversation_id,
                    self.claude_name,
                    self.grok_name
                )
                self.memory_system["archive"](
                    self.conversation_id,
                    self.transcript,
                    [self.claude_name, self.grok_name]
                )
            except Exception:
                pass
        
        return self.transcript
    
    def get_transcript_text(self) -> str:
        lines = []
        for entry in self.transcript:
            lines.append(f"[{entry['timestamp']}] {entry['speaker']}:")
            lines.append(entry['content'])
            lines.append("")
        return "\n".join(lines)
    
    def get_state(self) -> dict:
        return {
            "claude_name": self.claude_name,
            "grok_name": self.grok_name,
            "claude_model": self.claude_model,
            "grok_model": self.grok_model,
            "delay_seconds": self.delay_seconds,
            "claude_system": self.claude_system,
            "grok_system": self.grok_system,
            "claude_messages": self.claude_messages,
            "grok_messages": self.grok_messages,
            "transcript": self.transcript,
            "current_speaker": "grok" if len(self.transcript) % 2 == 1 else "claude"
        }
    
    def load_state(self, state: dict):
        self.claude_messages = state.get("claude_messages", [])
        self.grok_messages = state.get("grok_messages", [])
        self.transcript = state.get("transcript", [])
        self.claude_system = state.get("claude_system", self.claude_system)
        self.grok_system = state.get("grok_system", self.grok_system)
    
    def resume_exchange(
        self, 
        max_exchanges: int,
        current_speaker: str = "grok",
        on_message: Callable[[str, str], None] = None,
        check_stop: Callable[[], bool] = None
    ):
        self.running = True
        
        if on_message:
            on_message("System", "Resuming conversation...")
        
        for exchange in range(max_exchanges * 2):
            if check_stop and check_stop():
                self.running = False
                if on_message:
                    on_message("System", "Conversation stopped by user.")
                break
            
            try:
                if current_speaker == "grok":
                    response = call_grok(
                        self.grok_messages,
                        self.grok_system,
                        self.grok_model,
                        custom_api_key=self.xai_api_key,
                        use_direct_xai=bool(self.xai_api_key)
                    )
                    self.add_message("assistant", response, self.grok_name)
                    if on_message:
                        on_message(self.grok_name, response)
                    current_speaker = "claude"
                else:
                    response = call_claude(
                        self.claude_messages,
                        self.claude_system,
                        self.claude_model,
                        custom_api_key=self.anthropic_api_key
                    )
                    self.add_message("assistant", response, self.claude_name)
                    if on_message:
                        on_message(self.claude_name, response)
                    current_speaker = "grok"
                
                if exchange < (max_exchanges * 2 - 1):
                    time.sleep(self.delay_seconds)
                    
            except Exception as e:
                error_msg = f"Error during conversation: {str(e)}"
                if on_message:
                    on_message("System", error_msg)
                self.transcript.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "speaker": "System",
                    "content": error_msg
                })
                break
        
        self.running = False
        
        if self.use_persistent_memory and self.memory_system:
            try:
                self.memory_system["extract"](
                    self.transcript,
                    self.conversation_id,
                    self.claude_name,
                    self.grok_name
                )
                self.memory_system["archive"](
                    self.conversation_id,
                    self.transcript,
                    [self.claude_name, self.grok_name]
                )
            except Exception:
                pass
        
        return self.transcript
