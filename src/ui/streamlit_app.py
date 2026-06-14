import streamlit as st
import requests
import json

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Text-to-SQL Agent",
    page_icon="🗄️",
    layout="wide"
)

st.title("Text-to-SQL Agent")
st.caption("Ask questions about the ClassicModels database in plain English")

# ============================================================
# SESSION STATE - persists chat history between reruns
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# ============================================================
# SIDEBAR - connection settings
# ============================================================
with st.sidebar:
    st.header("Settings")
    api_url = st.text_input(
        "API URL",
        value="http://app:8000",
        help="FastAPI backend URL"
    )
    st.divider()
    st.markdown("**Example Questions:**")
    example_questions = [
        "How many customers are from the USA?",
        "List all products and their prices",
        "Show total payments per customer",
        "Which employees report to Anthony Bow?",
        "Count orders per status",
        "Get all shipped orders from German customers"
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True):
            st.session_state.pending_question = q

    st.divider()
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
            # Display assistant response
            content = message["content"]
            st.write(content["summary"])

            # Show details in expander
            with st.expander("View Details"):
                col1, col2 = st.columns(2)

                with col2:
                    st.markdown("**Generated SQL:**")
                    if content.get("sql"):
                        st.code(content["sql"], language="sql")

                st.markdown("**Results:**")
                if content.get("result"):
                    st.dataframe(content["result"])
                else:
                    st.info("No results returned.")

                if content.get("error"):
                    st.error(f"Error: {content['error']}")


# ============================================================
# HANDLE INPUT
# Either from chat input or sidebar button click
# ============================================================
def process_question(question: str):
    """Send question to FastAPI and display response."""

    # Add user message to history
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    # Display user message
    with st.chat_message("user"):
        st.write(question)

    # Call FastAPI endpoint
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    f"{api_url}/agent/sql",
                    json={"question": question},
                    timeout=60
                )
                data = response.json()

                # Display summary
                st.write(data.get("summary", "No summary available."))

                # Show details in expander
                with st.expander("View Details"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Decomposition:**")
                        if data.get("decomposition"):
                            st.json(data["decomposition"])
                        else:
                            st.info("No decomposition available.")

                    with col2:
                        st.markdown("**Generated SQL:**")
                        if data.get("sql"):
                            st.code(data["sql"], language="sql")
                        else:
                            st.info("No SQL generated.")

                    st.markdown("**Results:**")
                    if data.get("result"):
                        st.dataframe(data["result"])
                    else:
                        st.info("No results returned.")

                    # Status badge
                    if data.get("status") == "success":
                        st.success("Status: Success")
                    else:
                        st.error(f"Status: Failed - {data.get('error', 'Unknown error')}")

                # Save to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data
                })

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API. Make sure FastAPI is running.")
            except requests.exceptions.Timeout:
                st.error("Request timed out. The query took too long.")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")


# Handle sidebar button click
if "pending_question" in st.session_state:
    q = st.session_state.pending_question
    del st.session_state.pending_question
    process_question(q)

# Handle chat input
if prompt := st.chat_input("Ask a question about the database..."):
    process_question(prompt)