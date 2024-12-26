import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json

# Retrieve Firebase credentials and database URL from secrets
firebase_credentials = st.secrets["firebase"]["credentials"]
database_url = st.secrets["firebase"]["database_url"]

# Parse the JSON string into a dictionary
cred_dict = json.loads(firebase_credentials)

# Initialize Firebase with the credentials and database URL
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': database_url
})

# Fetch data from Firebase to test connection
ref = db.reference('test')  # Reference to a test node
data = ref.get()

# Display data in Streamlit
st.write(data)
