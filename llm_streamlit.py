import streamlit as st
from openai import OpenAI
import requests

# Read the API key from Streamlit secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
OPENAI_MODEL = st.secrets["OPENAI_MODEL"]

client = OpenAI(api_key=OPENAI_API_KEY)

st.title("💬 HR Chatbot Assistant")

query = st.text_input("Ask your HR Assistant...")

if st.button("Send"):
    if query.strip():
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an HR assistant that answers employee queries politely and briefly."},
                    {"role": "user", "content": query}
                ]
            )
            st.success(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Error: {str(e)}")
    else:
        st.warning("Please type something before sending!")