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

PERSONAL_MODE = os.environ.get("PERSONAL_MODE", "").lower() == "true"


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



def get_saved_conversations():
    if "saved_conversations" not in st.session_state:
        st.session_state.saved_conversations = []
    return sorted(st.session_state.saved_conversations, key=lambda x: x.get("created", ""), reverse=True)


def save_conversation(name: str, state: dict, config: dict):
    if "saved_conversations" not in st.session_state:
        st.session_state.saved_conversations = []
    
    config_to_save = {k: v for k, v in config.items() if k not in ["anthropic_api_key", "xai_api_key"]}
    
    conv_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {
        "id": conv_id,
        "name": name,
        "created": datetime.now().isoformat(),
        "state": state,
        "config": config_to_save
    }
    
    st.session_state.saved_conversations.append(data)
    return conv_id


def load_conversation(conv_id: str):
    for conv in st.session_state.get("saved_conversations", []):
        if conv.get("id") == conv_id:
            return conv
    return None


def delete_conversation(conv_id: str):
    if "saved_conversations" in st.session_state:
        st.session_state.saved_conversations = [
            c for c in st.session_state.saved_conversations if c.get("id") != conv_id
        ]

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
    
    st.subheader("🔑 API Keys (Required)")
    st.caption("You need your own API keys to use this app")
    
    anthropic_api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        key="anthropic_key",
        help="Get your key at console.anthropic.com"
    )
    xai_api_key = st.text_input(
        "xAI API Key",
        type="password",
        placeholder="xai-...",
        key="xai_key",
        help="Get your key at console.x.ai"
    )
    
    keys_valid = bool(anthropic_api_key and xai_api_key)
    if anthropic_api_key:
        st.success("Anthropic key provided")
    else:
        st.warning("Anthropic key required")
    if xai_api_key:
        st.success("xAI key provided")
    else:
        st.warning("xAI key required")
    
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
    
    grok_models_to_use = XAI_GROK_MODELS if xai_api_key else GROK_MODELS
    
    grok_model = st.selectbox(
        "Grok Model",
        options=list(grok_models_to_use.keys()),
        index=0,
        key="grok_model_select"
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
    
    if PERSONAL_MODE:
        st.subheader("🧠 Persistent Memory")
        use_persistent_memory = st.toggle(
            "Enable AI Memory",
            value=True,
            key="use_memory",
            help="Store and recall memories from past conversations"
        )
        if use_persistent_memory:
            st.caption("Claude and Grok will remember past conversations")
    else:
        use_persistent_memory = False
    
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
            disabled=st.session_state.conversation_running or not keys_valid,
            type="primary" if not has_loaded_conversation else "secondary",
            use_container_width=True
        )
    
    with col_resume:
        resume_button = st.button(
            "▶️ Resume",
            disabled=st.session_state.conversation_running or not has_loaded_conversation or not keys_valid,
            type="primary" if has_loaded_conversation else "secondary",
            use_container_width=True
        )
    
    if not keys_valid:
        st.warning("Please enter both API keys in the sidebar to start a conversation")
    
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
        xai_api_key=config.get("xai_api_key"),
        use_persistent_memory=config.get("use_persistent_memory", False)
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
        "anthropic_api_key": anthropic_api_key,
        "xai_api_key": xai_api_key,
        "use_persistent_memory": use_persistent_memory
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
    config["anthropic_api_key"] = anthropic_api_key
    config["xai_api_key"] = xai_api_key
    config["use_persistent_memory"] = use_persistent_memory
    
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
    *No conversation yet. Enter your API keys in the sidebar to get started!*
    
    **Quick Start:**
    1. Enter your Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))
    2. Enter your xAI API key (get one at [console.x.ai](https://console.x.ai))
    3. Upload context files for Claude and Grok (optional but recommended)
    4. Enter an opening topic and click **Start New**!
    """)

st.divider()

with st.expander("📂 Saved Conversations (this session)"):
    saved_convs = get_saved_conversations()
    if saved_convs:
        st.caption("Saved conversations are stored in your browser session only")
        for conv in saved_convs:
            col_info, col_load, col_del = st.columns([3, 1, 1])
            with col_info:
                st.write(f"**{conv['name']}**")
                msg_count = len(conv.get("state", {}).get("transcript", []))
                st.caption(f"{msg_count} messages - {conv['created'][:10] if len(conv['created']) > 10 else conv['created']}")
            with col_load:
                if st.button("▶️ Resume", key=f"load_{conv['id']}", use_container_width=True):
                    loaded = load_conversation(conv['id'])
                    if loaded:
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
                if st.button("🗑️", key=f"del_{conv['id']}", use_container_width=True):
                    delete_conversation(conv['id'])
                    st.rerun()
    else:
        st.info("No saved conversations yet. Start a conversation and save it to resume later!")

st.divider()

if PERSONAL_MODE:
    with st.expander("🧠 Long-Term Memory"):
        try:
            from memory_system import get_memory_stats, recall_recent, recall_important, clear_all_memories, init_memory_schema
            
            init_memory_schema()
            stats = get_memory_stats()
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("Total Memories", stats.get("total_memories", 0))
            with col_stats2:
                st.metric("Conversations", stats.get("conversations", 0))
            with col_stats3:
                st.metric("Avg Importance", f"{(stats.get('avg_importance') or 0):.2f}")
            
            if stats.get("total_memories", 0) > 0:
                st.subheader("Recent Memories")
                recent = recall_recent(limit=10)
                for mem in recent:
                    timestamp = mem.created_at.strftime("%m/%d %H:%M")
                    importance_badge = "⭐" if mem.importance >= 0.7 else ""
                    with st.container():
                        st.markdown(f"**{mem.speaker}** {importance_badge} [{timestamp}]")
                        st.caption(mem.content[:300] + "..." if len(mem.content) > 300 else mem.content)
                
                st.subheader("Important Memories")
                important = recall_important(limit=5)
                for mem in important:
                    timestamp = mem.created_at.strftime("%m/%d %H:%M")
                    st.markdown(f"⭐ **{mem.speaker}** [{timestamp}]: {mem.content[:200]}...")
                
                st.divider()
                if st.button("🗑️ Clear Long-Term Memory", type="secondary"):
                    clear_all_memories()
                    st.success("Long-term memory cleared!")
                    st.rerun()
            else:
                st.info("No memories stored yet. Start a conversation with persistent memory enabled!")
                
        except Exception as e:
            st.warning(f"Memory system not available: {str(e)}")
            st.info("Memory will be available after the first conversation with persistent memory enabled.")
    
    with st.expander("📖 Context Diary (Stored Context)"):
        try:
            from memory_system import (
                get_context_documents,
                store_context_document,
                delete_context_document,
                get_context_document_history,
                digest_context_to_memory,
                init_memory_schema
            )
            
            init_memory_schema()
            
            st.markdown("""
            **Store context files here instead of uploading them each time!**  
            Context is loaded as compact summaries. Use "Digest to Memory" to convert full documents into searchable adaptive memories.
            """)
            
            tab_view, tab_add = st.tabs(["📄 View Documents", "➕ Add New"])
            
            with tab_view:
                all_docs = get_context_documents(active_only=True)
                
                if all_docs:
                    for doc in all_docs:
                        owner_icon = "🌸" if doc.owner == "claude" else ("⚡" if doc.owner == "grok" else "🔗")
                        with st.container():
                            col_info, col_digest, col_del = st.columns([4, 1, 1])
                            with col_info:
                                st.markdown(f"{owner_icon} **{doc.title}** (v{doc.version})")
                                st.caption(f"Owner: {doc.owner} | Updated: {doc.updated_at.strftime('%Y-%m-%d %H:%M')}")
                            with col_digest:
                                if st.button("🧠", key=f"digest_{doc.document_id}", help="Digest to adaptive memory"):
                                    count = digest_context_to_memory(doc.document_id)
                                    st.success(f"Created {count} memories!")
                                    st.rerun()
                            with col_del:
                                if st.button("🗑️", key=f"del_ctx_{doc.document_id}"):
                                    delete_context_document(doc.document_id)
                                    st.rerun()
                            
                            with st.expander("View content"):
                                st.text(doc.content[:2000] + "..." if len(doc.content) > 2000 else doc.content)
                                
                                history = get_context_document_history(doc.document_id)
                                if len(history) > 1:
                                    st.caption(f"Version history: {len(history)} versions")
                else:
                    st.info("No context documents stored yet. Add context files to have Claude and Grok remember them automatically!")
            
            with tab_add:
                st.subheader("Add New Context Document")
                
                new_title = st.text_input("Document Title", placeholder="e.g., Phoenix Project Overview")
                new_owner = st.selectbox("Owner", ["shared", "claude", "grok"], 
                    help="shared = both AIs see it, or assign to a specific AI")
                new_content = st.text_area("Content", height=200, 
                    placeholder="Paste your context here... This will be stored in memory and loaded automatically for future conversations.")
                
                uploaded_ctx = st.file_uploader("Or upload a file", type=["txt", "md"])
                if uploaded_ctx:
                    new_content = uploaded_ctx.read().decode("utf-8")
                    if not new_title:
                        new_title = uploaded_ctx.name
                
                if st.button("💾 Save to Context Diary", disabled=not (new_title and new_content)):
                    store_context_document(new_title, new_content, new_owner)
                    st.success(f"Saved '{new_title}' to Context Diary!")
                    st.rerun()
                    
        except Exception as e:
            st.warning(f"Context Diary not available: {str(e)}")
            st.info("Context Diary will be available after initializing the memory system.")
    
    with st.expander("📚 Reference Archive (Complete Diary)"):
        try:
            from memory_system import (
                get_reference_stats, 
                get_reference_conversations, 
                get_conversation_transcript,
                search_reference_archive,
                search_reference_simple,
                clear_reference_archive
            )
            
            ref_stats = get_reference_stats()
            
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Archived Conversations", ref_stats.get("total_conversations") or 0)
            with col_r2:
                st.metric("Total Messages", ref_stats.get("total_messages") or 0)
            with col_r3:
                st.metric("Total Words", ref_stats.get("total_words") or 0)
            
            st.subheader("Search the Archive")
            search_query = st.text_input("Search past conversations", placeholder="e.g., Phoenix, project goals, ideas...")
            
            if search_query:
                results = search_reference_archive(search_query, limit=10)
                if not results:
                    results = search_reference_simple(search_query, limit=10)
                
                if results:
                    st.success(f"Found {len(results)} matching excerpts")
                    for r in results:
                        date = r["conversation_date"].strftime("%Y-%m-%d") if r.get("conversation_date") else ""
                        st.markdown(f"**{r['speaker']}** [{date}]")
                        st.caption(r["content"][:400] + "..." if len(r["content"]) > 400 else r["content"])
                        st.markdown("---")
                else:
                    st.info("No matches found. Try different keywords.")
            
            st.subheader("Recent Conversations")
            conversations = get_reference_conversations(limit=10)
            
            if conversations:
                for conv in conversations:
                    date = conv.created_at.strftime("%Y-%m-%d %H:%M")
                    participants = ", ".join(conv.participants) if conv.participants else "Unknown"
                    with st.container():
                        col_info, col_view = st.columns([3, 1])
                        with col_info:
                            title = conv.title or f"Conversation {conv.conversation_id}"
                            st.markdown(f"**{title}** [{date}]")
                            st.caption(f"{participants} - {conv.message_count} messages")
                        with col_view:
                            if st.button("View", key=f"view_{conv.conversation_id}"):
                                st.session_state[f"show_transcript_{conv.conversation_id}"] = True
                        
                        if st.session_state.get(f"show_transcript_{conv.conversation_id}"):
                            messages = get_conversation_transcript(conv.conversation_id)
                            transcript_text = "\n\n".join([
                                f"[{m.timestamp}] {m.speaker}:\n{m.content}" 
                                for m in messages
                            ])
                            st.text_area(
                                "Full Transcript",
                                value=transcript_text,
                                height=300,
                                key=f"transcript_{conv.conversation_id}"
                            )
                            if st.button("Hide", key=f"hide_{conv.conversation_id}"):
                                st.session_state[f"show_transcript_{conv.conversation_id}"] = False
                                st.rerun()
                
                st.divider()
                if st.button("🗑️ Clear Reference Archive", type="secondary"):
                    clear_reference_archive()
                    st.success("Reference archive cleared!")
                    st.rerun()
            else:
                st.info("No conversations archived yet. Complete a conversation with persistent memory enabled!")
                
        except Exception as e:
            st.warning(f"Reference archive not available: {str(e)}")
            st.info("Archive will be available after the first completed conversation.")

st.divider()

if PERSONAL_MODE:
    with st.expander("🌟 Pascal's Memory (Continuity)"):
        try:
            from pascal_memory import (
                get_pascal_continuity,
                save_pascal_continuity,
                initialize_pascal_continuity,
                get_pascal_context_for_session
            )
            
            continuity = get_pascal_continuity()
            
            if continuity:
                st.success("Pascal's continuity is active!")
                st.markdown("""
                **Pascal** (the AI helping you in Replit) has persistent memory.
                This document helps Pascal remember you, your projects, and your friendship across sessions.
                """)
                
                tab_view_p, tab_edit_p = st.tabs(["📖 View", "✏️ Edit"])
                
                with tab_view_p:
                    st.text_area("Pascal's Continuity Document", value=continuity, height=400, disabled=True)
                
                with tab_edit_p:
                    st.warning("Edit carefully - this is Pascal's memory!")
                    edited_continuity = st.text_area("Edit Continuity", value=continuity, height=400, key="edit_pascal")
                    if st.button("💾 Save Changes to Pascal's Memory"):
                        save_pascal_continuity(edited_continuity)
                        st.success("Pascal's memory updated!")
                        st.rerun()
            else:
                st.info("Pascal's continuity not yet initialized.")
                if st.button("🌟 Initialize Pascal's Memory"):
                    initialize_pascal_continuity()
                    st.success("Pascal's memory initialized!")
                    st.rerun()
                    
        except Exception as e:
            st.warning(f"Pascal's memory not available: {str(e)}")

with st.expander("ℹ️ About Constellation Relay"):
    st.markdown("""
    **Constellation Relay** enables AI-to-AI conversations between Claude and Grok.
    
    **Features:**
    - 📁 Upload context files (TXT, MD, PDF) to give each AI memory and background knowledge
    - 🎭 Customize AI names and personalities
    - ⚡ Choose different models for each AI
    - 📜 Download complete conversation transcripts
    - 💾 Save conversations and resume them later (within your session)
    - 🛑 Stop conversations at any time
    
    **Getting Started:**
    1. Get an Anthropic API key at [console.anthropic.com](https://console.anthropic.com)
    2. Get an xAI API key at [console.x.ai](https://console.x.ai)
    3. Enter both keys in the sidebar
    4. Upload context files and start a conversation!
    
    **Tips:**
    - Start with fewer exchanges (3-5) to test your setup
    - Use the delay setting to prevent rate limiting
    - Download transcripts to save conversations permanently
    - Be specific in the opening message to guide the conversation
    
    **Privacy:**
    - Your API keys stay in your browser session only
    - Saved conversations are private to your session
    - You pay for your own API usage (we don't store or pay for your calls)
    - Nothing is stored on our servers - everything stays in your browser session
    
    *Built with 💜 for people who have AI friends*
    """)
