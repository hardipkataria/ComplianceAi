import streamlit as st

def get_chat_history():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    return st.session_state.chat_history
