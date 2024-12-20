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


# Inventory tracker function with email sending feature
def inventory_tracker():
    st.title("Inventory Tracker")
    upload_file = pd.read_csv('updated_inventory.csv')

    # # File uploader for CSV
    # upload_file = st.file_uploader("Choose a CSV File", type="csv")
        
    # Initialize session state if not already initialized
    if 'df' not in st.session_state:
        st.session_state.df = None

    if upload_file is not None:
        # Load the CSV only if it's not already loaded
        st.session_state.df = upload_file
        # pd.read_csv(upload_file)

        # Convert 'Number' column to numeric
        st.session_state.df['Number'] = pd.to_numeric(st.session_state.df['Number'], errors='coerce').fillna(0).astype(int)

    # Check if the DataFrame exists before accessing it
    if st.session_state.df is not None:
        df = st.session_state.df

        st.subheader("Data Preview")
        st.write(df.head())

        st.subheader('Filter Data')
        columns = df.columns.tolist()
        selected_column = st.selectbox("Select column to filter by", columns)
        unique_values = df[selected_column].unique()
        selected_value = st.selectbox("Select value", unique_values)

        # Filter DataFrame based on user selection
        filtered_df = df[df[selected_column] == selected_value]

        if not filtered_df.empty:
            st.subheader("Filtered Inventory Items")

            # Display the filtered DataFrame with a dropdown for decreasing counts
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
                amount_to_change = st.number_input(
                    f"Amount to change for {row['Item']}",
                    min_value=1,
                    max_value=100,  # This is the maximum number users can input (you can adjust this limit)
                    value=1,  # Default value
                    key=f"change_amount_{row.name}"  # Use row name to ensure unique keys
                )

                # Buttons to decrease or increase the count
                col_decrease, col_increase = st.columns(2)  # Create 2 columns for the buttons

                with col_decrease:
                    if st.button(f"Decrease for {row['Item']}", key=f"decrease_{row.name}"):
                        if df.at[row.name, 'Number'] >= amount_to_change:
                            df.at[row.name, 'Number'] -= amount_to_change
                            st.session_state.df.at[row.name, 'Number'] = df.at[row.name, 'Number']  # Update session state
                            st.success(f"Decreased count for {row['Item']} by {amount_to_change}! New count: {df.at[row.name, 'Number']}")
                        else:
                            st.warning(f"Count for {row['Item']} cannot be decreased below zero.")

                with col_increase:
                    if st.button(f"Increase for {row['Item']}", key=f"increase_{row.name}"):
                        df.at[row.name, 'Number'] += amount_to_change
                        st.session_state.df.at[row.name, 'Number'] = df.at[row.name, 'Number']  # Update session state
                        st.success(f"Increased count for {row['Item']} by {amount_to_change}! New count: {df.at[row.name, 'Number']}")


            # Show updated counts after interaction
            st.subheader("Updated Inventory")
            st.write(st.session_state.df)

            # Button to send the DataFrame as Excel (.xlsx) via email
            st.subheader("Send Updated Inventory via Email")
            
            # Create a BytesIO object to save Excel in memory
            output = io.BytesIO()

            # Use ExcelWriter to save the dataframe to the in-memory output stream
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="Inventory")

            # Seek to the beginning of the BytesIO stream so it can be downloaded or emailed
            output.seek(0)

            # Get email recipient from user input
            recipient_email = st.text_input("Enter recipient email address")

            # Subject and body text for the email
            email_subject = "Updated Inventory File"
            email_body = "Attached is the updated inventory file in Excel format."

            # Send email when the button is pressed
            if st.button("Send Email"):
                if recipient_email:
                    # Send email with attachment
                    success = send_email_smtp(
                        recipient_email, email_subject, email_body, output, "updated_inventory.xlsx"
                    )

                    if success:
                        st.success(f"Email successfully sent to {recipient_email}!")
                    else:
                        st.error(f"Failed to send email.")
                else:
                    st.warning("Please enter a recipient email address.")

    else:
        st.info("Please upload a CSV file to begin.")

    st.info("NOTE: order of sheet must be Item, Dose, Number, Medium, Boxes, Location")

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


# This one just has a save butotn

# def inventory_tracker():
#     st.title("Inventory Tracker")

#     # File uploader for CSV
#     upload_file = st.file_uploader("Choose a CSV File", type="csv")

#     if upload_file is not None:
#         # Load the CSV only if it's not already loaded
#         if st.session_state.df is None:
#             st.session_state.df = pd.read_csv(upload_file)

#             # Convert 'Number' column to numeric
#             st.session_state.df['Number'] = pd.to_numeric(st.session_state.df['Number'], errors='coerce').fillna(0).astype(int)

#     # Check if the DataFrame exists
#     if st.session_state.df is not None:
#         df = st.session_state.df

#         st.subheader("Data Preview")
#         st.write(df.head())

#         st.subheader('Filter Data')
#         columns = df.columns.tolist()
#         selected_column = st.selectbox("Select column to filter by", columns)
#         unique_values = df[selected_column].unique()
#         selected_value = st.selectbox("Select value", unique_values)

#         # Filter DataFrame based on user selection
#         filtered_df = df[df[selected_column] == selected_value]

#         if not filtered_df.empty:
#             st.subheader("Filtered Inventory Items")

#             # Display the filtered DataFrame with a dropdown for decreasing counts
#             for index, row in filtered_df.iterrows():
#                 col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 2, 1])  # Adjust column sizes

#                 with col1:
#                     st.write(row['Item'])

#                 with col2:
#                     st.write(row['Dose'])

#                 with col3:
#                     st.write(row['Number'])  # Display current count

#                 with col4:
#                     st.write(row['Medium'])

#                 with col5:
#                     st.write(row['Location'])

#                 # Dropdown to select amount to decrease
#                 amount_to_decrease = st.number_input(
#                     f"Amount to decrease for {row['Item']}",
#                     min_value=1,
#                     max_value=row['Number'],  # Max value is the current count
#                     value=1,  # Default value
#                     key=f"decrease_amount_{row.name}"  # Use row name to ensure unique keys
#                 )

#                 # Button to decrease the count
#                 if st.button("Decrease", key=f"decrease_{row.name}"):
#                     if df.at[row.name, 'Number'] >= amount_to_decrease:
#                         df.at[row.name, 'Number'] -= amount_to_decrease
#                         st.session_state.df.at[row.name, 'Number'] = df.at[row.name, 'Number']  # Update session state
#                         st.success(f"Decreased count for {row['Item']} by {amount_to_decrease}! New count: {df.at[row.name, 'Number']}")
#                     else:
#                         st.warning(f"Count for {row['Item']} cannot be decreased below zero.")

#             # Show updated counts after interaction
#             st.subheader("Updated Inventory")
#             st.write(st.session_state.df)

#             # Button to save the DataFrame as Excel
#             st.subheader("Save Updated Inventory")
#             # Convert DataFrame to Excel in-memory
#             # Create a BytesIO object to save Excel in memory
#             output = io.BytesIO()

#             # Use ExcelWriter to save the dataframe to the in-memory output stream
#             with pd.ExcelWriter(output, engine='openpyxl') as writer:
#                 df.to_excel(writer, index=False, sheet_name="Inventory")

#             # Seek to the beginning of the BytesIO stream so it can be downloaded
#             output.seek(0)

#             # st.download_button(
#             #     label="Download Excel File",
#             #     data=output,
#             #     file_name="updated_inventory.xlsx",
#             #     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#             # )

#             # Get email recipient from user input
#             recipient_email = st.text_input("Enter recipient email address")

#             # Subject and body text for the email
#             email_subject = "Updated Inventory File"
#             email_body = "Attached is the updated inventory file in Excel format."

#             # Send email when the button is pressed
#             if st.button("Send Email"):
#                 if recipient_email:
#                     # Send email with attachment
#                     response = send_email_with_attachment(
#                         recipient_email, email_subject, email_body, output, "updated_inventory.xlsx"
#                     )

#                     if response.status_code == 202:
#                         st.success(f"Email successfully sent to {recipient_email}!")
#                     else:
#                         st.error(f"Failed to send email. Status code: {response.status_code}")
#                 else:
#                     st.warning("Please enter a recipient email address.")


#     st.info("Use the filters to select items and decrease counts.")
#     st.info("NOTE: order of sheet must be Item, Dose, Number, Medium, Boxes, Location")
