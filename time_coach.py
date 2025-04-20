import os
import streamlit as st
import datetime
from datetime import timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
tasks = []
calendar_events = []

# --- Google Calendar API Integration ---
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
    end_of_day = (datetime.datetime.utcnow() + timedelta(hours=24)).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary', timeMin=now, timeMax=end_of_day,
        maxResults=20, singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])
    return sorted(events, key=lambda e: e['start'].get('dateTime', e['start'].get('date')))

# --- Task Management ---
def add_task(title, priority, duration_minutes):
    task = {"title": title, "priority": priority, "duration": timedelta(minutes=duration_minutes), "scheduled": False}
    tasks.append(task)

def get_prioritized_tasks():
    return sorted(tasks, key=lambda x: x["priority"])

def find_free_slots(events, day_start, day_end):
    busy_slots = []
    for event in events:
        start_str = event['start'].get('dateTime')
        end_str = event['end'].get('dateTime')
        if start_str and end_str:
            start = datetime.datetime.fromisoformat(start_str[:-1])
            end = datetime.datetime.fromisoformat(end_str[:-1])
            busy_slots.append((start, end))

    busy_slots.sort()
    free_slots = []
    current = day_start

    for start, end in busy_slots:
        if current < start:
            free_slots.append((current, start))
        current = max(current, end)

    if current < day_end:
        free_slots.append((current, day_end))

    return free_slots

def schedule_tasks():
    global tasks
    day_start = datetime.datetime.combine(datetime.date.today(), datetime.time(8, 0))
    day_end = datetime.datetime.combine(datetime.date.today(), datetime.time(20, 0))
    free_slots = find_free_slots(calendar_events, day_start, day_end)

    for task in get_prioritized_tasks():
        if task["scheduled"]:
            continue
        for start, end in free_slots:
            slot_duration = end - start
            if task["duration"] <= slot_duration:
                task["scheduled"] = True
                task["start_time"] = start
                task["end_time"] = start + task["duration"]
                # Update slot
                new_start = task["end_time"]
                free_slots.append((new_start, end))
                free_slots.remove((start, end))
                break

# --- Streamlit UI ---
st.set_page_config(page_title="🧠 AI Time Coach", layout="centered")
st.title("🧠 AI Time Management Coach")

# Add a Task
st.subheader("➕ Add Task")
title = st.text_input("Task Name")
priority = st.selectbox("Priority", [1, 2, 3], format_func=lambda x: {1: "High", 2: "Medium", 3: "Low"}[x])
duration = st.slider("Task Duration (minutes)", 15, 180, 30)

if st.button("Add Task"):
    add_task(title, priority, duration)
    st.success("✅ Task added!")

# Fetch Calendar
st.subheader("📅 Google Calendar Events")
if st.button("Fetch Calendar"):
    calendar_events.clear()
    calendar_events.extend(get_google_calendar_events())
    if not calendar_events:
        st.info("No upcoming events found.")
    else:
        for event in calendar_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            st.write(f"📌 {event['summary']} at {start}")

# Smart Scheduler
if st.button("🧠 Smart Schedule Tasks"):
    if not calendar_events:
        st.warning("📅 Please fetch calendar first!")
    else:
        schedule_tasks()
        st.success("Tasks scheduled into free time!")

# Show Tasks
st.subheader("📝 Your Tasks")
for task in get_prioritized_tasks():
    if task.get("scheduled"):
        st.write(f"✅ {task['title']} | {task['start_time'].strftime('%H:%M')} to {task['end_time'].strftime('%H:%M')} | Priority: {task['priority']}")
    else:
        st.write(f"🕒 {task['title']} | Not scheduled | Priority: {task['priority']} | Duration: {task['duration']}")

