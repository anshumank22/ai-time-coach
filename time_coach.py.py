import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
tasks = []

# --- Google Calendar Fetch ---
def get_google_calendar_events():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    now = datetime.datetime.utcnow().isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=10, singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])
    return events

# --- Task Manager ---
def add_task(title, priority, deadline):
    task = {'title': title, 'priority': priority, 'deadline': deadline}
    tasks.append(task)

def get_prioritized_tasks():
    return sorted(tasks, key=lambda x: (x['priority'], x['deadline']))

# --- Display Schedule ---
def display_schedule():
    print("\n📅 Your Google Calendar Events:")
    for event in get_google_calendar_events():
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(f" - {event['summary']} at {start}")

    print("\n📝 Your Prioritized Tasks:")
    for task in get_prioritized_tasks():
        print(f" - {task['title']} | Priority: {task['priority']} | Deadline: {task['deadline']}")

# --- Demo Use ---
if __name__ == "__main__":
    # Add some example tasks
    add_task("Finish Assignment", 1, "2025-04-20 10:00")
    add_task("Buy Groceries", 3, "2025-04-20 19:00")
    add_task("Call Client", 2, "2025-04-20 14:00")

    display_schedule()
