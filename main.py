import streamlit as st
import time
import random
from views import guest, admin, customer
from database import run_query, generate_id 
import datetime 

# CONFIGURATION 
st.set_page_config(page_title="Thunder Cargo", layout="wide", page_icon="⚡")

# SESSION STATE MANAGEMENT 
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = 'guest' 
if 'username' not in st.session_state:
    st.session_state['username'] = ''

# AUTHENTICATION FUNCTIONS 
def login_process(username, password):
    # 1. Check Employee Table first
    # Note: Using plain text comparison for demo purposes.
    emp_query = """
    SELECT EmployeeID, EmployeeName, EmployeeLastName, BranchID, RoleID 
    FROM Employees 
    WHERE Username = %s AND PasswordHash = %s AND IsActive = 1
    """
    employee = run_query(emp_query, (username, password))
    
    if employee:
        user = employee[0]
        st.session_state['user_role'] = 'admin' # Role for Streamlit navigation
        st.session_state['user_id'] = user['EmployeeID']
        st.session_state['username'] = f"{user['EmployeeName']} {user['EmployeeLastName']}"
        st.session_state['branch_id'] = user['BranchID'] # Critical for branch-based management
        st.session_state['role_id'] = user['RoleID']
        
        st.success(f"Login Successful! Welcome {st.session_state['username']}")
        time.sleep(0.5)
        st.rerun()
        return

    # 2. If not employee, check Customers Table
    cust_query = """
    SELECT CustID, FirstName, LastName 
    FROM Customers 
    WHERE Username = %s AND PasswordHash = %s
    """
    customer_data = run_query(cust_query, (username, password))
    
    if customer_data:
        user = customer_data[0]
        st.session_state['user_role'] = 'customer'
        st.session_state['user_id'] = user['CustID'] # Critical for fetching customer specific data
        st.session_state['username'] = f"{user['FirstName']} {user['LastName']}"
        
        st.success("Customer Login Successful! Redirecting...")
        time.sleep(0.5)
        st.rerun()
        return

    # 3. Handle invalid credentials
    st.error("Invalid username or password!")

def logout_process():
    st.session_state['user_role'] = 'guest'
    st.session_state['username'] = ''
    st.rerun()

# --- GUEST NAVIGATION ---
if st.session_state['user_role'] == 'guest':
    
    st.write("") 
    st.write("")

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        with st.container(border=True):
            col_img1, col_img2, col_img3 = st.columns([1,1,1])
            with col_img2:
                st.image("thunderimage.png", use_container_width=3)
            
            st.markdown("<h1 style='text-align: center;'>Thunder Cargo ⚡</h1>", unsafe_allow_html=True)
            
            # --- LOGIN / REGISTER TABS ---
            tab_login, tab_register = st.tabs(["🔒 Log In", "📝 Sign Up"])
            
            # --- TAB 1: LOGIN ---
            with tab_login:
                with st.form("login_form"):
                    user_input = st.text_input("Username", placeholder="Username")
                    pass_input = st.text_input("Password", type="password", placeholder="Password")
                    
                    submitted = st.form_submit_button("Log In", use_container_width=True, type="primary")
                    
                    if submitted:
                        login_process(user_input, pass_input)
                
                # Demo Credentials Info
                st.info("Demo: Admin (ali.v/pass1) | Client (ahmety/hash1)")

            # --- TAB 2: REGISTER ---
            with tab_register:
                st.write("Create a new account and track your shipments.")
                with st.form("register_form"):
                    # Two-column form layout
                    r_col1, r_col2 = st.columns(2)
                    with r_col1:
                        new_name = st.text_input("Name*")
                        new_surname = st.text_input("Surname*")
                        new_phone = st.text_input("Phone Number*", placeholder="5XX...")
                        new_city = st.selectbox("City*", ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Other"])
                    
                    with r_col2:
                        new_email = st.text_input("E-mail")
                        new_username = st.text_input("Username ")
                        new_pass = st.text_input("Create Password", type="password")
                        new_address = st.text_area("Address", height=100)
                    
                    # Submit Registration
                    reg_submit = st.form_submit_button("Sign Up", use_container_width=True, type="primary")
                    
                    if reg_submit:
                        if new_name and new_username and new_pass and new_phone:
                            try:
                                rand_suffix = str(random.randint(100, 999))
                                new_cust_id = "CU" + rand_suffix
                                
                                # SQL Insert Query
                                insert_query = """
                                INSERT INTO Customers 
                                (CustID, FirstName, LastName, CustNumber, Email, Address, Country, City, Username, PasswordHash, LastLogin)
                                VALUES (%s, %s, %s, %s, %s, %s, 'Turkey', %s, %s, %s, NOW())
                                """
                                params = (new_cust_id, new_name, new_surname, new_phone, new_email, new_address, new_city, new_username, new_pass)
                                
                                run_query(insert_query, params)
                                st.success("✅ Registration Successful! Please log in from the 'Log In' tab.")
                                time.sleep(1) 
                            except Exception as e:
                                # Error handling for duplicate entries
                                if "Duplicate entry" in str(e):
                                    st.error("❌ Error: This Username or Phone is already registered.")
                                else:
                                    st.error(f"Registration Error: {e}")
                        else:
                            st.warning("⚠️ Please fill in all required fields.")

            # Footer / Quick Access Links
                        
            about_thunder = st.radio(
                "Quick Access", 
                ["About Us", "Branches", "Track Shipment", "Price Calculator"], # Buraya eklendi
                horizontal=True
            )

            if about_thunder == "About Us":
                guest.show_about()
            elif about_thunder == "Branches":
                guest.show_branch_locator()
            elif about_thunder == "Track Shipment":    
                guest.show_public_tracking()
            elif about_thunder == "Price Calculator": # Yeni eklenen kısım
                guest.show_price_calculator()


# --- ADMIN NAVIGATION ---
elif st.session_state['user_role'] == 'admin':
    st.sidebar.image("thunderimage.png", use_container_width=True)
    st.sidebar.success(f"User: **{st.session_state['username']}**")
    st.sidebar.subheader("Admin Panel")
    page_selection = st.sidebar.radio("Operations", 
        ["📊 Dashboard", "📦 Cargo Tracking", "📋 All Shipments", "👥 Employee Management", "🔧 Admin Tools"])
    
    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        logout_process()

    # Admin Page Routing
    if page_selection == "📊 Dashboard":
        admin.show_dashboard()
    elif page_selection == "📦 Cargo Tracking":
        admin.show_tracking()
    elif page_selection == "📋 All Shipments":
        admin.show_all_shipments()
    elif page_selection == "👥 Employee Management":
        admin.show_employee_management()
    elif page_selection == "🔧 Admin Tools":
        admin.show_admin_tools()


# --- CUSTOMER NAVIGATION ---
elif st.session_state['user_role'] == 'customer':
    st.sidebar.image("thunderimage.png", use_container_width=True)
    st.sidebar.info(f"Welcome, **{st.session_state['username']}**")
    st.sidebar.subheader("Customer Portal")
    
    # Expanded menu options for Customer
    page_selection = st.sidebar.radio("My Account", 
        ["📊 Dashboard", "📦 My Shipments", "📥 Incoming Deliveries", "🧾 Invoices", "🚚 Request Courier"])
    
    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        logout_process()

    # Customer Page Routing
    if page_selection == "📊 Dashboard":
        customer.show_dashboard()
    elif page_selection == "📦 My Shipments":
        customer.show_my_shipments()
    elif page_selection == "📥 Incoming Deliveries":
        customer.show_incoming()
    elif page_selection == "🧾 Invoices":
        customer.show_invoices()
    elif page_selection == "🚚 Request Courier":
        customer.show_courier_request()