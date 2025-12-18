import time
from datetime import datetime
from typing import Callable
from ai_clients import call_claude, call_grok


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
        xai_api_key: str = None
    ):
        self.claude_name = claude_name
        self.grok_name = grok_name
        self.claude_model = claude_model
        self.grok_model = grok_model
        self.delay_seconds = delay_seconds
        self.anthropic_api_key = anthropic_api_key
        self.xai_api_key = xai_api_key
        
        self.claude_system = self._build_system_prompt(
            claude_name, grok_name, "Claude", claude_system_prompt, claude_context
        )
        self.grok_system = self._build_system_prompt(
            grok_name, claude_name, "Grok", grok_system_prompt, grok_context
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
        return self.transcript
    
    def get_transcript_text(self) -> str:
        lines = []
        for entry in self.transcript:
            lines.append(f"[{entry['timestamp']}] {entry['speaker']}:")
            lines.append(entry['content'])
            lines.append("")
        return "\n".join(lines)
