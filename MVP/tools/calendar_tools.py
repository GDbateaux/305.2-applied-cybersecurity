import caldav
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
URL = "https://sync.infomaniak.com/calendars"
USERNAME = os.getenv("CALENDAR_USERNAME")
PASSWORD = os.getenv("CALENDAR_PASSWORD")

def get_calendar(target_name=None):
    """
    Connects to Infomaniak and returns a specific calendar by name.
    If target_name is None, returns the primary calendar.
    """
    try:
        client = caldav.DAVClient(url=URL, username=USERNAME, password=PASSWORD)
        principal = client.principal()
        calendars = principal.calendars()
        if not calendars:
            print("No calendars found.")
            return None

        if target_name:
            for cal in calendars:
                display_name = cal.get_display_name()
                if target_name.lower() in display_name.lower():
                    print(f"Using calendar: {display_name}")
                    return cal
            print(f"Warning: Calendar '{target_name}' not found. Using primary.")
        
        return calendars[0]
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def get_free_slots(start_from, duration_hours=1.5, days_to_scan=3, target_calendar="Garage"):
    """
    Scans the calendar for free time slots of a specific duration.
    """
    calendar = get_calendar(target_calendar)
    if not calendar:
        return []

    end_scan = start_from + timedelta(days=days_to_scan)
    # 1. Fetch all events in the search window
    events = calendar.search(start=start_from, end=end_scan, event=True)
    
    # 2. Map busy periods
    busy_times = []
    for event in events:
        comp = event.icalendar_instance.subcomponents[0]
        dt_start = comp.get('dtstart').dt
        dt_end = comp.get('dtend').dt
        # Convert date to datetime if necessary
        if not isinstance(dt_start, datetime):
            dt_start = datetime.combine(dt_start, datetime.min.time())
        if not isinstance(dt_end, datetime):
            dt_end = datetime.combine(dt_end, datetime.min.time())
        busy_times.append((dt_start.replace(tzinfo=None), dt_end.replace(tzinfo=None)))

    # 3. Find gaps
    free_slots = []
    current_time = start_from.replace(minute=0, second=0, microsecond=0)
    slot_delta = timedelta(hours=duration_hours)

    while current_time + slot_delta <= end_scan:
        potential_end = current_time + slot_delta
        
        # Check if current_time is within working hours (8h - 18h)
        if 8 <= current_time.hour < 18:
            # Check for overlap with any busy period
            overlap = any(current_time < b_end and potential_end > b_start for b_start, b_end in busy_times)
            
            if not overlap:
                free_slots.append((current_time, potential_end))
        
        # Step forward by 30 minutes for the next search possibility
        current_time += timedelta(minutes=30)
        
        # If we reach the end of the day, jump to the next morning at 8 AM
        if current_time.hour >= 18:
            current_time = (current_time + timedelta(days=1)).replace(hour=8, minute=0)

    return free_slots

def create_calendar_event(summary, start_time, duration_hours=1, description="", target_calendar="Garage"):
    # --- Configuration ---
    # Use an Application Password from Infomaniak Manager (Security > App Passwords)
    
    try:
        # 1. Get calendar
        my_calendar = get_calendar(target_calendar)
        if not my_calendar:
            print("No calendars found.")
            return
        
        end_time = start_time + timedelta(hours=duration_hours)

        # 2. Check for availability
        conflicts = my_calendar.date_search(start=start_time, end=end_time)
        
        if len(conflicts) > 0:
            print(f"Conflict detected: You already have {len(conflicts)} event(s) at this time.")
            return None

        # 3. Create the event
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

    now = datetime.now()
    print(f"Searching for 1.5h slots starting from {now.strftime('%d/%m %H:%M')}...")
    days_to_scan = 3
    available = get_free_slots(now, duration_hours=1.5,days_to_scan=days_to_scan)
    
    if available:
        print("\nNext available slots:")
        for start, end in available[:5]: # Show top 5
            print(f"{start.strftime('%d/%m at %H:%M')} to {end.strftime('%H:%M')}")
    else:
        print(f"No free slots found in the next {days_to_scan} days.")

    
    
    # Define your event details
    event_title = "Test"
    # Set time for tomorrow at 2 PM
    start_dt = datetime(2026, 4, 15, 15, 30, 0)
    create_calendar_event(event_title, start_dt, duration_hours=1.5)
   