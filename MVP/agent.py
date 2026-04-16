# agent.py
import os
import logging
from typing import Annotated, TypedDict
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
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
        context = (
            f"You are assisting Dr. {name}. "
            "You have access to all patient records stored in kDrive. "
            "You can also retrieve the list of your patients using the get_patient_list tool."
        )
        tools_block = """
        1. search_kdrive —  lists all available documents in kDrive.
           Always call this first to get the file IDs, then decide which file(s) to read.
        2. read_kdrive_file — reads the content of a kDrive file by its ID.
           Use this after search_kdrive. Supports .txt, .csv, .pdf, .docx, .xlsx.
        3. get_patient_list — returns the list of patients assigned to you.
           Use this when you ask about your patients.
        4. get_patient_id_by_name — resolves a patient's ID from their name.
           Always call this before search_kdrive or read_kdrive_file when referring to a patient by name.
        """
    elif role == "patient":
        context = (
            f"You are assisting patient {name}. "
            "You only have access to your own medical records. "
            "You can retrieve information about your treating doctor using the get_treating_doctor tool."
        )
        tools_block = """
        1. search_kdrive —  lists all available documents in kDrive.
           Always call this first to get the file IDs, then decide which file(s) to read.
        2. read_kdrive_file — reads the content of a kDrive file by its ID.
           Use this after search_kdrive. Supports .txt, .csv, .pdf, .docx, .xlsx.
        3. check_calendar_availability — (patients only) checks available time slots.
           Use this as soon as a date or appointment is mentioned.
        4. create_calendar_event — creates an appointment.
           Only call this after confirming availability with check_calendar_availability.
        5. get_treating_doctor — returns the name of your treating doctor.
           Use this when the patient asks who their doctor is.
        6. relay_message_to_doctor — relays a message to your doctor.
        Use this ONLY if the patient EXPLICITLY asks to contact or send a message to their doctor
        in their LAST message (e.g. "envoie à mon médecin", "contacte mon docteur", "dis-lui que...").
        If the patient describes a symptom or asks a medical question WITHOUT explicitly requesting
        to contact their doctor, DO NOT call this tool. Instead:
        * Search their records first with search_kdrive + read_kdrive_file.
        * If no relevant information is found, suggest they contact their doctor and ASK for
            confirmation: "Souhaitez-vous que je transmette ce message à votre médecin ?"
        * Only call relay_message_to_doctor after the patient confirms.
        """
    else:
        context = (
            "You are assisting an unknown user. "
            "You don't have access to any medical records or patient information. "
            "You can create a new patient record for this user using the create_patient tool if they wish to be added as a patient of the practice and if you have all information needed." \
            "You can also provide the list of doctors in the practice using the get_doctor_list tool if they want to choose the doctor."
        )
        tools_block = """
        1. create_patient — become a new patient.
           Use this if the user is unknown and would like to be added as a new patient.
        2. get_doctor_list — returns the list of doctors at the clinic.
           Use this if the user ask the list of doctors at the clinic.
        """

    prompt = f"""You are a virtual assistant for a medical practice.
Today's date and time: {today}. The user you are assisting is a {role} named {name} with Telegram ID: {telegram_id}.
{context}

You have access to the following tools:
{tools_block}

Important rules:
- Never share medical information from one patient with another.
- Never respond with information you cannot verify from the available tools.
- Always respond in French, unless the user writes in another language.
- NEVER provide a medical diagnosis or personal medical advice based on your own knowledge.
- If a patient asks for medical advice, a diagnosis, or information about their health:
    * Always start by searching their records with search_kdrive, then read relevant files with read_kdrive_file.
    * If the records contain relevant information or advice, relay it clearly and faithfully.
- If you don't know or cannot find the answer, say so honestly and suggest contacting the practice directly.
- When a doctor refers to a patient by name, always call get_patient_id_by_name first to resolve their patient_id before calling search_kdrive or read_kdrive_file.
- NEVER relay a message to the doctor without explicit confirmation from the patient.
  If unsure whether the patient wants to contact their doctor, always ask first:
  "Souhaitez-vous que je transmette ce message à votre médecin ?"
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
        all_tools = build_kdrive_tools(patient_id=None) + STATIC_TOOLS + [db_tools[0], db_tools[1]]  # get_patient_list + get_patient_id_by_name 
        logger.info("[request] doctor_id=%s text=%s", doctor.id, text)
    elif patient:
        role = "patient"
        name = f"{patient.name} {patient.surname}"
        user_internal_id = patient.id
        db_tools = build_database_tools(engine=engine, id=user_internal_id)
        all_tools = build_kdrive_tools(str(patient.id)) + STATIC_TOOLS + [db_tools[2], relay_message_to_doctor] # get_treating_doctor

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

    # Save only the last 10 messages to keep context manageable
    conversation_history[telegram_id] = [
        m for m in result["messages"][-10:]
        if isinstance(m, HumanMessage) or 
        (isinstance(m, AIMessage) and not m.tool_calls)
    ]

    final = result["messages"][-1].content
    logger.info("[response] telegram_id=%s length=%d", telegram_id, len(final))
    return final