import streamlit as st
import streamlit_authenticator as stauth
import pickle
from pathlib import Path
import json
import datetime

st.set_page_config(page_title="Schedule App")

# --- Load Hashed Passwords ---
file_path = Path(__file__).parent / "hashed_pw.pkl"

try:
    with open(file_path, "rb") as f:
        hashed_pw = pickle.load(f)
except FileNotFoundError:
    st.error("Password file not found!")
    st.stop()

# --- Debug: Check what's in hashed_pw ---
st.write("DEBUG - Type of hashed_pw:", type(hashed_pw))
st.write("DEBUG - Content:", hashed_pw)

# --- Build Credentials ---
# Check if hashed_pw is a dict or list
if isinstance(hashed_pw, dict):
    # Example: {'Nandakishore': 'hashed_pw1', 'PVN': 'hashed_pw2'}
    credentials = {}
    for username, password in hashed_pw.items():
        credentials[username] = {
            "name": username,
            "password": password
        }
elif isinstance(hashed_pw, (list, tuple)):
    # Example: ['hashed_pw1', 'hashed_pw2']
    names = ["Nandakishore", "PVNandakishore"]
    usernames = ["Nandakishore", "PVN"]
    credentials = {}
    for i, pw in enumerate(hashed_pw):
        if i < len(usernames):
            credentials[usernames[i]] = {
                "name": names[i] if i < len(names) else usernames[i],
                "password": pw
            }
else:
    st.error("Unknown format for hashed_pw file!")
    st.stop()

st.write("DEBUG - Credentials built:", credentials)

# --- Initialize Authenticator ---
authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name="schedule_app",
    cookie_key="abcdef",
    cookie_expiry_days=30
)

# --- Safe Login ---
login_result = authenticator.login("main")

# Check if login_result is None
if login_result is None:
    st.error("Login failed - authenticator.login() returned None")
    st.write("This usually means the credentials format is wrong.")
    st.stop()

# Unpack the result
try:
    name, authentication_status, username = login_result
except TypeError as e:
    st.error(f"Error unpacking login result: {e}")
    st.write("Login result:", login_result)
    st.stop()

# --- Status Messages ---
if authentication_status == False:
    st.error("Username/password is incorrect")
    st.stop()
elif authentication_status == None:
    st.warning("Please enter your username and password")
    st.stop()

# --- Main App ---
if authentication_status == True:
    st.title(f"Schedule App - Welcome {name}")

    cognition = st.slider("How does your cognition feel today? : ", 0, 10)
    tasks = st.text_input("Enter your tasks : ")
    difficulty = st.slider("Enter your difficulty : ", 1, 5)

    if st.button("Submit"):
        try:
            with open("all_tasks.json", "r") as f:
                all_tasks = json.load(f)
        except FileNotFoundError:
            all_tasks = {}

        all_tasks[tasks] = {
            "difficulty": difficulty,
            "cognition": cognition,
            "timestamp": datetime.datetime.now().isoformat()
        }

        with open("all_tasks.json", "w") as f:
            json.dump(all_tasks, f, indent=4)

        st.success("Tasks saved!")

    if st.button("Show all tasks"):
        try:
            with open("all_tasks.json", "r") as f:
                data = json.load(f)
            st.json(data)
        except FileNotFoundError:
            st.info("No tasks saved yet.")

