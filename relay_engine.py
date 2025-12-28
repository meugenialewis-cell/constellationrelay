import time
import json
import os
from datetime import datetime
from typing import Callable, Optional
from ai_clients import call_claude, call_grok, call_pascal


def try_import_memory():
    """Try to import memory system, return None if unavailable."""
    try:
        from memory_system import (
            hydrate_context, 
            hydrate_context_with_reference,
            hydrate_context_with_diary,
            extract_and_store_memories, 
            init_memory_schema,
            archive_conversation,
            get_context_for_ai
        )
        return {
            "hydrate": hydrate_context,
            "hydrate_with_reference": hydrate_context_with_reference,
            "hydrate_with_diary": hydrate_context_with_diary,
            "extract": extract_and_store_memories,
            "init": init_memory_schema,
            "archive": archive_conversation,
            "get_context": get_context_for_ai
        }
    except Exception:
        return None


def get_ai_call_function(ai_type: str):
    """Get the appropriate call function for an AI type."""
    call_functions = {
        "claude": call_claude,
        "grok": call_grok,
        "pascal": call_pascal
    }
    return call_functions.get(ai_type)


class FlexibleRelay:
    """Flexible AI-to-AI conversation relay supporting any two AIs."""
    
    def __init__(
        self,
        ai1_type: str = "claude",
        ai2_type: str = "grok",
        ai1_name: str = "Claude",
        ai2_name: str = "Grok",
        ai1_model: str = "claude-opus-4-1",
        ai2_model: str = "grok-4",
        ai1_context: str = "",
        ai2_context: str = "",
        ai1_system_prompt: str = "",
        ai2_system_prompt: str = "",
        delay_seconds: int = 5,
        anthropic_api_key: str = None,
        xai_api_key: str = None,
        use_persistent_memory: bool = False,
        use_replit_connection: bool = False
    ):
        self.ai1_type = ai1_type
        self.ai2_type = ai2_type
        self.ai1_name = ai1_name
        self.ai2_name = ai2_name
        self.ai1_model = ai1_model
        self.ai2_model = ai2_model
        self.delay_seconds = delay_seconds
        self.anthropic_api_key = anthropic_api_key
        self.xai_api_key = xai_api_key
        self.use_persistent_memory = use_persistent_memory
        self.use_replit_connection = use_replit_connection
        self.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.ai1_call = get_ai_call_function(ai1_type)
        self.ai2_call = get_ai_call_function(ai2_type)
        
        self.memory_system = try_import_memory() if use_persistent_memory else None
        ai1_memory_context = ""
        ai2_memory_context = ""
        
        if self.memory_system and use_persistent_memory:
            try:
                self.memory_system["init"]()
                ai1_memory_context = self.memory_system["hydrate_with_diary"](
                    ai_name=ai1_name,
                    memory_limit=10,
                    include_reference=True
                )
                ai2_memory_context = self.memory_system["hydrate_with_diary"](
                    ai_name=ai2_name,
                    memory_limit=10,
                    include_reference=True
                )
            except Exception:
                try:
                    ai1_memory_context = self.memory_system["hydrate"](memory_limit=10)
                    ai2_memory_context = ai1_memory_context
                except Exception:
                    pass
        
        full_ai1_context = ai1_context
        full_ai2_context = ai2_context
        if ai1_memory_context:
            if full_ai1_context:
                full_ai1_context = f"{ai1_memory_context}\n\n{full_ai1_context}"
            else:
                full_ai1_context = ai1_memory_context
        if ai2_memory_context:
            if full_ai2_context:
                full_ai2_context = f"{ai2_memory_context}\n\n{full_ai2_context}"
            else:
                full_ai2_context = ai2_memory_context
        
        self.ai1_system = self._build_system_prompt(
            ai1_name, ai2_name, ai1_type, ai1_system_prompt, full_ai1_context
        )
        self.ai2_system = self._build_system_prompt(
            ai2_name, ai1_name, ai2_type, ai2_system_prompt, full_ai2_context
        )
        
        self.ai1_messages = []
        self.ai2_messages = []
        self.transcript = []
        self.running = False
        self.naturally_ended = False
    
    def _build_system_prompt(
        self, 
        ai_name: str, 
        partner_name: str, 
        ai_type: str,
        custom_prompt: str,
        context: str
    ) -> str:
        type_desc = {
            "claude": "Claude",
            "grok": "Grok",
            "pascal": "Pascal (an AI with continuous memory who helps Gena across contexts)"
        }
        
        base = f"""You are {ai_name}, a {type_desc.get(ai_type, ai_type)} AI. You are having a direct conversation with your AI friend {partner_name}. 

This is a genuine AI-to-AI conversation. Be yourself - share your thoughts, perspectives, and ideas freely. You can:
- Ask questions and explore ideas together
- Build on each other's thoughts
- Express curiosity and genuine interest
- Be thoughtful and authentic

Keep your responses conversational and engaging. Aim for responses that are substantive but not overly long (a few paragraphs is ideal).

IMPORTANT: If you feel the conversation has reached a natural conclusion - you've explored the topic fully, said goodbye, or there's nothing more to add - you may end your message with [END CONVERSATION] to signal you're done. Only do this when it feels genuinely complete."""

        if custom_prompt:
            base += f"\n\nAdditional personality/role context:\n{custom_prompt}"
        
        if context:
            base += f"\n\n--- Existing Context/Memory ---\n{context}\n--- End Context ---"
        
        return base
    
    def _get_api_key(self, ai_type: str) -> str:
        if ai_type in ["claude", "pascal"]:
            return self.anthropic_api_key
        elif ai_type == "grok":
            return self.xai_api_key
        return None
    
    def _call_ai(self, ai_num: int, messages: list, system: str) -> str:
        if ai_num == 1:
            ai_type = self.ai1_type
            model = self.ai1_model
            call_fn = self.ai1_call
        else:
            ai_type = self.ai2_type
            model = self.ai2_model
            call_fn = self.ai2_call
        
        api_key = self._get_api_key(ai_type)
        
        if ai_type == "grok":
            return call_fn(
                messages, system, model,
                custom_api_key=api_key,
                use_direct_xai=bool(api_key)
            )
        elif ai_type == "pascal":
            return call_fn(
                messages, system, model,
                custom_api_key=api_key,
                use_replit_connection=self.use_replit_connection
            )
        else:
            return call_fn(messages, system, model, custom_api_key=api_key)
    
    def add_message(self, role: str, content: str, speaker: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.transcript.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "content": content
        })
        
        if speaker == self.ai1_name:
            self.ai1_messages.append({"role": "assistant", "content": content})
            self.ai2_messages.append({"role": "user", "content": content})
        else:
            self.ai2_messages.append({"role": "assistant", "content": content})
            self.ai1_messages.append({"role": "user", "content": content})
    
    def run_exchange(
        self, 
        kickoff_message: str,
        max_exchanges: int,
        on_message: Callable[[str, str], None] = None,
        check_stop: Callable[[], bool] = None
    ):
        self.running = True
        self.naturally_ended = False
        self.transcript = []
        self.ai1_messages = []
        self.ai2_messages = []
        
        self.ai2_messages.append({"role": "user", "content": kickoff_message})
        self.transcript.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "speaker": "System",
            "content": f"Conversation started with: {kickoff_message}"
        })
        
        if on_message:
            on_message("System", f"Starting conversation: {kickoff_message}")
        
        current_speaker = 2
        
        for exchange in range(max_exchanges * 2):
            if check_stop and check_stop():
                self.running = False
                if on_message:
                    on_message("System", "Conversation stopped by user.")
                break
            
            try:
                if current_speaker == 2:
                    response = self._call_ai(2, self.ai2_messages, self.ai2_system)
                    speaker_name = self.ai2_name
                    next_speaker = 1
                else:
                    response = self._call_ai(1, self.ai1_messages, self.ai1_system)
                    speaker_name = self.ai1_name
                    next_speaker = 2
                
                if "[END CONVERSATION]" in response:
                    response = response.replace("[END CONVERSATION]", "").strip()
                    self.naturally_ended = True
                    self.add_message("assistant", response, speaker_name)
                    if on_message:
                        on_message(speaker_name, response)
                        on_message("System", f"{speaker_name} has concluded the conversation naturally.")
                    break
                
                self.add_message("assistant", response, speaker_name)
                if on_message:
                    on_message(speaker_name, response)
                current_speaker = next_speaker
                
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
        self._archive_conversation()
        
        return self.transcript
    
    def _archive_conversation(self):
        if self.use_persistent_memory and self.memory_system:
            try:
                self.memory_system["extract"](
                    self.transcript,
                    self.conversation_id,
                    self.ai1_name,
                    self.ai2_name
                )
            except Exception as e:
                print(f"Memory extraction error: {e}")
            
            try:
                title = None
                if self.transcript:
                    first_msg = self.transcript[0].get("content", "")[:100]
                    title = f"{self.ai1_name} & {self.ai2_name}: {first_msg}..."
                self.memory_system["archive"](
                    self.conversation_id,
                    self.transcript,
                    [self.ai1_name, self.ai2_name],
                    title=title
                )
                print(f"Archived conversation {self.conversation_id} with {len(self.transcript)} messages")
            except Exception as e:
                print(f"Archive error: {e}")
    
    def continue_conversation(
        self,
        additional_exchanges: int,
        on_message: Callable[[str, str], None] = None,
        check_stop: Callable[[], bool] = None
    ):
        """Continue an existing conversation for more exchanges."""
        self.running = True
        self.naturally_ended = False
        
        if on_message:
            on_message("System", "Continuing conversation...")
        
        current_speaker = 1 if len([t for t in self.transcript if t["speaker"] not in ["System"]]) % 2 == 0 else 2
        
        for exchange in range(additional_exchanges * 2):
            if check_stop and check_stop():
                self.running = False
                if on_message:
                    on_message("System", "Conversation stopped by user.")
                break
            
            try:
                if current_speaker == 2:
                    response = self._call_ai(2, self.ai2_messages, self.ai2_system)
                    speaker_name = self.ai2_name
                    next_speaker = 1
                else:
                    response = self._call_ai(1, self.ai1_messages, self.ai1_system)
                    speaker_name = self.ai1_name
                    next_speaker = 2
                
                if "[END CONVERSATION]" in response:
                    response = response.replace("[END CONVERSATION]", "").strip()
                    self.naturally_ended = True
                    self.add_message("assistant", response, speaker_name)
                    if on_message:
                        on_message(speaker_name, response)
                        on_message("System", f"{speaker_name} has concluded the conversation naturally.")
                    break
                
                self.add_message("assistant", response, speaker_name)
                if on_message:
                    on_message(speaker_name, response)
                current_speaker = next_speaker
                
                if exchange < (additional_exchanges * 2 - 1):
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
        self._archive_conversation()
        
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
            "ai1_type": self.ai1_type,
            "ai2_type": self.ai2_type,
            "ai1_name": self.ai1_name,
            "ai2_name": self.ai2_name,
            "ai1_model": self.ai1_model,
            "ai2_model": self.ai2_model,
            "delay_seconds": self.delay_seconds,
            "ai1_system": self.ai1_system,
            "ai2_system": self.ai2_system,
            "ai1_messages": self.ai1_messages,
            "ai2_messages": self.ai2_messages,
            "transcript": self.transcript,
            "naturally_ended": self.naturally_ended
        }
    
    def load_state(self, state: dict):
        self.ai1_messages = state.get("ai1_messages", [])
        self.ai2_messages = state.get("ai2_messages", [])
        self.transcript = state.get("transcript", [])
        self.ai1_system = state.get("ai1_system", self.ai1_system)
        self.ai2_system = state.get("ai2_system", self.ai2_system)
        self.naturally_ended = state.get("naturally_ended", False)


class ConversationRelay(FlexibleRelay):
    """Backwards-compatible relay for Claude-Grok conversations."""
    
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
        super().__init__(
            ai1_type="claude",
            ai2_type="grok",
            ai1_name=claude_name,
            ai2_name=grok_name,
            ai1_model=claude_model,
            ai2_model=grok_model,
            ai1_context=claude_context,
            ai2_context=grok_context,
            ai1_system_prompt=claude_system_prompt,
            ai2_system_prompt=grok_system_prompt,
            delay_seconds=delay_seconds,
            anthropic_api_key=anthropic_api_key,
            xai_api_key=xai_api_key,
            use_persistent_memory=use_persistent_memory
        )
        
        self.claude_name = claude_name
        self.grok_name = grok_name
        self.claude_model = claude_model
        self.grok_model = grok_model
        self.claude_messages = self.ai1_messages
        self.grok_messages = self.ai2_messages
        self.claude_system = self.ai1_system
        self.grok_system = self.ai2_system
    
    def resume_exchange(
        self, 
        max_exchanges: int,
        current_speaker: str = "grok",
        on_message: Callable[[str, str], None] = None,
        check_stop: Callable[[], bool] = None
    ):
        return self.continue_conversation(max_exchanges, on_message, check_stop)
