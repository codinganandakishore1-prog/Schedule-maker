import pickle
from pathlib import Path
import streamlit_authenticator as sta

names = ["Nandakishore", "PVNandakishore"]
usernames = ["Nandakishore", "PVN"]
passwords = ["xxx", "xxx"]

# 1. Structure the credentials data into the format the library expects
credentials = {
    "usernames": {
        usernames[i]: {
            "name": names[i],
            "password": passwords[i]  # Provide plain text here initially
        }
        for i in range(len(usernames))
    }
}

# 2. Use the updated static method to hash the passwords in-place
sta.Hasher.hash_passwords(credentials)

# 3. Save the final dictionary using "wb" mode
file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("wb") as f:
    pickle.dump(credentials, f)

print("Passwords successfully hashed and saved!")


