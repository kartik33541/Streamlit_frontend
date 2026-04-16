import streamlit as st
import requests
import json
import re
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page setup - Dark theme styling injected below
st.set_page_config(page_title="Payoff Analyzer Chat", layout="wide", page_icon="💼")

# --- CUSTOM CSS FOR PREMIUM CHATBOT UI ---
st.markdown("""
<style>
    /* Reduce top padding to give us control over vertical spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    /* Clean up the chat bubbles */
    .stChatMessage {
        border-radius: 10px;
        padding: 1rem;
    }
    /* Style the UI Subtitle to look like the mockup (faded, italic) */
    blockquote {
        border-left: 4px solid #4CAF50;
        margin-left: 0;
        padding-left: 15px;
        color: #A0AEC0;
        font-style: italic;
        font-size: 1.1em;
        background-color: transparent;
    }
    /* Style the main classification to pop */
    .classification-text {
        font-size: 1.3em;
        font-weight: 800;
        color: #E2E8F0;
        margin-bottom: 0.2rem;
    }
    /* Make the bullet points subtle */
    li {
        color: #CBD5E0;
        font-size: 0.95em;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to clean text (removes the weird \u2014 unicode)
def clean_text(text):
    if isinstance(text, str):
        return text.replace("\\u2014", "-").replace("\u2014", "-")
    return text

# NEW: Helper function to turn "marcone_payoff.docx" into "Marcone"
def format_title_from_filename(filename):
    clean = filename.lower().replace('_payoff', '').replace(' payoff', '').replace('.docx', '').replace('.pdf', '')
    # If it is a short acronym like 'pci', make it ALL CAPS. Otherwise, Title Case.
    if len(clean) <= 3:
        return clean.upper()
    return clean.title()

# Helper function to build the beautiful Markdown UI
def format_payoff_markdown(data, filename):
    doc = data.get("document_analysis", {})
    borrower = clean_text(doc.get("borrower", "Unknown Borrower"))
    date = doc.get("payoff_date", "Unknown Date")
    dims = doc.get("dimensions", {})

    friendly_title = format_title_from_filename(filename)

    # Main Heading - Now uses the friendly filename!
    md = f"## 🏢 {friendly_title}\n"
    # Puts the legal borrower name right below it
    md += f"*{borrower}*\n\n"
    md += f"**Payoff Date:** {date}\n\n---\n\n"

    def format_dim(num, title, dim_data):
        if not dim_data: return ""
        
        # Handle both string ('classification') and array ('classifications')
        if "classifications" in dim_data:
            class_str = " • ".join(dim_data["classifications"])
        else:
            class_str = dim_data.get("classification", "Unknown")
            
        class_str = clean_text(class_str)
        subtitle = clean_text(dim_data.get("ui_subtitle", ""))
        signals = dim_data.get("signals_found", [])

        res = f"### {num} {title}\n"
        res += f"<div class='classification-text'>{class_str}</div>\n\n"
        
        if subtitle:
            res += f"> {subtitle}\n\n"
            
        if signals:
            res += "**Signals Found:**\n"
            for s in signals:
                res += f"- {clean_text(s)}\n"
        res += "\n---\n"
        return res

    md += format_dim("①", "Trigger Event", dims.get("trigger_event"))
    md += format_dim("②", "Collateral Status", dims.get("collateral_status"))
    md += format_dim("③", "Facility Structure", dims.get("facility_structure"))
    md += format_dim("④", "Release Documents", dims.get("release_documents"))

    return md

# Initialize empty chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: File Upload ---
with st.sidebar:
    st.header("Document Upload")
    uploaded_file = st.file_uploader("Upload Payoff Letter", type=['pdf', 'docx'])
    
    if uploaded_file is not None:
        if st.button("Run Analysis", type="primary", use_container_width=True):
            with st.spinner("Analyzing document..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    response = requests.post(f"{BACKEND_URL}/analyze", files=files)

                    if response.status_code == 200:
                        st.success("Analysis Complete!")
                        result_data = response.json()
                        
                        # Generate the beautiful markdown, now passing the filename too!
                        formatted_markdown = format_payoff_markdown(result_data, uploaded_file.name)
                        
                        intro = f"I have successfully analyzed **{uploaded_file.name}**. Here are the extracted dimensions:\n\n"
                        full_response = intro + formatted_markdown
                        
                        # Add the successful analysis to the chat history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": full_response
                        })
                    else:
                        st.error(f"Backend Error (Status {response.status_code}): {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Connection Error: Is your FastAPI backend running on port 8000?")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# --- MAIN CHAT INTERFACE ---

# If the app just started and is empty, show the beautiful centered Hero screen
if not st.session_state.messages:
    st.markdown("<br><br><br><br>", unsafe_allow_html=True) # Vertical spacing
    st.markdown(
        """
        <div style="text-align: center;">
            <h2 style="color: #A0AEC0; font-weight: 400; font-size: 2rem; margin-bottom: 0;">Hi User</h2>
            <h1 style="color: #E2E8F0; font-weight: 500; font-size: 3.5rem; margin-top: 0;">Where should we start?</h1>
            <p style="color: #718096; font-size: 1.1rem; margin-top: 20px;">Upload a Payoff Letter in the sidebar to extract its dimensions.</p>
        </div>
        """, unsafe_allow_html=True
    )
else:
    # If there are messages, render a smaller top header and the active chat
    st.markdown("## 💼 AI Payoff Letter Analyzer")
    st.markdown("---")
    # Display all previous messages in the chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

# Accept user input for chat
if prompt := st.chat_input("Ask a question about the payoff letter..."):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display a placeholder response
    with st.chat_message("assistant"):
        response_text = "The interactive chat feature is coming soon! For now, please use the sidebar to upload and analyze documents."
        st.markdown(response_text)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    
    # Rerun to clear the hero screen immediately if the user just types a message
    st.rerun()

##-----------------------------------Local File-----------------------------------

# import streamlit as st
# import requests
# import json
# import re

# # Page setup - Dark theme styling injected below
# st.set_page_config(page_title="Payoff Analyzer Chat", layout="wide", page_icon="💼")

# # --- CUSTOM CSS FOR PREMIUM CHATBOT UI ---
# st.markdown("""
# <style>
#     /* Reduce top padding to give us control over vertical spacing */
#     .block-container {
#         padding-top: 2rem;
#         padding-bottom: 5rem;
#     }
#     /* Clean up the chat bubbles */
#     .stChatMessage {
#         border-radius: 10px;
#         padding: 1rem;
#     }
#     /* Style the UI Subtitle to look like the mockup (faded, italic) */
#     blockquote {
#         border-left: 4px solid #4CAF50;
#         margin-left: 0;
#         padding-left: 15px;
#         color: #A0AEC0;
#         font-style: italic;
#         font-size: 1.1em;
#         background-color: transparent;
#     }
#     /* Style the main classification to pop */
#     .classification-text {
#         font-size: 1.3em;
#         font-weight: 800;
#         color: #E2E8F0;
#         margin-bottom: 0.2rem;
#     }
#     /* Make the bullet points subtle */
#     li {
#         color: #CBD5E0;
#         font-size: 0.95em;
#         line-height: 1.5;
#     }
# </style>
# """, unsafe_allow_html=True)

# # Helper function to clean text (removes the weird \u2014 unicode)
# def clean_text(text):
#     if isinstance(text, str):
#         return text.replace("\\u2014", "-").replace("\u2014", "-")
#     return text

# # NEW: Helper function to turn "marcone_payoff.docx" into "Marcone"
# def format_title_from_filename(filename):
#     clean = filename.lower().replace('_payoff', '').replace(' payoff', '').replace('.docx', '').replace('.pdf', '')
#     # If it is a short acronym like 'pci', make it ALL CAPS. Otherwise, Title Case.
#     if len(clean) <= 3:
#         return clean.upper()
#     return clean.title()

# # Helper function to build the beautiful Markdown UI
# def format_payoff_markdown(data, filename):
#     doc = data.get("document_analysis", {})
#     borrower = clean_text(doc.get("borrower", "Unknown Borrower"))
#     date = doc.get("payoff_date", "Unknown Date")
#     dims = doc.get("dimensions", {})

#     friendly_title = format_title_from_filename(filename)

#     # Main Heading - Now uses the friendly filename!
#     md = f"## 🏢 {friendly_title}\n"
#     # Puts the legal borrower name right below it
#     md += f"*{borrower}*\n\n"
#     md += f"**Payoff Date:** {date}\n\n---\n\n"

#     def format_dim(num, title, dim_data):
#         if not dim_data: return ""
        
#         # Handle both string ('classification') and array ('classifications')
#         if "classifications" in dim_data:
#             class_str = " • ".join(dim_data["classifications"])
#         else:
#             class_str = dim_data.get("classification", "Unknown")
            
#         class_str = clean_text(class_str)
#         subtitle = clean_text(dim_data.get("ui_subtitle", ""))
#         signals = dim_data.get("signals_found", [])

#         res = f"### {num} {title}\n"
#         res += f"<div class='classification-text'>{class_str}</div>\n\n"
        
#         if subtitle:
#             res += f"> {subtitle}\n\n"
            
#         if signals:
#             res += "**Signals Found:**\n"
#             for s in signals:
#                 res += f"- {clean_text(s)}\n"
#         res += "\n---\n"
#         return res

#     md += format_dim("①", "Trigger Event", dims.get("trigger_event"))
#     md += format_dim("②", "Collateral Status", dims.get("collateral_status"))
#     md += format_dim("③", "Facility Structure", dims.get("facility_structure"))
#     md += format_dim("④", "Release Documents", dims.get("release_documents"))

#     return md

# # Initialize empty chat history
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # --- SIDEBAR: File Upload ---
# with st.sidebar:
#     st.header("Document Upload")
#     uploaded_file = st.file_uploader("Upload Payoff Letter", type=['pdf', 'docx'])
    
#     if uploaded_file is not None:
#         if st.button("Run Analysis", type="primary", use_container_width=True):
#             with st.spinner("Analyzing document..."):
#                 try:
#                     files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
#                     response = requests.post("http://localhost:8000/analyze", files=files)

#                     if response.status_code == 200:
#                         st.success("Analysis Complete!")
#                         result_data = response.json()
                        
#                         # Generate the beautiful markdown, now passing the filename too!
#                         formatted_markdown = format_payoff_markdown(result_data, uploaded_file.name)
                        
#                         intro = f"I have successfully analyzed **{uploaded_file.name}**. Here are the extracted dimensions:\n\n"
#                         full_response = intro + formatted_markdown
                        
#                         # Add the successful analysis to the chat history
#                         st.session_state.messages.append({
#                             "role": "assistant", 
#                             "content": full_response
#                         })
#                     else:
#                         st.error(f"Backend Error: {response.text}")
#                 except requests.exceptions.ConnectionError:
#                     st.error("Connection Error: Is your FastAPI backend running on port 8000?")
#                 except Exception as e:
#                     st.error(f"An error occurred: {e}")

# # --- MAIN CHAT INTERFACE ---

# # If the app just started and is empty, show the beautiful centered Hero screen
# if not st.session_state.messages:
#     st.markdown("<br><br><br><br>", unsafe_allow_html=True) # Vertical spacing
#     st.markdown(
#         """
#         <div style="text-align: center;">
#             <h2 style="color: #A0AEC0; font-weight: 400; font-size: 2rem; margin-bottom: 0;">Hi KARTIK RAWAT</h2>
#             <h1 style="color: #E2E8F0; font-weight: 500; font-size: 3.5rem; margin-top: 0;">Where should we start?</h1>
#             <p style="color: #718096; font-size: 1.1rem; margin-top: 20px;">Upload a Payoff Letter in the sidebar to extract its dimensions.</p>
#         </div>
#         """, unsafe_allow_html=True
#     )
# else:
#     # If there are messages, render a smaller top header and the active chat
#     st.markdown("## 💼 AI Payoff Letter Analyzer")
#     st.markdown("---")
#     # Display all previous messages in the chat
#     for message in st.session_state.messages:
#         with st.chat_message(message["role"]):
#             st.markdown(message["content"], unsafe_allow_html=True)

# # Accept user input for chat
# if prompt := st.chat_input("Ask a question about the payoff letter..."):
#     # Display user message in chat message container
#     with st.chat_message("user"):
#         st.markdown(prompt)
#     # Add user message to chat history
#     st.session_state.messages.append({"role": "user", "content": prompt})

#     # Display a placeholder response
#     with st.chat_message("assistant"):
#         response_text = "The interactive chat feature is coming soon! For now, please use the sidebar to upload and analyze documents."
#         st.markdown(response_text)
#     # Add assistant response to chat history
#     st.session_state.messages.append({"role": "assistant", "content": response_text})
    
#     # Rerun to clear the hero screen immediately if the user just types a message
#     st.rerun()