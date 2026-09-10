import re
import threading
import time

import streamlit as st
from api_client import query_backend


# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Hardware RAG Assistant",
    page_icon="🤖",
    layout="centered"
)


# ==================================================
# 2. SAMPLE PROMPTS
#    Shown once, only on the empty-state welcome screen.
#    Not duplicated in the sidebar to avoid repeating
#    the same four questions twice.
# ==================================================

SAMPLE_PROMPTS = [
    {"icon": "🔌", "text": "What is the operating voltage of the Arduino Uno?"},
    {"icon": "💾", "text": "How much flash memory does the Arduino Uno have?"},
    {"icon": "🖨️", "text": "What should I do if the 3D printer filament jams?"},
    {"icon": "🔗", "text": "What interface does the Raspberry Pi Pico use for I2C?"},
]

DOCS = [
    {"icon": "🔧", "name": "Arduino Uno"},
    {"icon": "🖨️", "name": "Creality Ender-3 S1"},
    {"icon": "🍓", "name": "Raspberry Pi Pico"},
]

def unique_sources_label(index):
    """
    Build a "📚 Sources" label that is unique per message index, using
    invisible zero-width-space characters as an appendix.

    Newer Streamlit versions let st.expander take a `key=` argument to
    disambiguate repeated widgets, but that parameter isn't available
    on older Streamlit versions (it raises "unexpected keyword
    argument 'key'"). Every expander in this app used the exact same
    visible label ("📚 Sources"), which is what caused Streamlit to
    mix up open/closed state between different messages' expanders.
    Appending invisible characters makes each label text-unique --
    and therefore each widget identity-unique -- without needing the
    key parameter at all, so this works on any Streamlit version.
    """
    return "📚 Sources" + ("\u200b" * index)


# ==================================================
# CITATION MARKER, e.g. "[arduino_uno.pdf | Page: 2 | Chunk: 1]"
# ==================================================

CITATION_PATTERN = re.compile(
    r"\s*\[\s*([^\[\]|]+?)\s*\|\s*Page:?\s*(\d+)\s*\|\s*Chunk:?\s*(\d+)\s*\]",
    re.IGNORECASE
)


def extract_citations(answer_text):
    """
    Pull the inline citation markers out of the model's answer and use
    THEM (not the backend's raw retrieval list) as the source of truth
    for which documents were actually used.

    A RAG backend's "sources" field is usually just every chunk that
    was retrieved during search -- not necessarily every chunk the
    model ended up citing. Parsing the model's own inline citations
    avoids showing a document as a "source" when it was retrieved but
    never actually referenced in the answer.

    Returns (clean_text, cited_sources):
      - clean_text: the answer with citation brackets removed, so the
        reader sees plain, uninterrupted prose.
      - cited_sources: a de-duplicated list of {"file": ..., "page": ...}
        dicts, sorted by filename then ascending page number -- not by
        the order the model happened to cite them in the text, which
        can look reversed (e.g. page 38 mentioned before page 18).
    """
    cited_sources = []
    seen = set()

    for match in CITATION_PATTERN.finditer(answer_text):
        filename, page, _chunk = match.group(1).strip(), match.group(2), match.group(3)
        key = (filename, page)
        if key not in seen:
            seen.add(key)
            cited_sources.append({"file": filename, "page": page})

    cited_sources.sort(key=lambda s: (s["file"], int(s["page"])))

    clean_text = CITATION_PATTERN.sub("", answer_text).strip()
    clean_text = re.sub(r"[ \t]{2,}", " ", clean_text)

    return clean_text, cited_sources


def render_source_pills(sources):
    """Render a list of sources as pill badges. Accepts either the
    {"file", "page"} dicts produced by extract_citations, or plain
    filename strings (used as a fallback when an answer has no inline
    citations to parse, e.g. an older/different backend response)."""

    def label_for(source):
        if isinstance(source, dict):
            page = source.get("page")
            return f"{source['file']} · p.{page}" if page else source["file"]
        return str(source)

    pills = "".join(
        f'<span class="source-pill">📄 {label_for(s)}</span>'
        for s in sources
    )
    st.markdown(pills, unsafe_allow_html=True)


# ==================================================
# 3. CUSTOM CSS
# ==================================================

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        /* Keep Streamlit's native header and menu visible
           so built-in Settings and Theme remain accessible. */

        /* Hide only the footer */
        footer { visibility: hidden; }

        /* ---------- Layout ---------- */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 7rem;
            max-width: 820px;
        }

        /* ---------- Branded header ---------- */
        .app-header {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-bottom: 0.15rem;
        }
        .app-header .logo-badge {
            width: 44px;
            height: 44px;
            flex-shrink: 0;
            border-radius: 13px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
        }
        .app-header h1 {
            font-size: 1.55rem;
            font-weight: 700;
            margin: 0;
            line-height: 1.2;
        }
        .app-subtitle {
            color: var(--text-color, #6b7280);
            opacity: 0.65;
            font-size: 0.93rem;
            margin: 0.3rem 0 1.6rem 0;
        }

        /* ---------- Chat bubbles ---------- */
        [data-testid="stChatMessage"] {
            padding: 0.9rem 1.05rem;
            margin-bottom: 0.15rem;
            border-radius: 16px;
            border: 1px solid transparent;
            animation: fadeIn 0.25s ease-in-out;
        }
        /* User: a tinted bubble, like ChatGPT / Claude */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: rgba(99, 102, 241, 0.07);
            border-color: rgba(99, 102, 241, 0.15);
            margin-top: 0.9rem;
        }
        /* Assistant: plain flowing text, no card -- just a hairline
           divider underneath, closer to how Claude/ChatGPT render
           model replies (the reply IS the page, not a boxed chip) */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: transparent;
            border: none;
            border-bottom: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 0;
            padding-left: 0;
            padding-right: 0;
            padding-bottom: 1.3rem;
            margin-bottom: 0.9rem;
        }
        [data-testid="stChatMessage"] p {
            font-size: 0.97rem;
            line-height: 1.65;
            margin-bottom: 0.4rem;
        }

        /* Branded, consistent avatar colors (instead of Streamlit's
           per-session random hash color) */
        [data-testid="chatAvatarIcon-assistant"] {
            background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        }
        [data-testid="chatAvatarIcon-user"] {
            background: #e2e5ea !important;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        /* ---------- Thinking indicator ---------- */
        .thinking-dots {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 0.35rem 0;
        }
        .thinking-dots span {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #a1a8b5;
            animation: thinking-bounce 1.2s infinite ease-in-out;
        }
        .thinking-dots span:nth-child(2) { animation-delay: 0.15s; }
        .thinking-dots span:nth-child(3) { animation-delay: 0.3s; }
        @keyframes thinking-bounce {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }

        /* ---------- Chat input ---------- */
        [data-testid="stChatInput"] textarea {
            border-radius: 14px !important;
        }
        [data-testid="stChatInput"] {
            box-shadow: 0 2px 14px rgba(0, 0, 0, 0.06);
            border-radius: 16px;
        }
        [data-testid="stChatInput"] textarea:disabled {
            opacity: 0.55;
            cursor: default;
        }

        /* ---------- Stop generating button ---------- */
        .stop-btn-row {
            display: flex;
            justify-content: center;
            margin: 0.3rem 0 0.6rem 0;
        }
        .stop-btn-row .stButton > button {
            border-radius: 999px !important;
            border: 1px solid rgba(148, 163, 184, 0.35) !important;
            background: var(--secondary-background-color, #f4f4f6);
            font-size: 0.85rem;
            padding: 0.3rem 1rem;
            color: #4b5563;
        }
        .stop-btn-row .stButton > button:hover {
            border-color: #ef4444 !important;
            color: #ef4444 !important;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
        }

        /* ---------- Buttons (sidebar + suggestion cards) ---------- */
        .stButton > button {
            border-radius: 12px !important;
            border: 1px solid rgba(148, 163, 184, 0.25) !important;
            font-weight: 500;
            transition: all 0.15s ease-in-out;
            text-align: left;
        }
        .stButton > button:hover {
            border-color: #6366f1 !important;
            color: #6366f1 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
        }

        /* ---------- Sidebar doc chips ---------- */
        .doc-chip {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.5rem 0.7rem;
            border-radius: 10px;
            background: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.15);
            margin-bottom: 0.45rem;
            font-size: 0.9rem;
        }

        /* ---------- Source pills ---------- */
        .source-pill {
            display: inline-block;
            padding: 0.25rem 0.7rem;
            margin: 0.15rem 0.3rem 0.15rem 0;
            border-radius: 999px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.25);
            font-size: 0.8rem;
            color: #6366f1;
        }

        /* ---------- Empty-state welcome ---------- */
        .welcome-wrap {
            text-align: center;
            padding: 2.2rem 0 1.4rem 0;
        }
        .welcome-wrap .welcome-badge {
            width: 64px;
            height: 64px;
            margin: 0 auto 1rem auto;
            border-radius: 18px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.3);
        }
        .welcome-wrap h2 {
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }
        .welcome-wrap p {
            color: var(--text-color, #6b7280);
            opacity: 0.65;
            font-size: 0.92rem;
            margin-bottom: 1.6rem;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.35);
            border-radius: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# 4. INITIALIZE SESSION STATE
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# True exactly while a backend request is in flight. Used to lock the
# chat input, sidebar, and suggestion buttons so a new question can't
# be submitted (and queued up) while the current one is still running
# -- which is what previously let the same question get sent 2-3
# times in a row.
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# The question currently being answered. Set the moment a prompt is
# submitted, then actually processed on the NEXT run -- see section 7
# for why this two-step handoff is needed.
if "processing_prompt" not in st.session_state:
    st.session_state.processing_prompt = None

# The backend call runs on a background thread so a "Stop generating"
# click can be noticed (and acted on) within a fraction of a second,
# instead of only after query_backend() finally returns.
if "bg_thread" not in st.session_state:
    st.session_state.bg_thread = None
if "bg_event" not in st.session_state:
    st.session_state.bg_event = None
if "bg_result" not in st.session_state:
    st.session_state.bg_result = None
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False


# ==================================================
# 5. MAIN HEADER
# ==================================================

st.markdown(
    """
    <div class="app-header">
        <div class="logo-badge">🤖</div>
        <h1>Hardware RAG Assistant</h1>
    </div>
    <div class="app-subtitle">
        Ask questions grounded strictly in your indexed hardware documentation.
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# 6. SIDEBAR
# ==================================================

with st.sidebar:

    st.header("⚙️ Controls")

    # Clear conversation
    if st.button(
        "🗑️  Clear Chat",
        use_container_width=True,
        disabled=st.session_state.is_processing
    ):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()

    st.divider()

    # Available documentation
    st.markdown("### 📚 Available Documentation")

    for doc in DOCS:
        st.markdown(
            f"""<div class="doc-chip">{doc['icon']} <span>{doc['name']}</span></div>""",
            unsafe_allow_html=True
        )


# ==================================================
# 7. RESOLVE INCOMING PROMPT
#    (typed input OR a clicked welcome suggestion)
#
#    Submitting a question does NOT call the backend on
#    this same run. Streamlit reruns are synchronous and
#    blocking -- if we called the (slow) backend right
#    here, the chat input's "disabled" state wouldn't
#    actually reach the browser until the network call
#    already finished, leaving a window where a second
#    submission could sneak in and queue up (which is
#    exactly how the same question ended up being sent
#    2-3 times in a row).
#
#    Instead: lock immediately, rerun immediately (fast,
#    no network call), and only THEN -- on the very next
#    run, with the input already rendered as disabled --
#    actually call the backend. See section 10.
# ==================================================

typed_prompt = st.chat_input(
    "Waiting for response..." if st.session_state.is_processing
    else "What would you like to know about the hardware?",
    disabled=st.session_state.is_processing
)

new_prompt = typed_prompt or st.session_state.pending_prompt
st.session_state.pending_prompt = None

if new_prompt and not st.session_state.is_processing:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": new_prompt
        }
    )
    st.session_state.processing_prompt = new_prompt
    st.session_state.is_processing = True
    st.session_state.stop_requested = False
    st.rerun()


# ==================================================
# 8. EMPTY STATE (welcome screen with suggestion cards)
#    Only shown when there's no conversation yet AND no
#    question is queued up or being processed this run.
# ==================================================

if not st.session_state.messages and not st.session_state.is_processing:

    st.markdown(
        """
        <div class="welcome-wrap">
            <div class="welcome-badge">🤖</div>
            <h2>How can I help you today?</h2>
            <p>Ask a question below, or try one of these to get started.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    columns = [col1, col2]

    for i, sp in enumerate(SAMPLE_PROMPTS):
        with columns[i % 2]:
            if st.button(
                f"{sp['icon']}  {sp['text']}",
                key=f"welcome_sample_{i}",
                use_container_width=True,
                disabled=st.session_state.is_processing
            ):
                st.session_state.pending_prompt = sp["text"]
                st.rerun()


# ==================================================
# 9. RENDER PREVIOUS CONVERSATION
# ==================================================

for i, message in enumerate(st.session_state.messages):

    # Choose avatar based on message role
    avatar = (
        "👤"
        if message["role"] == "user"
        else "🤖"
    )

    with st.chat_message(
        message["role"],
        avatar=avatar
    ):

        # Display the message
        st.markdown(message["content"])

        # Display sources for assistant messages
        if (
            message["role"] == "assistant"
            and message.get("sources")
        ):

            # A unique key per message index -- without this, every
            # expander shares the identical label "Sources", and
            # Streamlit can mix up which expander's open/closed state
            # belongs to which message once the message list shifts
            # between reruns, producing the ghosted/duplicated
            # expander glitch.
            with st.expander(unique_sources_label(i)):
                render_source_pills(message["sources"])


# ==================================================
# 10. PROCESS USER QUESTION
#     Runs only when the previous run already locked the
#     input (see section 7). The user's own message is
#     already in session_state.messages and rendered by
#     the history loop above -- this block only concerns
#     itself with getting (or cancelling) the answer.
#
#     query_backend() runs on a background thread instead
#     of blocking here directly. That's what lets a
#     "Stop generating" click take effect almost
#     instantly: we simply stop waiting on the thread and
#     show "You stopped this response," even though the
#     backend call may still be quietly finishing in the
#     background and getting its result discarded. This
#     is the same trade-off ChatGPT/Claude make -- a
#     plain Python function call can't be forcibly
#     interrupted mid-flight without its own cooperation.
# ==================================================

if st.session_state.is_processing:

    prompt = st.session_state.processing_prompt

    # Kick off the background request once, the first time we see
    # this prompt being processed.
    if st.session_state.bg_thread is None:

        result_holder = {}
        done_event = threading.Event()

        def _run_backend_call(prompt=prompt, result_holder=result_holder, done_event=done_event):
            try:
                result_holder["response"] = query_backend(prompt)
            except Exception as exc:
                result_holder["error"] = str(exc)
            finally:
                done_event.set()

        thread = threading.Thread(target=_run_backend_call, daemon=True)
        thread.start()

        st.session_state.bg_thread = thread
        st.session_state.bg_event = done_event
        st.session_state.bg_result = result_holder

    done_event = st.session_state.bg_event
    result_holder = st.session_state.bg_result


    def _finish_processing():
        """Release the lock/thread bookkeeping and do one clean
        rerun, so the final message is drawn exactly once, by the
        history loop, rather than by this live block too."""
        st.session_state.is_processing = False
        st.session_state.processing_prompt = None
        st.session_state.bg_thread = None
        st.session_state.bg_event = None
        st.session_state.bg_result = None
        st.session_state.stop_requested = False
        st.rerun()


    with st.chat_message("assistant", avatar="🤖"):

        if not done_event.is_set():

            # Still waiting on the backend -- show the thinking
            # indicator and a Stop button.
            st.markdown(
                '<div class="thinking-dots"><span></span><span></span><span></span></div>',
                unsafe_allow_html=True
            )

            st.markdown('<div class="stop-btn-row">', unsafe_allow_html=True)
            stop_clicked = st.button("⏹  Stop generating", key="stop_generating_btn")
            st.markdown('</div>', unsafe_allow_html=True)

            if stop_clicked:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "You stopped this response."
                    }
                )
                _finish_processing()

            # Short poll: wait a beat, then rerun to check again.
            # Keeping this interval short is what makes the Stop
            # button feel near-instant rather than sluggish.
            time.sleep(0.3)
            st.rerun()

        else:

            # ==========================================
            # BACKGROUND CALL FINISHED
            # ==========================================

            if "error" in result_holder:

                error_message = f"Something went wrong: {result_holder['error']}"
                st.error(f"⚠️ {error_message}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"⚠️ {error_message}"
                    }
                )

            else:

                response = result_holder["response"]

                # ==========================================
                # SUCCESSFUL RESPONSE
                # ==========================================

                if response["status"] == "success":

                    raw_answer = response["data"]["answer"]

                    # Only show sources the model actually cited inline
                    # (e.g. "[arduino_uno.pdf | Page: 2 | Chunk: 1]"). We
                    # deliberately do NOT fall back to the backend's raw
                    # "sources" field -- that field reflects everything
                    # retrieved during search, which still gets populated
                    # even when the model couldn't find an answer (e.g.
                    # "I don't know based on the provided documents.").
                    # Showing those would misleadingly imply the answer
                    # was grounded when it wasn't.
                    answer, sources = extract_citations(raw_answer)

                    st.markdown(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": sources
                        }
                    )

                # ==========================================
                # FAILED RESPONSE
                # ==========================================

                else:

                    error_message = response["message"]

                    st.error(f"⚠️ {error_message}")

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": f"⚠️ {error_message}"
                        }
                    )

            _finish_processing()