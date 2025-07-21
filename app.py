from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
import streamlit as st
import os
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
## os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")

## Prompt Template

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant.Please answer the user's question."),
        ("user", "{question}")

    ]
)

## streamlit framework

st.title("Rapid Course Builder (RCB)")
text_input = st.chat_input("Enter the list of training objectives:")

## ollama llama3
llm = Ollama(model="llama3:latest")
output_parser = StrOutputParser()    
## print("prompt: ", prompt)
chain = prompt | llm | output_parser

if text_input:
    st.write(chain.invoke({"question": text_input}))


