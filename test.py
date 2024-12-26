import firebase_admin
from firebase_admin import credentials, db

# Retrieve credentials and database URL from secrets
firebase_credentials = st.secrets["firebase"]["credentials"]
database_url = st.secrets["firebase"]["database_url"]

# Initialize Firebase with the credentials and database URL
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred, {
    'databaseURL': database_url
})

# Fetch data from Firebase
ref = db.reference('test')  # Reference to a test node
data = ref.get()

st.write(data)
