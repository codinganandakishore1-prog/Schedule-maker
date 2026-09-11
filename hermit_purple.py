"""
AI PRODUCTIVITY SCHEDULER - HERMIT PURPLE 👾
==========================================
"""

import streamlit as st
import subprocess
import json
import os
from datetime import datetime, timedelta

# ==================== CONFIGURATION ====================
SCHEDULE_FILE = "schedule_data.json"
STATS_FILE = "user_stats.json"
ENERGY_FILE = "energy_data.json"

WORK_BLOCK_MINUTES = 90
BREAK_MINUTES = 20

DIFFICULTY_TIME = {
    1: 15, 2: 20, 3: 25, 4: 30, 5: 40,
    6: 50, 7: 60, 8: 75, 9: 90, 10: 105
}

# ==================== FILE OPERATIONS ====================
def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)

# ==================== COGNITIVE LEVEL ====================
def get_cognitive_level(time_str):
    try:
        hour = int(time_str.split(":")[0])
    except:
        hour = 9

    levels = {
        8: 5, 9: 9, 10: 10, 11: 8, 12: 5, 13: 4, 14: 4, 15: 5, 16: 6, 17: 5
    }
    return levels.get(hour, 4)

# ==================== TIME ESTIMATION ====================
def calculate_final_duration(difficulty, tags, preferred_duration, success_rate=0.7):
    base_time = DIFFICULTY_TIME.get(difficulty, 40)

    multiplier = 1.0
    if "creative" in tags: multiplier *= 1.2
    if "analytical" in tags: multiplier *= 1.1
    if "repetitive" in tags: multiplier *= 0.9

    if success_rate >= 0.9: multiplier *= 0.8
    elif success_rate >= 0.7: multiplier *= 0.9
    elif success_rate >= 0.5: multiplier *= 1.1
    else: multiplier *= 1.3

    estimated_time = int(base_time * multiplier)

    if preferred_duration and preferred_duration > 0:
        final_duration = int((preferred_duration * 0.75) + (estimated_time * 0.25))
    else:
        final_duration = estimated_time

    return final_duration

# ==================== NOTIFICATIONS ====================
def send_mac_notification(title, message, delay_seconds=0):
    try:
        if delay_seconds > 0:
            subprocess.run(["sleep", str(delay_seconds)], capture_output=True)
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except:
        pass

# ==================== SUCCESS RATE ====================
def get_success_rate():
    stats = load_json(STATS_FILE)
    completed = stats.get("completed_tasks", 0)
    total = stats.get("total_tasks", 0)
    return completed / total if total > 0 else 0.7

def update_success_stats(task_completed):
    stats = load_json(STATS_FILE)
    stats["total_tasks"] = stats.get("total_tasks", 0) + 1
    if task_completed:
        stats["completed_tasks"] = stats.get("completed_tasks", 0) + 1
    save_json(STATS_FILE, stats)

# ==================== SCHEDULE GENERATION ====================
def generate_schedule(tasks, start_time_str, end_time_str):
    try:
        work_start = datetime.strptime(start_time_str, "%H:%M")
        work_end = datetime.strptime(end_time_str, "%H:%M")
    except:
        work_start = datetime.strptime("08:00", "%H:%M")
        work_end = datetime.strptime("17:30", "%H:%M")

    remaining_tasks = tasks.copy()
    tasks_with_time = [t for t in remaining_tasks if t.get("preferred_time")]
    tasks_without_time = [t for t in remaining_tasks if not t.get("preferred_time")]
    tasks_with_time.sort(key=lambda x: x.get("preferred_time", "23:59"))

    schedule = []
    break_counter = 1
    current_time = work_start

    # Schedule tasks with preferred time
    for task in tasks_with_time:
        try:
            pref_time = datetime.strptime(task["preferred_time"], "%H:%M")
            current_time = max(pref_time, work_start)
        except:
            current_time = work_start

        duration = task.get("final_duration", task.get("estimated_time", 30))
        task_end = current_time + timedelta(minutes=duration)

        if current_time < work_end and task_end <= work_end:
            schedule.append({
                "start": current_time.strftime("%H:%M"),
                "end": task_end.strftime("%H:%M"),
                "task": task.get("task"),
                "difficulty": task.get("difficulty", 5),
                "tags": task.get("tags", []),
                "duration": duration,
                "is_break": False,
                "completed": False
            })
            current_time = task_end

    # Schedule remaining tasks with 5-min gaps and breaks
    current_time = work_start

    for task in tasks_without_time:
        duration = task.get("final_duration", task.get("estimated_time", 30))
        task_end = current_time + timedelta(minutes=duration)

        if current_time >= work_end or task_end > work_end:
            break

        schedule.append({
            "start": current_time.strftime("%H:%M"),
            "end": task_end.strftime("%H:%M"),
            "task": task.get("task"),
            "difficulty": task.get("difficulty", 5),
            "tags": task.get("tags", []),
            "duration": duration,
            "is_break": False,
            "completed": False
        })

        current_time = task_end

        if current_time < work_end:
            current_time += timedelta(minutes=5)

        work_done = sum(item.get("duration", 0) for item in schedule if not item.get("is_break", False))

        if work_done > 0 and work_done % WORK_BLOCK_MINUTES == 0:
            if current_time + timedelta(minutes=BREAK_MINUTES) <= work_end:
                break_start = current_time
                break_end = current_time + timedelta(minutes=BREAK_MINUTES)

                schedule.append({
                    "start": break_start.strftime("%H:%M"),
                    "end": break_end.strftime("%H:%M"),
                    "task": f"☕ Break #{break_counter}",
                    "difficulty": 0,
                    "tags": ["break"],
                    "duration": BREAK_MINUTES,
                    "is_break": True,
                    "completed": True
                })

                current_time = break_end
                break_counter += 1

                if current_time < work_end:
                    current_time += timedelta(minutes=5)

    schedule.sort(key=lambda x: x.get("start", "00:00"))

    # Create unique IDs
    for i, item in enumerate(schedule):
        task_name_clean = "".join(c for c in item.get("task", "task") if c.isalnum())[:10]
        start_time_clean = item.get("start", "0000").replace(":", "")
        item["id"] = f"{task_name_clean}_{start_time_clean}_{i}"

    return schedule

# ==================== MAIN APP ====================
def main():
    # Initialize session state (ONLY ONCE)
    if "tasks" not in st.session_state:
        st.session_state.tasks = []
    if "generated_schedule" not in st.session_state:
        st.session_state.generated_schedule = []
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    if "timer_active" not in st.session_state:
        st.session_state.timer_active = False
    if "timer_remaining" not in st.session_state:
        st.session_state.timer_remaining = 0

    # Load today's schedule on startup
    today_str = datetime.now().strftime("%Y-%m-%d")
    existing_schedules = load_json(SCHEDULE_FILE)
    if today_str in existing_schedules:
        st.session_state.generated_schedule = existing_schedules[today_str]

    # Page config
    st.set_page_config(
        page_title="AI Productivity Scheduler - HERMIT PURPLE 👾",
        page_icon="📅",
        layout="wide"
    )

    # Dark mode CSS
    if st.session_state.dark_mode:
        st.markdown("""
        <style>
        .stApp { background-color: #1e1e1e; color: #e0e0e0; }
        .stMarkdown, .stText, .stMarkdown p { color: #e0e0e0 !important; }
        div[data-testid="stExpander"] { background-color: #2d2d2d !important; border: 1px solid #444; }
        .stButton > button { background-color: #4a4a4a !important; color: #e0e0e0 !important; }
        div[data-testid="stMetricValue"] { color: #e0e0e0 !important; }
        </style>
        """, unsafe_allow_html=True)

    # ==================== SIDEBAR ====================
    st.sidebar.title("⚙️ Settings")

    st.sidebar.subheader("🕐 Work Hours")
    start_time_input = st.sidebar.time_input("Start Time", datetime.strptime("08:00", "%H:%M"))
    end_time_input = st.sidebar.time_input("End Time", datetime.strptime("17:30", "%H:%M"))

    st.sidebar.write("---")

    # ONE dark mode toggle with unique key
    st.sidebar.subheader("🌙 Appearance")
    st.session_state.dark_mode = st.sidebar.toggle(
        "Dark Mode",
        value=st.session_state.dark_mode,
        key="dark_mode_toggle_main"
    )

    st.sidebar.write("---")

    # Energy insights in sidebar
    st.sidebar.subheader("⚡ Energy Insights")
    energy_data = load_json(ENERGY_FILE)
    today = datetime.now().strftime("%Y-%m-%d")

    if today in energy_data and energy_data[today]:
        avg_energy = sum(e["level"] for e in energy_data[today]) / len(energy_data[today])
        st.sidebar.write(f"**Average Today:** {avg_energy:.1f}/10")

        if avg_energy >= 7:
            st.sidebar.success("🚀 Great energy!")
        elif avg_energy >= 4:
            st.sidebar.warning("⚡ Moderate energy")
        else:
            st.sidebar.error("🔋 Low energy")
    else:
        st.sidebar.info("Log energy to get insights")

    st.sidebar.write("---")

    # User statistics
    st.sidebar.subheader("📊 Your Statistics")
    current_success_rate = get_success_rate()
    st.sidebar.progress(current_success_rate)
    st.sidebar.write(f"**Success Rate: {current_success_rate*100:.0f}%**")
    st.sidebar.caption("Learns from your completed tasks")

    st.sidebar.write("---")

    # Data management
    st.sidebar.subheader("🗑️ Data Management")
    if st.sidebar.button("Clear All Schedule Data"):
        save_json(SCHEDULE_FILE, {})
        save_json(STATS_FILE, {"completed_tasks": 0, "total_tasks": 0})
        st.session_state.tasks = []
        st.session_state.generated_schedule = []
        st.sidebar.success("All data cleared!")
        st.rerun()

    if st.sidebar.button("Clear Current Tasks"):
        st.session_state.tasks = []
        st.rerun()

    # ==================== MAIN TABS ====================
    tab_create, tab_timer, tab_calendar, tab_stats = st.tabs([
        "📝 Create Schedule",
        "🍅 Pomodoro Timer",
        "📅 Calendar",
        "📈 Statistics"
    ])

    # ==================== TAB 1: CREATE SCHEDULE ====================
    with tab_create:
        st.title("🚀 AI Productivity Scheduler - HERMIT PURPLE 👾")
        st.markdown("""
        ### Productivity Formula
        - **90 min work** → **20 min break** (ultradian rhythm)
        - **High difficulty (8-10)** → Peak morning (8-11 AM)
        - **Medium difficulty (5-7)** → Mid-day
        - **Low difficulty (1-4)** → Afternoon
        """)

        st.write("---")
        st.subheader("➕ Add Your Tasks")

        col_task, col_diff = st.columns([3, 1])

        with col_task:
            task_name_input = st.text_input("Task Name", placeholder="e.g., Write project proposal...", key="task_input")

        with col_diff:
            difficulty_slider = st.slider("Difficulty", 1, 10, 5, key="diff_slider")

        col_tags, col_pref_time = st.columns([2, 1])

        with col_tags:
            available_tags = ["creative", "analytical", "repetitive", "learning", "meeting", "editing", "exercise", "coding", "self"]
            selected_tags = st.multiselect("Tags", available_tags, key="tags_select")

        with col_pref_time:
            preferred_time_input = st.text_input("Preferred Time", placeholder="e.g., 09:00", key="pref_time")

        col_pref_duration, col_addbtn = st.columns([1, 3])

        with col_pref_duration:
            preferred_duration_input = st.number_input("Preferred Duration (min)", 0, 480, 0, 5, key="pref_duration")

        # Calculate times
        success_rate = get_success_rate()
        estimated_time = int(DIFFICULTY_TIME.get(difficulty_slider, 40) * (
            1.2 if "creative" in selected_tags else 1.0) * (
            1.1 if "analytical" in selected_tags else 1.0) * (
            0.9 if "repetitive" in selected_tags else 1.0) * (
            0.8 if success_rate >= 0.9 else 0.9 if success_rate >= 0.7 else 1.1 if success_rate >= 0.5 else 1.3))

        final_duration = calculate_final_duration(difficulty_slider, selected_tags, preferred_duration_input, success_rate)

        st.caption(f"📏 Estimated: {estimated_time} min | Final: {final_duration} min")

        with col_addbtn:
            if st.button("➕ Add Task", type="primary", use_container_width=True) and task_name_input:
                new_task = {
                    "task": task_name_input,
                    "difficulty": difficulty_slider,
                    "tags": selected_tags,
                    "preferred_time": preferred_time_input if preferred_time_input else None,
                    "preferred_duration": preferred_duration_input if preferred_duration_input > 0 else None,
                    "estimated_time": estimated_time,
                    "final_duration": final_duration
                }
                st.session_state.tasks.append(new_task)
                st.success(f"✅ Added: {task_name_input} ({final_duration} min)")

        # === DISPLAY SCHEDULE ===
        if st.session_state.generated_schedule:
            st.write("---")
            st.subheader("📅 Today's Schedule")

            total_work = sum(i.get("duration", 0) for i in st.session_state.generated_schedule if not i.get("is_break", False))
            total_break = sum(i.get("duration", 0) for i in st.session_state.generated_schedule if i.get("is_break", False))
            total_day = total_work + total_break

            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("Work Time", f"{total_work} min")
            col_s2.metric("Break Time", f"{total_break} min")
            col_s3.metric("Day Time", f"{total_day} min")

            st.write("---")

            completed_time = 0
            counter = 0

            for item in st.session_state.generated_schedule:
                if item.get("is_break", False):
                    st.info(f"☕ **{item.get('start')} - {item.get('end')}** | {item.get('task')} | {item.get('duration')} min")
                else:
                    diff = item.get("difficulty", 5)
                    color = "🟢" if diff <= 4 else "🟡" if diff <= 7 else "🔴"

                    c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 1, 1])

                    with c1:
                        st.write(f"**{item.get('start')}**")
                    with c2:
                        st.write(f"{color} {item.get('task')}")
                    with c3:
                        st.write(f"{item.get('duration')}min")
                    with c4:
                        st.write(f"Diff: {diff}")
                    with c5:
                        # UNIQUE KEY using counter + task name
                        unique_key = f"cb_{counter}_{item.get('task', '').replace(' ', '_')}"
                        task_completed = st.checkbox("Done", key=unique_key, value=item.get("completed", False))
                        item["completed"] = task_completed

                        if task_completed:
                            completed_time += item.get("duration", 0)
                            update_success_stats(True)
                        else:
                            update_success_stats(False)

                    counter += 1

            st.write("---")

            if total_work > 0:
                progress = completed_time / total_work
                st.progress(progress)
                st.write(f"**Progress:** {completed_time}/{total_work} min ({progress * 100:.0f}%)")

                if progress >= 1.0:
                    st.balloons()
                    st.success("🎉 All tasks completed!")

        st.write("---")

        # === ENERGY TRACKER ===
        st.subheader("⚡ Energy Tracker")

        col_e1, col_e2 = st.columns([1, 1])

        with col_e1:
            energy_level = st.slider(f"Energy at {datetime.now().strftime('%H:%M')}", 1, 10, 5,
                                        key="energy_slider")

            if st.button("💾 Save Energy Level"):
                energy_data = load_json(ENERGY_FILE)
                today = datetime.now().strftime("%Y-%m-%d")

                if today not in energy_data:
                    energy_data[today] = []

                energy_data[today].append({
                    "time": datetime.now().strftime("%H:%M"),
                    "level": energy_level
                })

                save_json(ENERGY_FILE, energy_data)
                st.success("Energy level saved!")

        with col_e2:
            energy_data = load_json(ENERGY_FILE)
            today = datetime.now().strftime("%Y-%m-%d")

            if today in energy_data and energy_data[today]:
                for entry in energy_data[today]:
                    emoji = "🟢" if entry["level"] >= 7 else "🟡" if entry["level"] >= 4 else "🔴"
                    st.write(f"{emoji} **{entry['time']}:** Energy {entry['level']}/10")
            else:
                st.info("No energy data logged yet")

        # === GENERATE SCHEDULE BUTTON ===
        st.write("---")

        if st.button("🚀 Generate Optimal Schedule", type="primary", use_container_width=True):
            if st.session_state.tasks:
                with st.spinner("Creating schedule..."):
                    new_schedule = generate_schedule(
                        st.session_state.tasks.copy(),
                        start_time_input.strftime("%H:%M"),
                        end_time_input.strftime("%H:%M")
                    )

                    # Save schedule
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    existing_schedules = load_json(SCHEDULE_FILE)
                    existing_schedules[today_str] = new_schedule
                    save_json(SCHEDULE_FILE, existing_schedules)

                    st.session_state.generated_schedule = new_schedule
                    st.success(f"✅ Schedule created with {len(new_schedule)} tasks!")
            else:
                st.warning("⚠️ Add at least one task first!")

        # ==================== TAB 2: POMODORO TIMER ====================
    with tab_timer:
        st.title("🍅 Pomodoro Timer")
        st.markdown("### 90 min work | 20 min break cycles")

        col_t1, col_t2 = st.columns([1, 1])

        with col_t1:
            task_options = [i["task"] for i in st.session_state.generated_schedule if
                            not i.get("is_break", False)]
            if task_options:
                current_task = st.selectbox("Select Task", options=task_options, index=0)
            else:
                current_task = st.text_input("Task Name", value="No tasks scheduled")

            work_duration = st.number_input("Work Duration (min)", 1, 120, 90)
            break_duration = st.number_input("Break Duration (min)", 1, 60, 20)

        with col_t2:
            # Timer display
            if st.session_state.timer_remaining > 0:
                minutes = st.session_state.timer_remaining // 60
                seconds = st.session_state.timer_remaining % 60
                st.markdown(
                    f"<h1 style='text-align: center; font-size: 72px;'>{minutes:02d}:{seconds:02d}</h1>",
                    unsafe_allow_html=True)
            else:
                st.write("⏰ Timer ready")

            # Timer controls
            col_b1, col_b2, col_b3 = st.columns(3)

            with col_b1:
                if st.button("▶️ Start", type="primary", use_container_width=True):
                    st.session_state.timer_active = True
                    st.session_state.timer_remaining = work_duration * 60

            with col_b2:
                if st.button("⏸️ Pause"):
                    st.session_state.timer_active = False

            with col_b3:
                if st.button("🔄 Reset"):
                    st.session_state.timer_active = False
                    st.session_state.timer_remaining = 0

            # Timer countdown
            if st.session_state.timer_active and st.session_state.timer_remaining > 0:
                import time
                time.sleep(1)
                st.session_state.timer_remaining -= 1
                st.rerun()

            # Notification when done
            if st.session_state.timer_remaining == 0 and st.session_state.timer_active:
                send_mac_notification("🍅 Timer Complete!", f"Time for a {break_duration} min break!", 0)
                st.session_state.timer_active = False

        # ==================== TAB 3: CALENDAR ====================
    with tab_calendar:
        st.title("📅 Calendar View")

        all_schedules = load_json(SCHEDULE_FILE)

        if all_schedules:
            sorted_dates = sorted(all_schedules.keys(), reverse=True)

            for date in sorted_dates:
                tasks_for_date = all_schedules[date]

                with st.expander(f"📅 {date}"):
                    st.write(f"**{len(tasks_for_date)} tasks**")

                    for task in tasks_for_date:
                        emoji = "✅" if task.get("completed") else "⬜"
                        st.write(
                            f"{emoji} **{task.get('start')}** - {task.get('task')} ({task.get('duration')} min)")

                    col_d1, col_d2 = st.columns([1, 4])
                    with col_d1:
                        if st.button(f"🗑️ Delete {date}", key=f"delete_{date}"):
                            del all_schedules[date]
                            save_json(SCHEDULE_FILE, all_schedules)
                            st.success(f"Deleted {date}")
                            st.rerun()
        else:
            st.info("No schedules yet!")

        # ==================== TAB 4: STATISTICS ====================
    with tab_stats:
        st.title("📈 Statistics")

        stats = load_json(STATS_FILE)
        all_schedules = load_json(SCHEDULE_FILE)

        total_completed = stats.get("completed_tasks", 0)
        total_tasks = stats.get("total_tasks", 0)
        success_rate = total_completed / total_tasks if total_tasks > 0 else 0.7

        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Success Rate", f"{success_rate * 100:.0f}%")
        col_s2.metric("Tasks Completed", total_completed)
        col_s3.metric("Total Attempted", total_tasks)

        st.progress(success_rate)

        st.write("---")
        st.subheader("📊 Weekly Progress")

        # Last 7 days
        days_data = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            day_name = (datetime.now() - timedelta(days=i)).strftime("%a")

            if date in all_schedules:
                day_schedule = all_schedules[date]
                completed = sum(1 for t in day_schedule if t.get("completed", False))
                total = len(day_schedule)
                days_data.append({"day": day_name, "completed": completed, "total": total})
            else:
                days_data.append({"day": day_name, "completed": 0, "total": 0})

        for day in days_data:
            if day["total"] > 0:
                pct = day["completed"] / day["total"]
                st.write(f"**{day['day']}:** {day['completed']}/{day['total']} tasks")
                st.progress(pct)
            else:
                st.write(f"**{day['day']}:** No tasks")

        st.write("---")
        st.subheader("💡 Productivity Tips")
        st.markdown("""
                        1. **Work in 90-minute blocks** - Brain naturally cycles every 90 min
                        2. **Schedule hard tasks for peak hours** - Morning (8-11 AM)
                        3. **Afternoon for easy tasks** - After lunch energy dips
                        4. **The scheduler learns from you** - More use = better estimates!
                        """)

        if st.button("🔄 Reset Statistics"):
            save_json(STATS_FILE, {"completed_tasks": 0, "total_tasks": 0})
            st.success("Statistics reset!")
            st.rerun()

# ==================== RUN ====================
if __name__ == "__main__":
    main()