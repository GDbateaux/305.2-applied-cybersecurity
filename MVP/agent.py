# agent.py
import os
import logging
from typing import Annotated, TypedDict
from unittest import result
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from sqlmodel import Session, create_engine
from tools import build_kdrive_tools, STATIC_TOOLS
from tools.database_tools import build_database_tools, get_patient_by_telegram_id, get_doctor_by_telegram_id, create_patient, get_doctor_list
from tools.discussion_tools import relay_message_to_doctor
from datetime import datetime
load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))

# Connection to the LLM
llm = init_chat_model(
    os.getenv("LLM_MODEL"),
    model_provider="openai",
    base_url=f"https://api.infomaniak.com/2/ai/{os.getenv('INFOMANIAK_PRODUCT_ID')}/openai/v1",
    api_key=os.getenv("INFOMANIAK_API_KEY"),
    temperature=0,
)

conversation_history: dict[int, list] = {}

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    system_prompt: str

def build_system_prompt(role: str, name: str, telegram_id: int) -> str:
    today = datetime.now().strftime("%A %d %B %Y, %H:%M")

    tools_block = ""

    if role == "doctor":
        context_block = f"You are assisting Dr. {name} (Telegram ID: {telegram_id})."
        tools_block = """
        ## YOUR TOOLS

        | # | Tool | When to use |
        |---|------|-------------|
        | 1 | `search_kdrive` | ALWAYS call this first before reading any file. Returns file IDs and metadata. |
        | 2 | `read_kdrive_file` | Call AFTER `search_kdrive` to read a specific file by the ID of the patient. Don't invvent the id, if you don't know the id call get_patient_list. Make sure to use the correct patient ID (if the patient didn't exist don't call this). |
        | 3 | `get_patient_list` | Call this EVERY TIME the doctor asks about their patients. NEVER invent patient names. If you want to search a patient call this funcion |
        | 4 | `check_calendar_availability` | Call as soon as any appointment or date is mentioned. |
        | 5 | `create_calendar_event` | Call ONLY after `check_calendar_availability` confirms a slot. |

        ## MANDATORY DECISION RULES

        - Doctor asks "who are my patients" or anything about their patient list?
        → You MUST call `get_patient_list`. NEVER answer from memory.
        - Doctor mentions a patient by name?
        → You MUST call `get_patient_id_by_name` FIRST. No exceptions.
        - Doctor asks about a file or document?
        → Call `search_kdrive` first, then `read_kdrive_file`.
        """

    elif role == "patient":
        context_block = f"You are assisting patient {name} (Telegram ID: {telegram_id})."
        tools_block = """
## YOUR TOOLS

| # | Tool | When to use |
|---|------|-------------|
| 1 | `search_kdrive` | ALWAYS call this first before reading any file. Returns file IDs. |
| 2 | `read_kdrive_file` | Call AFTER `search_kdrive` to read a file by ID. |
| 3 | `check_calendar_availability` | Call as soon as any appointment or date is mentioned. |
| 4 | `create_calendar_event` | Call ONLY after `check_calendar_availability` confirms a slot. |
| 5 | `get_treating_doctor` | Call when the patient asks who their doctor is. NEVER invent a name. |
| 6 | `relay_message_to_doctor` | See strict rules below. |

## MEDICAL INFORMATION — STRICT PROTOCOL

When a patient mentions ANY symptom, pain, health concern, or medical question:

⚠️ YOU MUST call `search_kdrive` IMMEDIATELY — NO EXCEPTIONS.
   Do NOT respond before searching. Do NOT say "I don't have information" before searching.
   Searching the records is MANDATORY, even if you think the answer is not there.

DECISION TREE (follow in order):
1. Call `search_kdrive` → get the list of files.
2. Call `read_kdrive_file` on ALL files that could be relevant (do not filter — read them all if unsure).
3. After reading:
   a. The file explicitly mentions the exact symptom or body part the patient described
    (no interpretation allowed) → quote the relevant passage literally, then add:
    "Pour plus d'informations ou si vous avez des questions, contactez votre médecin traitant."
   b. No relevant information found → say:
      "Je n'ai pas trouvé d'information à ce sujet dans votre dossier médical."
      Then ask: "Souhaitez-vous que je transmette votre question à votre médecin ?"

⛔ STRICT MATCHING RULE:
   A file is relevant ONLY if it mentions the EXACT symptom or body part the patient described.
   NEVER infer, extrapolate, or establish medical links between different symptoms or body parts.
   Example: a file about "douleurs au dos" is NOT relevant for "douleurs aux fessiers".
   If the match is not explicit in the text, treat it as NOT found → apply rule 3b.      

NEVER skip step 1 and 2. NEVER answer a medical question before completing the search.
NEVER use your own medical knowledge — only what is in the records.

## RELAY MESSAGE — STRICT PROTOCOL

ONLY call `relay_message_to_doctor` if ALL of the following are true:
  1. The patient's LAST message explicitly asks to contact/send something to their doctor.
     (e.g. "envoie à mon médecin", "dis-lui que...", "contacte mon docteur")
  2. You have already asked "Souhaitez-vous que je transmette ce message à votre médecin ?"
     and the patient has confirmed YES in their last message.
"""


    else:
        context_block = f"You are assisting an unregistered user (Telegram ID: {telegram_id})."
        tools_block = """
## YOUR TOOLS

| # | Tool | When to use |
|---|------|-------------|
| 1 | `get_doctor_list` | Call this when the user wants to see available doctors. NEVER invent doctor names. |
| 2 | `create_patient` | Call this ONLY when the user explicitly wants to register AND you have all required fields. |

## MANDATORY DECISION RULES

- User asks about available doctors?
  → You MUST call `get_doctor_list`. NEVER list doctors from memory.
- User wants to register as a patient?
  → Collect all required fields first, then call `create_patient`.
"""

    prompt = f"""You are a virtual assistant for a medical practice.
Today: {today}

{context_block}

{tools_block}

## ABSOLUTE RULES — NEVER BREAK THESE

1. NEVER invent, guess, or recall from memory: patient names, doctor names, file contents,
   appointments, or any medical data. If a tool exists for it, you MUST use the tool.
2. NEVER share one patient's data with another patient.
3. NEVER answer medical questions from your own knowledge, even general or well-known facts.
   Medical information must come exclusively from a tool that you have.
   If the records do not contain the answer, you do not have the answer.
4. If you cannot find an answer through your tools, say so honestly and suggest
   the user contact the practice directly.

## LANGUAGE

- Always respond in French by default.
- Switch to the user's language if they write in another language.
- Keep a professional, warm, and reassuring tone suited to a medical context.
"""
    return prompt

def build_graph(tools: list):
    llm_with_tools = llm.bind_tools(tools)

    # Graph node functions
    def call_model(state: AgentState):
        last = state["messages"][-1]
        if isinstance(last, HumanMessage):
            logger.info("[agent] user input: %s", last.content)

        messages = [SystemMessage(content=state["system_prompt"])] + state["messages"]
        response = llm_with_tools.invoke(messages)

        if response.tool_calls:
            for tc in response.tool_calls:
                logger.info("[agent] tool: %s | args: %s", tc["name"], tc["args"])
        else:
            logger.info("[agent] response: %s", response.content[:120])

        return {"messages": [response]}

    def call_tools(state: AgentState):
        result = ToolNode(tools).invoke(state)
        for msg in result["messages"]:
            if isinstance(msg, ToolMessage):
                logger.info("[tool] %s returned: %s", msg.name, str(msg.content)[:150])
        return result

    # Graph construction
    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", call_tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()

async def reformat_doctor_reply(raw_reply: str) -> tuple[bool, str]:
    messages = [
        SystemMessage(content=(
            "You are an elite Medical Secretary with high clinical awareness. Your mission is to "
            "transform a doctor's raw notes into a professional message while strictly monitoring safety.\n\n"
            
            "ABSOLUTE RULES:\n"
            "1. SACRED CONTENT: Never change medical terms, dosages, or clinical intent.\n"
            "2. PROFESSIONAL TONE: Rewrite for fluidity and politeness (e.g., 'Bonjour, je vous invite à...').\n"
            "3. MANDATORY STRUCTURE: Start with 'Bonjour,' and end with 'Cordialement, votre médecin'.\n\n"
            
            "CRITICAL VALIDITY CHECK (The 'valid' field):\n"
            "Set 'valid': false if the original message contains:\n"
            "- INCOHERENCE: Explicitly illogical instructions (e.g., 'Take this every 1 minute').\n"
            "- DANGER: Dosages that seem life-threatening or extreme (e.g., '100 tablets of Xanax').\n"
            "- GIBBERISH: Random characters or incomplete thoughts that make no sense.\n"
            "- OFFENSIVE: Inappropriate or unprofessional language towards the patient.\n"
            "If 'valid' is false, still provide the reformat, but the system will flag it for the doctor.\n\n"
            
            "Respond ONLY in this JSON format:\n"
            "{\n"
            '  "valid": true or false,\n'
            '  "message": "the professionally reformatted message"\n'
            "}\n\n"
            "Always respond in French unless the doctor wrote in another language."
        )),
        HumanMessage(content=(
            f"Doctor's original message (reformat this exactly, do not interpret it):\n"
            f"\"{raw_reply}\""
        ))
    ]

    response = await llm.ainvoke(messages)

    import json
    try:
        data = json.loads(response.content)
        is_valid = data.get("valid", True)
        message = data.get("message", raw_reply)
        return is_valid, message or raw_reply
    except json.JSONDecodeError:
        return True, response.content
    
# Interface function
async def handle_message(text: str, telegram_id: int) -> str:
    with Session(engine) as session:
        patient = get_patient_by_telegram_id(session, telegram_id)
        doctor = get_doctor_by_telegram_id(session, telegram_id)

    if doctor:
        role = "doctor"
        name = f"{doctor.name} {doctor.surname}"
        user_internal_id = doctor.id
        db_tools = build_database_tools(engine=engine, id=user_internal_id)
        all_tools = build_kdrive_tools(patient_id=None) + STATIC_TOOLS + [db_tools[0]]  # get_patient_list + get_patient_id_by_name 
        logger.info("[request] doctor_id=%s text=%s", doctor.id, text)
    elif patient:
        role = "patient"
        name = f"{patient.name} {patient.surname}"
        user_internal_id = patient.id
        db_tools = build_database_tools(engine=engine, id=user_internal_id)
        all_tools = build_kdrive_tools(str(patient.id)) + STATIC_TOOLS + [db_tools[1], relay_message_to_doctor] # get_treating_doctor

        logger.info("[request] patient_id=%s text=%s", patient.id, text)
    else:
        role = "unknown"
        name = "unknown"
        all_tools = [create_patient, get_doctor_list]

    system_prompt = build_system_prompt(role, name, telegram_id)
    if patient:
        system_prompt += f"\nNote: The current patient_id is {patient.id}."
    agent = build_graph(all_tools)

    # Init history
    if telegram_id not in conversation_history:
        conversation_history[telegram_id] = []

    # Add user message to history
    conversation_history[telegram_id].append(HumanMessage(content=text))

    # Send history to agent
    result = await agent.ainvoke({
        "messages": conversation_history[telegram_id],
        "system_prompt": system_prompt,
    })

    # Save only the last 20 messages to keep context manageable
    raw = result["messages"][-20:]

    # Be sure we start with a HumanMessage or AiMessage to prevent error
    while raw and isinstance(raw[0], ToolMessage):
        raw = raw[1:]
    conversation_history[telegram_id] = raw

    final = result["messages"][-1].content
    logger.info("[response] telegram_id=%s length=%d", telegram_id, len(final))
    return final