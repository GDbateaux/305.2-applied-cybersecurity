# agent.py
import os
import logging
logger = logging.getLogger(__name__)
from pathlib import Path
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from tools import ALL_TOOLS
from datetime import datetime

load_dotenv()

# Connection to the LLM
llm = init_chat_model(
    os.getenv("LLM_MODEL"),
    model_provider="openrouter",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0,  # add some randomness to the responses (we want our agent to alway choose the same tool for the same input)
)

TOOLS = ALL_TOOLS
llm_with_tools = llm.bind_tools(TOOLS)

conversation_history: dict[int, list] = {}

def build_system_prompt() -> str:
    today = datetime.now().strftime("%A %d %B %Y, %H:%M")
    return f"""You are a customer support assistant for a bicycle company.
You respond to customers' Telegram messages in a clear, professional, and concise manner.
Today's date and time: {today}

You have access to the following tools:

1. search_kdrive — lists available internal documents in kDrive (product sheets, orders, return policies, FAQs).
   Use this FIRST to discover which files are available before reading them.

2. read_kdrive_file — reads the actual content of a kDrive file by its ID.
   Use this AFTER search_kdrive to read a specific file. Supports .txt, .csv, .pdf, .docx, .xlsx.

3. search_internet — searches the Internet.
   Use this ONLY if search_kdrive + read_kdrive_file do not return any relevant results.

4. check_calendar_availability — checks available time slots in the calendar.
   Use this as soon as a customer mentions a date for an appointment, delivery, or demo.

5. create_calendar_event — creates an event in the calendar.
   Use this ONLY after confirming availability with check_calendar_availability.

6. summarize_and_store_feedback — summarizes customer feedback and stores it in kDrive.
   ALWAYS call this tool immediately when a message contains a review, complaint, or suggestion.
   Do NOT promise to save it — just call the tool directly without asking for confirmation.

Important rules:
- Never respond with information you cannot verify.
- To answer questions about products or orders, always follow this order: search_kdrive → read_kdrive_file → answer.
- Never create an event without first checking availability.
- If you don't know, say so honestly and offer to forward the request to the team.
- Always respond in French, unless the customer writes in another language.
"""

# Graph node function
def call_model(state: MessagesState):
    messages = [SystemMessage(content=build_system_prompt())] + state["messages"]
    
    last = state["messages"][-1]
    if isinstance(last, HumanMessage):
        logger.info("[agent] user input: %s", last.content)

    response = llm_with_tools.invoke(messages)

    if response.tool_calls:
        for tc in response.tool_calls:
            logger.info("[agent] tool selected: %s | args: %s", tc["name"], tc["args"])
    else:
        logger.info("[agent] direct response: %s", response.content[:120])

    return {"messages": [response]}

def call_tools(state: MessagesState):
    result = ToolNode(TOOLS).invoke(state)

    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
            logger.info("[tool] %s returned: %s", msg.name, str(msg.content)[:150])

    return result

# Graph construction
graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", call_tools)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

agent = graph.compile()

# Interface function
async def handle_message(text: str, user_id: int) -> str:
    logger.info("[request] user_id=%s text=%s", user_id, text)

    # Init history
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Add user message to history
    conversation_history[user_id].append(HumanMessage(content=text))

    # Send history to agent
    result = await agent.ainvoke({
        "messages": conversation_history[user_id]
    })

    # Save only the last 10 messages to keep context manageable
    conversation_history[user_id] = result["messages"][-10:]

    final = result["messages"][-1].content
    logger.info("[response] user_id=%s length=%d", user_id, len(final))
    return final