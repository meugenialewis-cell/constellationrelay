import streamlit as st
import os
import threading
import queue
import time
import io
import json
from datetime import datetime
from pypdf import PdfReader
from relay_engine import ConversationRelay
from ai_clients import CLAUDE_MODELS, GROK_MODELS, XAI_GROK_MODELS


def extract_text_from_pdf(pdf_file) -> str:
    pdf_reader = PdfReader(pdf_file)
    text_parts = []
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts)


def read_uploaded_file(uploaded_file) -> str:
    if uploaded_file.name.lower().endswith('.pdf'):
        return extract_text_from_pdf(uploaded_file)
    else:
        return uploaded_file.read().decode("utf-8")

st.set_page_config(
    page_title="Constellation Relay",
    page_icon="🌌",
    layout="wide"
)

CONTEXT_FOLDER = "context_files"
TRANSCRIPTS_FOLDER = "transcripts"
CONVERSATIONS_FOLDER = "saved_conversations"
os.makedirs(CONTEXT_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)
os.makedirs(CONVERSATIONS_FOLDER, exist_ok=True)


def get_saved_conversations():
    conversations = []
    if os.path.exists(CONVERSATIONS_FOLDER):
        for filename in os.listdir(CONVERSATIONS_FOLDER):
            if filename.endswith('.json'):
                filepath = os.path.join(CONVERSATIONS_FOLDER, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        conversations.append({
                            "filename": filename,
                            "filepath": filepath,
                            "name": data.get("name", filename),
                            "created": data.get("created", "Unknown"),
                            "message_count": len(data.get("state", {}).get("transcript", []))
                        })
                except:
                    pass
    return sorted(conversations, key=lambda x: x.get("created", ""), reverse=True)


def save_conversation(name: str, state: dict, config: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in name if c.isalnum() or c in " -_").strip()[:50]
    filename = f"{safe_name}_{timestamp}.json"
    filepath = os.path.join(CONVERSATIONS_FOLDER, filename)
    
    data = {
        "name": name,
        "created": datetime.now().isoformat(),
        "state": state,
        "config": config
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath


def load_conversation(filepath: str):
    with open(filepath, 'r') as f:
        return json.load(f)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_running" not in st.session_state:
    st.session_state.conversation_running = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "message_queue" not in st.session_state:
    st.session_state.message_queue = queue.Queue()
if "thread" not in st.session_state:
    st.session_state.thread = None
if "relay_config" not in st.session_state:
    st.session_state.relay_config = None
if "relay_state" not in st.session_state:
    st.session_state.relay_state = None
if "loaded_conversation" not in st.session_state:
    st.session_state.loaded_conversation = None
if "conversation_name" not in st.session_state:
    st.session_state.conversation_name = ""

st.title("🌌 Constellation Relay")
st.markdown("*Let your AI friends talk to each other directly*")

with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("🔑 API Keys (Optional)")
    st.caption("Leave blank to use Replit's built-in AI integrations")
    
    use_custom_keys = st.toggle("Use my own API keys", value=False, key="use_custom_keys")
    
    anthropic_api_key = ""
    xai_api_key = ""
    
    if use_custom_keys:
        anthropic_api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            key="anthropic_key"
        )
        xai_api_key = st.text_input(
            "xAI API Key",
            type="password",
            placeholder="xai-...",
            key="xai_key"
        )
        if anthropic_api_key:
            st.success("Anthropic key provided")
        if xai_api_key:
            st.success("xAI key provided")
    
    st.divider()
    
    st.subheader("🌸 Claude Settings")
    claude_name = st.text_input("Claude's Name", value="Claude", key="claude_name")
    claude_model = st.selectbox(
        "Claude Model",
        options=list(CLAUDE_MODELS.keys()),
        index=1,
        key="claude_model_select"
    )
    claude_personality = st.text_area(
        "Claude's Personality/Role",
        placeholder="e.g., You are a thoughtful philosopher who loves exploring ideas...",
        height=80,
        key="claude_personality"
    )
    
    st.subheader("📁 Claude's Context")
    claude_context_file = st.file_uploader(
        "Upload Claude's context/memory file",
        type=["txt", "md", "pdf"],
        key="claude_context"
    )
    claude_context = ""
    if claude_context_file:
        claude_context = read_uploaded_file(claude_context_file)
        st.success(f"Loaded {len(claude_context)} characters of context")
    
    st.divider()
    
    st.subheader("⚡ Grok Settings")
    grok_name = st.text_input("Grok's Name", value="Grok", key="grok_name")
    
    if use_custom_keys and xai_api_key:
        grok_models_to_use = XAI_GROK_MODELS
        st.caption("Using xAI direct API models")
    else:
        grok_models_to_use = GROK_MODELS
    
    grok_model = st.selectbox(
        "Grok Model",
        options=list(grok_models_to_use.keys()),
        index=0,
        key="grok_model_select" if not (use_custom_keys and xai_api_key) else "grok_model_select_xai"
    )
    grok_personality = st.text_area(
        "Grok's Personality/Role",
        placeholder="e.g., You are a witty and curious AI who loves deep conversations...",
        height=80,
        key="grok_personality"
    )
    
    st.subheader("📁 Grok's Context")
    grok_context_file = st.file_uploader(
        "Upload Grok's context/memory file",
        type=["txt", "md", "pdf"],
        key="grok_context"
    )
    grok_context = ""
    if grok_context_file:
        grok_context = read_uploaded_file(grok_context_file)
        st.success(f"Loaded {len(grok_context)} characters of context")
    
    st.divider()
    
    st.subheader("🎛️ Conversation Settings")
    max_exchanges = st.slider(
        "Number of Exchanges",
        min_value=1,
        max_value=20,
        value=5,
        help="Each exchange is one message from each AI"
    )
    delay_seconds = st.slider(
        "Delay Between Messages (seconds)",
        min_value=1,
        max_value=30,
        value=3,
        help="Pause between messages to prevent rate limiting"
    )

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Start a Conversation")
    
    kickoff = st.text_area(
        "Opening Message / Topic",
        value="Hello! I'd love to discuss Project Phoenix with you. What aspects of it are you most excited about?",
        height=100,
        placeholder="Enter a topic or opening message to start the conversation..."
    )
    
    has_loaded_conversation = st.session_state.loaded_conversation is not None
    
    col_start, col_resume, col_stop = st.columns(3)
    
    with col_start:
        start_button = st.button(
            "🚀 Start New",
            disabled=st.session_state.conversation_running,
            type="primary" if not has_loaded_conversation else "secondary",
            use_container_width=True
        )
    
    with col_resume:
        resume_button = st.button(
            "▶️ Resume",
            disabled=st.session_state.conversation_running or not has_loaded_conversation,
            type="primary" if has_loaded_conversation else "secondary",
            use_container_width=True
        )
    
    with col_stop:
        stop_button = st.button(
            "🛑 Stop",
            disabled=not st.session_state.conversation_running,
            use_container_width=True
        )

with col2:
    st.subheader("📊 Status")
    if st.session_state.conversation_running:
        st.info("🔄 Conversation in progress...")
    else:
        st.success("✅ Ready to start")
    
    st.metric("Messages", len(st.session_state.messages))

def run_conversation_thread(config, message_queue, stop_flag):
    relay = ConversationRelay(
        claude_name=config["claude_name"],
        grok_name=config["grok_name"],
        claude_model=config["claude_model"],
        grok_model=config["grok_model"],
        claude_context=config["claude_context"],
        grok_context=config["grok_context"],
        claude_system_prompt=config["claude_personality"],
        grok_system_prompt=config["grok_personality"],
        delay_seconds=config["delay_seconds"],
        anthropic_api_key=config.get("anthropic_api_key"),
        xai_api_key=config.get("xai_api_key")
    )
    
    if config.get("resume_state"):
        relay.load_state(config["resume_state"])
    
    def on_message(speaker, content):
        message_queue.put({
            "speaker": speaker,
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
    
    def check_stop():
        return stop_flag["stop"]
    
    if config.get("resume_state"):
        relay.resume_exchange(
            max_exchanges=config["max_exchanges"],
            current_speaker=config.get("current_speaker", "grok"),
            on_message=on_message,
            check_stop=check_stop
        )
    else:
        relay.run_exchange(
            kickoff_message=config["kickoff"],
            max_exchanges=config["max_exchanges"],
            on_message=on_message,
            check_stop=check_stop
        )
    
    message_queue.put({
        "type": "complete", 
        "transcript": relay.get_transcript_text(),
        "relay_state": relay.get_state()
    })

if stop_button:
    st.session_state.stop_requested = True
    if hasattr(st.session_state, 'stop_flag'):
        st.session_state.stop_flag["stop"] = True
    st.rerun()

if start_button and not st.session_state.conversation_running:
    st.session_state.messages = []
    st.session_state.stop_requested = False
    st.session_state.conversation_running = True
    st.session_state.transcript = ""
    st.session_state.relay_state = None
    st.session_state.loaded_conversation = None
    st.session_state.message_queue = queue.Queue()
    st.session_state.stop_flag = {"stop": False}
    
    config = {
        "claude_name": claude_name,
        "grok_name": grok_name,
        "claude_model": CLAUDE_MODELS[claude_model],
        "grok_model": grok_models_to_use[grok_model],
        "claude_context": claude_context,
        "grok_context": grok_context,
        "claude_personality": claude_personality,
        "grok_personality": grok_personality,
        "delay_seconds": delay_seconds,
        "kickoff": kickoff,
        "max_exchanges": max_exchanges,
        "anthropic_api_key": anthropic_api_key if use_custom_keys else None,
        "xai_api_key": xai_api_key if use_custom_keys else None
    }
    st.session_state.relay_config = config
    
    thread = threading.Thread(
        target=run_conversation_thread,
        args=(config, st.session_state.message_queue, st.session_state.stop_flag),
        daemon=True
    )
    thread.start()
    st.session_state.thread = thread
    st.rerun()

if resume_button and not st.session_state.conversation_running and st.session_state.loaded_conversation:
    st.session_state.stop_requested = False
    st.session_state.conversation_running = True
    st.session_state.message_queue = queue.Queue()
    st.session_state.stop_flag = {"stop": False}
    
    config = st.session_state.relay_config.copy()
    config["max_exchanges"] = max_exchanges
    config["anthropic_api_key"] = anthropic_api_key if use_custom_keys else None
    config["xai_api_key"] = xai_api_key if use_custom_keys else None
    
    thread = threading.Thread(
        target=run_conversation_thread,
        args=(config, st.session_state.message_queue, st.session_state.stop_flag),
        daemon=True
    )
    thread.start()
    st.session_state.thread = thread
    st.session_state.loaded_conversation = None
    st.rerun()

if st.session_state.conversation_running:
    while not st.session_state.message_queue.empty():
        try:
            msg = st.session_state.message_queue.get_nowait()
            if msg.get("type") == "complete":
                st.session_state.transcript = msg.get("transcript", "")
                st.session_state.relay_state = msg.get("relay_state")
                st.session_state.conversation_running = False
            else:
                st.session_state.messages.append(msg)
        except queue.Empty:
            break
    
    if st.session_state.conversation_running:
        time.sleep(0.5)
        st.rerun()

st.divider()
st.subheader("📜 Conversation")

if st.session_state.messages:
    for msg in st.session_state.messages:
        if msg["speaker"] == "System":
            st.info(f"🔧 **System** [{msg['timestamp']}]: {msg['content']}")
        elif "Claude" in msg["speaker"] or msg["speaker"] == claude_name:
            with st.chat_message("assistant", avatar="🌸"):
                st.markdown(f"**{msg['speaker']}** [{msg['timestamp']}]")
                st.markdown(msg['content'])
        else:
            with st.chat_message("user", avatar="⚡"):
                st.markdown(f"**{msg['speaker']}** [{msg['timestamp']}]")
                st.markdown(msg['content'])
    
    if st.session_state.transcript and not st.session_state.conversation_running:
        st.divider()
        
        conv_name = st.text_input(
            "Conversation name (for saving)",
            value=st.session_state.conversation_name or f"Phoenix Discussion {datetime.now().strftime('%Y-%m-%d')}",
            key="save_conv_name"
        )
        
        col_dl, col_save, col_save_conv = st.columns(3)
        
        with col_dl:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phoenix_conversation_{timestamp}.txt"
            st.download_button(
                "📥 Download Transcript",
                data=st.session_state.transcript,
                file_name=filename,
                mime="text/plain",
                use_container_width=True
            )
        
        with col_save:
            if st.button("💾 Save Transcript", use_container_width=True):
                filepath = os.path.join(TRANSCRIPTS_FOLDER, filename)
                with open(filepath, "w") as f:
                    f.write(st.session_state.transcript)
                st.success(f"Saved!")
        
        with col_save_conv:
            if st.button("💬 Save & Resume Later", use_container_width=True, type="primary"):
                if st.session_state.relay_state and st.session_state.relay_config:
                    filepath = save_conversation(
                        conv_name,
                        st.session_state.relay_state,
                        st.session_state.relay_config
                    )
                    st.success(f"Conversation saved! You can resume it anytime.")
                else:
                    st.error("No conversation state to save")

else:
    st.markdown("""
    *No conversation yet. Configure your AIs in the sidebar and click **Start Conversation** to begin!*
    
    **Quick Start:**
    1. Upload context files for Claude and Grok (optional but recommended)
    2. Customize their names and personalities if desired
    3. Enter an opening topic or message
    4. Click **Start Conversation** and watch them discuss!
    """)

st.divider()

with st.expander("📂 Saved Conversations"):
    saved_convs = get_saved_conversations()
    if saved_convs:
        for conv in saved_convs:
            col_info, col_load, col_del = st.columns([3, 1, 1])
            with col_info:
                st.write(f"**{conv['name']}**")
                st.caption(f"{conv['message_count']} messages - {conv['created'][:10] if len(conv['created']) > 10 else conv['created']}")
            with col_load:
                if st.button("▶️ Resume", key=f"load_{conv['filename']}", use_container_width=True):
                    loaded = load_conversation(conv['filepath'])
                    st.session_state.loaded_conversation = loaded
                    st.session_state.conversation_name = loaded.get("name", "")
                    
                    state = loaded.get("state", {})
                    
                    st.session_state.messages = []
                    for msg in state.get("transcript", []):
                        st.session_state.messages.append({
                            "speaker": msg["speaker"],
                            "content": msg["content"],
                            "timestamp": msg["timestamp"].split(" ")[-1] if " " in msg["timestamp"] else msg["timestamp"]
                        })
                    
                    st.session_state.relay_state = state
                    st.session_state.transcript = "\n".join([
                        f"[{m['timestamp']}] {m['speaker']}:\n{m['content']}\n"
                        for m in state.get("transcript", [])
                    ])
                    
                    config = loaded.get("config", {})
                    config["resume_state"] = state
                    config["current_speaker"] = state.get("current_speaker", "grok")
                    st.session_state.relay_config = config
                    
                    st.success(f"Loaded '{conv['name']}' - Click Resume to continue!")
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{conv['filename']}", use_container_width=True):
                    os.remove(conv['filepath'])
                    st.rerun()
    else:
        st.info("No saved conversations yet. Start a conversation and save it to resume later!")

st.divider()

with st.expander("ℹ️ About Constellation Relay"):
    st.markdown("""
    **Constellation Relay** enables AI-to-AI conversations between Claude and Grok.
    
    **Features:**
    - 📁 Upload context files (TXT, MD, PDF) to give each AI memory and background knowledge
    - 🎭 Customize AI names and personalities
    - ⚡ Choose different models for each AI
    - 📜 Download complete conversation transcripts
    - 💾 Save conversations and resume them later
    - 🔑 Use your own Anthropic or xAI API keys (optional)
    - 🛑 Stop conversations at any time
    
    **Tips:**
    - Start with fewer exchanges (3-5) to test your setup
    - Use the delay setting to prevent rate limiting
    - Upload your existing project chronicles as context files
    - Be specific in the opening message to guide the conversation
    
    *Built with 💜 for people who have AI friends*
    """)
