import os
import json
import streamlit as st
import datetime
from datetime import timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# --- Constants ---
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
TASKS_FILE = 'tasks.json'
calendar_events = []

# --- Initialize Session State ---
if "tasks" not in st.session_state:
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r') as f:
            st.session_state.tasks = json.load(f)
    else:
        st.session_state.tasks = []

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
def save_tasks():
    with open(TASKS_FILE, 'w') as f:
        json.dump(st.session_state.tasks, f, default=str)

def add_task(title, priority, duration_minutes):
    task = {
        "title": title,
        "priority": priority,
        "duration": duration_minutes,
        "scheduled": False,
        "start_time": None,
        "end_time": None
    }
    st.session_state.tasks.append(task)
    save_tasks()

def delete_task(index):
    del st.session_state.tasks[index]
    save_tasks()

def edit_task(index, new_title, new_priority, new_duration):
    st.session_state.tasks[index]["title"] = new_title
    st.session_state.tasks[index]["priority"] = new_priority
    st.session_state.tasks[index]["duration"] = new_duration
    save_tasks()

def get_prioritized_tasks():
    return sorted(st.session_state.tasks, key=lambda x: x["priority"])

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
    day_start = datetime.datetime.combine(datetime.date.today(), datetime.time(8, 0))
    day_end = datetime.datetime.combine(datetime.date.today(), datetime.time(20, 0))
    free_slots = find_free_slots(calendar_events, day_start, day_end)

    for task in get_prioritized_tasks():
        if task["scheduled"]:
            continue
        task_duration = timedelta(minutes=task["duration"])
        for start, end in free_slots:
            slot_duration = end - start
            if task_duration <= slot_duration:
                task["scheduled"] = True
                task["start_time"] = start.isoformat()
                task["end_time"] = (start + task_duration).isoformat()
                # Adjust the slot
                new_start = start + task_duration
                free_slots.remove((start, end))
                if new_start < end:
                    free_slots.append((new_start, end))
                break
    save_tasks()

# --- Streamlit UI ---
st.set_page_config(page_title="🧠 AI Time Coach", layout="centered")
st.title("🧠 AI Time Management Coach")

# Add a Task
st.subheader("➕ Add New Task")
title = st.text_input("Task Name")
priority = st.selectbox("Priority", [1, 2, 3], format_func=lambda x: {1: "High", 2: "Medium", 3: "Low"}[x])
duration = st.slider("Task Duration (minutes)", 15, 180, 30)

if st.button("Add Task"):
    if title.strip() == "":
        st.warning("⚠️ Task name can't be empty!")
    else:
        add_task(title, priority, duration)
        st.success("✅ Task added!")

# Fetch Calendar
st.subheader("📅 Google Calendar Events")
if st.button("Fetch Calendar"):
    calendar_events.clear()
    try:
        calendar_events.extend(get_google_calendar_events())
        if not calendar_events:
            st.info("No upcoming events found.")
        else:
            for event in calendar_events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                st.write(f"📌 {event['summary']} at {start}")
    except Exception as e:
        st.error(f"❌ Failed to fetch calendar: {e}")

# Smart Scheduler
if st.button("🧠 Smart Schedule Tasks"):
    if not calendar_events:
        st.warning("📅 Please fetch calendar first!")
    else:
        schedule_tasks()
        st.success("✅ Tasks scheduled into free time!")

# Show Tasks
st.subheader("📝 Your Tasks")
for idx, task in enumerate(get_prioritized_tasks()):
    col1, col2, col3 = st.columns([6, 2, 2])
    with col1:
        if task.get("scheduled") and task.get("start_time"):
            start_time = datetime.datetime.fromisoformat(task['start_time']).strftime('%H:%M')
            end_time = datetime.datetime.fromisoformat(task['end_time']).strftime('%H:%M')
            st.write(f"✅ **{task['title']}** | {start_time} - {end_time} | Priority: {task['priority']}")
        else:
            st.write(f"🕒 **{task['title']}** | Not scheduled | Priority: {task['priority']} | Duration: {task['duration']} min")
    with col2:
        if st.button("✏️ Edit", key=f"edit_{idx}"):
            new_title = st.text_input("New Title", value=task['title'], key=f"nt_{idx}")
            new_priority = st.selectbox("New Priority", [1, 2, 3], index=task['priority']-1, key=f"np_{idx}")
            new_duration = st.slider("New Duration (min)", 15, 180, task['duration'], key=f"nd_{idx}")
            if st.button("Save Changes", key=f"save_{idx}"):
                edit_task(idx, new_title, new_priority, new_duration)
                st.experimental_rerun()
    with col3:
        if st.button("🗑️ Delete", key=f"del_{idx}"):
            delete_task(idx)
            st.success("Task deleted!")
            st.experimental_rerun()

# Optional: Clear All Tasks
if st.button("🗑️ Clear All Tasks"):
    st.session_state.tasks.clear()
    save_tasks()
    st.success("All tasks cleared!")

# Show Timeline
st.subheader("🕓 Today's Timeline")
for task in sorted(st.session_state.tasks, key=lambda x: (x['start_time'] if x['start_time'] else 'Z')):
    if task.get("scheduled") and task.get("start_time"):
        start_time = datetime.datetime.fromisoformat(task['start_time']).strftime('%I:%M %p')
        end_time = datetime.datetime.fromisoformat(task['end_time']).strftime('%I:%M %p')
        st.write(f"🗓️ **{start_time} - {end_time}:** {task['title']}")
