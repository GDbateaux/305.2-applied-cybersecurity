import caldav
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

def create_calendar_event(summary, start_time, duration_hours=1, description=""):
    # --- Configuration ---
    # Use an Application Password from Infomaniak Manager (Security > App Passwords)
    url = "https://sync.infomaniak.com/calendars"
    username = os.getenv("CALENDAR_USERNAME")
    password = os.getenv("CALENDAR_PASSWORD")

    try:
        # 1. Connect to the server
        client = caldav.DAVClient(url=url, username=username, password=password)
        principal = client.principal()
        
        # 2. Get your primary calendar
        # Infomaniak usually lists the primary calendar first
        calendars = principal.calendars()
        if not calendars:
            print("No calendars found.")
            return
        
        my_calendar = calendars[0]
        end_time = start_time + timedelta(hours=duration_hours)

        # 3. Check for availability (Optional but recommended)
        conflicts = my_calendar.date_search(start=start_time, end=end_time)
        
        if len(conflicts) > 0:
            print(f"Conflict detected: You already have {len(conflicts)} event(s) at this time.")
            return None

        # 4. Create the event
        new_event = my_calendar.save_event(
            dtstart=start_time,
            dtend=end_time,
            summary=summary,
            description=description
        )
        
        print(f"Event '{summary}' successfully created!")
        return new_event

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# --- Example Usage ---
if __name__ == "__main__":
    # Define your event details
    event_title = "Test"
    # Set time for tomorrow at 2 PM
    start_dt = datetime(2026, 4, 15, 15, 30, 0)
    
    create_calendar_event(event_title, start_dt, duration_hours=1.5)