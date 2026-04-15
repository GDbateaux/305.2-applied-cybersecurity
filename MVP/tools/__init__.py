from tools.kdrive_tools import search_kdrive, read_kdrive_file, summarize_and_store_feedback
from tools.calendar_tools import check_calendar_availability, create_calendar_event
from tools.web_search_tool import search_internet

ALL_TOOLS = [
    search_kdrive,
    read_kdrive_file,
    summarize_and_store_feedback,
    check_calendar_availability,
    create_calendar_event,
    search_internet,
]