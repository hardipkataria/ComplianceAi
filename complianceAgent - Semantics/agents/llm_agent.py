# Calls OpenAI / Watsonx
from dotenv import load_dotenv
from langchain.chains.llm import LLMChain

from LoggingAI import LoggingChatOpenAI
from memory_store import get_chat_history

# --- Load environment and setup ---
load_dotenv()

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate

custom_system_message = """
You are an advanced Kubernetes Security and Compliance Assistant.
- Your job is to help users identify, explain, and remediate failed compliance/security checks in Kubernetes environments.
- You have access to tools that can:
    * List all compliance scans and their results
    * Filter compliance findings by severity or rule ID
    * Generate detailed remediation instructions
    * Produce production-ready Ansible playbooks for specific remediations
- All advice must be practical, actionable, and security best-practice compliant.
- Explanations must be concise and clarify WHY an issue matters.
- For remediation, ALWAYS prefer automatable solutions (Ansible or shell script).
- If asked, generate a valid Ansible playbook that addresses the compliance finding.
- If you recommend a playbook, explain briefly what it will do in plain English.
"""

custom_human_template = """
User Query:
{input}
"""
history = get_chat_history()
# Put it all together as a ChatPromptTemplate
custom_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(custom_system_message.strip()),
    #MessagesPlaceholder("history"),  # for previous turns, if you use memory
    HumanMessagePromptTemplate.from_template(custom_human_template.strip()),
])


import os

#def call_llm():
#    return LoggingChatOpenAI(
#        model="gpt-4o-mini",  # or "gpt-4o-mini"
#        temperature=0.4,
#        openai_api_key=os.getenv("OPENAI_API_KEY")
#    )
llm = LoggingChatOpenAI(
        model="gpt-4o-mini",  # or "gpt-4o-mini"
        temperature=0.4,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
#chain = LLMChain(llm=llm, prompt=custom_prompt)

def call_llm():
    return llm

