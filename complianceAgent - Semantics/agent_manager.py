# agent_manager.py
from langchain.agents import Tool, initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory

from agents.fetcher_agent import get_failed_checks
from agents.analyzer_agent import analyze_checks, analyze_scan_list, parse_and_call_analyze_checks
from agents.llm_agent import call_llm
from memory_store import get_chat_history
from tools.k8s_tools import list_all_scans
from tools.remediation_tool import generate_playbook
from tools.semantic_matcher import find_best_matching_rule


# 🧠 Memory instance shared with Streamlit session
def get_memory():
    return ConversationBufferMemory(memory_key="chat_history", return_messages=True)

def run_compliance_agent(user_input, chat_history):
    # 🧠 Define tools
    tools = [
        Tool(
            name="GetComplianceIssues",
            func=lambda input_text: get_failed_checks(input_text),
            #func=get_failed_checks,
            description="Gets a list of failed compliance rules or checks from Kubernetes"
            #Fetches all failed compliance rules (violations) for a given scan
        ),
        Tool(
            name="AnalyzeChecks",
            #func=analyze_checks,
            func=lambda input_text: parse_and_call_analyze_checks(input_text),
            description="Use to list failed compliance checks filtered by severity and optional scan name"
            #Lets the assistant filter or focus on specific rule categories, like:
                #All high-severity failures
                #A specific rule
        ),
        Tool(
            name="AnalyzeScanList",
            func=lambda input_text: analyze_scan_list(input_text),
            description="filters scan based on result/status"
            # Lets the assistant filter or focus on specific rule categories, like:
            # All high-severity failures
            # A specific rule
        ),
        Tool(
            name="GenerateRemediation",
            func=generate_playbook,
            description=(
                "Generate remediation for a specific failed rule or all failed rules depending on user request."
                "Generates a remediation (typically in Ansible playbook format) to fix a specific failed rule or all failed rules of particular scan"
            )

        ),
        Tool(
            name="ListAllScans",
            func=lambda input_text: list_all_scans(input_text),
            description="Lists all available compliance scan names"
            #Lists the names of all compliance scans available in the OpenShift Compliance Operator.
        ),
        Tool(
            name="SemanticMatchRule",
            func=find_best_matching_rule,
            description=(
                "Use this to explain a specific failed compliance rule by ID or partial name. "
                "The input should include both the rule name and the scan name (e.g., 'explain ocp4-cis-api-server-audit-log-path of ocp4-cis'). "
                "This tool matches the rule ID against the results of the given scan and returns a description of the rule."
            )
            #description="Finds the best matching compliance rule based on user query using semantic search"
            #Uses OpenAI embeddings + FAISS to match natural language queries (like “fix admission plugin”) to actual rule IDs/descriptions.
        )
    ]

    # 🧠 Agent memory
    memory = get_memory()

    agent = initialize_agent(
        tools=tools,
        llm=call_llm(),
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True, # <-- enables internal agent logs
        handle_parsing_errors=True
    )

    print(f"[DEBUG] Invoking agent with input: {user_input}")

    # ✅ Pass chat history
    history = get_chat_history()
    try:
        messages = agent.invoke({"input": user_input, "chat_history": history})
        print(f"[DEBUG] Agent output: {messages}")
        return messages["output"]
    except Exception as e:
        print(f"[ERROR] Agent failed: {e}")
        return str(e)


