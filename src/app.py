import streamlit as st

# Title of the dashboard
st.title("GitHub Audit Dashboard")

# Add some text
st.write("Welcome to the GitHub Audit Dashboard!")

# Add a button
if st.button("Click me"):
    st.write("Button clicked!")

# Add a selectbox
option = st.selectbox("Select an option", ["Option 1", "Option 2", "Option 3"])
st.write("You selected:", option)

# Add a slider
value = st.slider("Select a value", 0, 100, 50)
st.write("Selected value:", value)