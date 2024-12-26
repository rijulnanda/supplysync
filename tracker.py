import streamlit as st
import pandas as pd
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import time

# Set up the page config with theme and title
st.set_page_config(
    page_title="Inventory Tracker",
    page_icon="📦",
    layout="wide",  # Makes the content more expansive
)

# Initialize session state for the DataFrame, original values, waitlist, and count
if 'df' not in st.session_state:
    st.session_state.df = None
if 'waitlist' not in st.session_state:
    st.session_state.waitlist = pd.DataFrame(columns=["Name"])
if 'total_added' not in st.session_state:
    st.session_state.total_added = 0


import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate('mhsupplysync-firebase-adminsdk-k4jjf-d0bf272b67.json')  
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://mhsupplysync-default-rtdb.firebaseio.com/'  # Replace with your actual Firebase Realtime Database URL
    })

def get_waitlist():
    ref = db.reference('waitlist')  # "waitlist" is the path in Firebase
    return pd.DataFrame(ref.get()) if ref.get() else pd.DataFrame(columns=["Name"])  # Return waitlist data from Firebase

def set_waitlist(waitlist_df):
    ref = db.reference('waitlist')
    ref.set(waitlist_df.to_dict(orient='records'))  # Save the waitlist to Firebase

# Function to send email using SMTP
def send_email_smtp(recipient_email, subject, body, attachment_bytes, filename):
    sender_email = "supplysync03@gmail.com"  # Your Gmail email address
    password = "mqyj htly sdxx xxgn"  # Your Gmail app-specific password (use if 2FA enabled)

    # Set up the MIME
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Attach the email body text
    msg.attach(MIMEText(body, 'plain'))  # Correct way to attach a string as the email body

    # Attach the Excel file
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment_bytes.getvalue())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={filename}')
    msg.attach(part)

    try:
        # Set up the SMTP server and send the email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(sender_email, password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError as auth_error:
        print(f"Authentication Error: {auth_error}")
        return False
    except smtplib.SMTPException as smtp_error:
        print(f"SMTP Error: {smtp_error}")
        return False
    except Exception as e:
        print(f"General Error: {e}")
        return False


# Helper functions to get and set data to Firebase
def get_inventory():
    ref = db.reference('inventory')  # "inventory" is the path in Firebase
    inventory_data = ref.get()
    if inventory_data:
        return pd.DataFrame(inventory_data)
    else:
        return pd.DataFrame(columns=["Item", "Dose", "Number", "Medium", "Location"])  # Empty dataframe if no data exists

def set_inventory(df):
    ref = db.reference('inventory')
    ref.set(df.to_dict(orient='records'))  # Save the dataframe to Firebase

# Inventory tracker function with Firebase integration
def inventory_tracker():
    st.title("Inventory Tracker")
    
    # Fetch inventory data from Firebase
    df = get_inventory()
    
    if df.empty:
        st.info("No inventory data found. Please upload data first.")
        return
    
    # Reorder the columns to the desired order: Item, Number, Boxes, Dose, Location, Medium
    column_order = ["Item", "Number", "Boxes", "Dose", "Location", "Medium"]
    df = df[column_order]  # This reorders the columns to the desired order

    # Show the inventory preview
    st.subheader("Data Preview")
    st.write(df.head())

    st.subheader('Filter Data')
    columns = df.columns.tolist()
    selected_column = st.selectbox("Select column to filter by", columns)
    unique_values = df[selected_column].unique()
    selected_value = st.selectbox("Select value", unique_values)

    filtered_df = df[df[selected_column] == selected_value]
    if not filtered_df.empty:
        st.subheader("Filtered Inventory Items")
        
        for index, row in filtered_df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 2, 1])  # Adjust column sizes
            
            with col1:
                st.write(row['Item'])
            
            with col2:
                st.write(row['Dose'])
            
            with col3:
                st.write(row['Number'])  # Display current count
            
            with col4:
                st.write(row['Medium'])
            
            with col5:
                st.write(row['Location'])

            # Dropdown to select amount to change
            amount_to_change = st.number_input(f"Amount to change for {row['Item']}", min_value=1, max_value=100, value=1)

            # Buttons to decrease or increase the count
            col_decrease, col_increase = st.columns(2)  # Create 2 columns for the buttons

            with col_decrease:
                if st.button(f"Decrease for {row['Item']}", key=f"decrease_{row.name}"):
                    if df.at[row.name, 'Number'] >= amount_to_change:
                        df.at[row.name, 'Number'] -= amount_to_change
                        set_inventory(df)  # Save updated inventory to Firebase
                        st.success(f"Decreased count for {row['Item']} by {amount_to_change}! New count: {df.at[row.name, 'Number']}")
                    else:
                        st.warning(f"Count for {row['Item']} cannot be decreased below zero.")

            with col_increase:
                if st.button(f"Increase for {row['Item']}", key=f"increase_{row.name}"):
                    df.at[row.name, 'Number'] += amount_to_change
                    set_inventory(df)  # Save updated inventory to Firebase
                    st.success(f"Increased count for {row['Item']} by {amount_to_change}! New count: {df.at[row.name, 'Number']}")

        # Show updated counts after interaction
        st.subheader("Updated Inventory")
        st.write(df)

        # Create a BytesIO object to save the updated DataFrame as Excel
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Inventory")

        output.seek(0)  # Rewind to the start of the BytesIO buffer

        # Email sending functionality
        st.subheader("Send Updated Inventory via Email")
        
        recipient_email = st.text_input("Enter recipient email address")
        email_subject = "Updated Inventory File"
        email_body = "Attached is the updated inventory file in Excel format."

        if st.button("Send Email"):
            if recipient_email:
                success = send_email_smtp(
                    recipient_email, email_subject, email_body, output, "updated_inventory.xlsx"
                )

                if success:
                    st.success(f"Email successfully sent to {recipient_email}!")
                else:
                    st.error("Failed to send email.")
            else:
                st.warning("Please enter a recipient email address.")
    else:
        st.info("No items found matching the selected filter.")

# Function for waitlist page
import json
import time

def waitlist_page():
    st.title("Waitlist")

    # Fetch current waitlist from Redis
    waitlist_df = get_waitlist()

    # Input for user name
    name = st.text_input("Enter your name to join the waitlist")

    # Button to add to waitlist
    if st.button("Add to Waitlist"):
        if name:
            # Append the name to the waitlist DataFrame
            new_entry = pd.DataFrame([[name]], columns=["Name"])
            waitlist_df = pd.concat([waitlist_df, new_entry], ignore_index=True)
            set_waitlist(waitlist_df)
            st.success(f"{name} has been added to the waitlist!")
        else:
            st.warning("Please enter a name.")

    # Display the waitlist
    st.subheader("Current Waitlist")
    st.write(waitlist_df)

    # Remove a name from the waitlist
    if not waitlist_df.empty:
        name_to_remove = st.selectbox("Select a name to remove from the waitlist", waitlist_df['Name'])

        # Only show the remove button if a name is selected
        if st.button("Remove from Waitlist"):
            # Remove the selected name from the waitlist
            waitlist_df = waitlist_df[waitlist_df['Name'] != name_to_remove]
            set_waitlist(waitlist_df)
            st.success(f"{name_to_remove} has been removed from the waitlist!")

            # Pause for a brief moment to display the success message
            time.sleep(1)  # 1-second delay to allow the success message to show

            # Now trigger the rerun to refresh the list and UI
            st.experimental_rerun()

    # Reset button to clear the waitlist
    if st.button("Reset Waitlist"):
        waitlist_df = pd.DataFrame(columns=["Name"])
        set_waitlist(waitlist_df)
        st.success("Waitlist has been reset!")
        time.sleep(1)
        st.experimental_rerun()

    # Display the total count of people added
    st.subheader("Total Added to Waitlist")
    st.write(len(waitlist_df))

    # Display the next person on the waitlist
    if not waitlist_df.empty:
        next_person = waitlist_df.iloc[0]['Name']  # Get the first person in the waitlist
        st.markdown(f"<h1 style='text-align: center;'>Next Up: {next_person}</h1>", unsafe_allow_html=True)

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ("Inventory Tracker", "Waitlist"))

# Page navigation
if page == "Inventory Tracker":
    inventory_tracker()
else:
    waitlist_page()
