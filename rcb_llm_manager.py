import streamlit as st
from langchain_openai import ChatOpenAI
import google.genai as genai
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv
import os

MAAS_API_KEY = os.environ["MAAS_API_KEY"]
MAAS_API_BASE = os.environ["MAAS_API_BASE"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_BASE = os.environ.get("GEMINI_API_BASE")

# def build_prompt(system_prompt: str, user_prompt:str):
#     #print(f"Building prompt with system prompt: {system_prompt} and image prompt: {user_prompt}")
#     return ChatPromptTemplate.from_messages(
#         [
#             ("system", system_prompt),
#             ("user", user_prompt)

#         ]
#     )

def call_llm_to_generate_response(model_choice: str, system_prompt: str, user_prompt: str):
    if not st.session_state.use_default_prompts:
        print("Using custom prompts")
        print("====================")
    print(f"\nGenerating response with... \nmodel_choice: {model_choice} \nsystem_prompt: {system_prompt} \nuser_prompt: {user_prompt}")
    if model_choice == "MaaS":
        print("USING MODEL AS A SERVICE")
        llm = ChatOpenAI(
            openai_api_key=MAAS_API_KEY,
            openai_api_base=MAAS_API_BASE,
            model_name="granite-3-3-8b-instruct",
            temperature=0.05,
            max_tokens=512,
            streaming=True,
            #callbacks=[StreamingStdOutCallbackHandler()],
            top_p=0.9,
            #presence_penalty=0.5,
            model_kwargs={
                "stream_options": {"include_usage": True}
            })
        parser = StrOutputParser()
        # Prompt Template
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                ("human", "{user_prompt}"),
            ]
        )
        prompt_str = prompt.format_prompt(system_prompt=system_prompt, user_prompt=user_prompt)
        print(f"DEBUG: PROMPT STR: {prompt_str.to_string()}")
        print(f"DEBUG: Type of prompt: {type(prompt)}")
        print(f"DEBUG: PROMPT MESSAGES: {prompt.messages}")
        # Create LLM Chain
        chain = prompt | llm
        response = chain.invoke({"system_prompt": system_prompt, "user_prompt": user_prompt})
        print("\nNumber of input tokens: ", response.usage_metadata['input_tokens'])
        print("\nNumber of output tokens: ", response.usage_metadata['output_tokens'])
        response = parser.invoke(response)
        return response
            

    elif model_choice == "Gemini":
        print("USING GEMINI MODEL")

        prompt = f"{system_prompt}\n\n{user_prompt}"
        client = genai.Client(
            api_key=st.session_state.gemini_api_key
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        print(response.text)
        return response.text

    else:
        print("USING LOCAL MODEL")
        print("LOCAL MODEL NOT CONFIGURED YET")
        return "LOCAL MODEL NOT CONFIGURED YET"
        

