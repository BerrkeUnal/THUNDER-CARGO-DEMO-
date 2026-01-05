import streamlit as st
import pandas as pd
import plotly.express as px
import time
from database import run_query
from utils import (
    get_dashboard_stats, get_branch_cargo_distribution,
    get_cargo_details, get_progress_value, get_all_shipments_list,
    get_all_employees_extended, get_dropdown_data, add_new_employee_logic,
    get_my_branch_employees, update_employee_logic, delete_employee_logic,
    update_cargo_status_logic, create_shipment_logic, 
    add_new_vehicle, get_vehicles_by_branch
)

# --- TRACKING ---
def show_tracking():
    """Internal tracking tool for employees to check shipment status via ID"""
    st.title("🔎 Internal Tracking")
    cargo_id_input = st.text_input("Enter Cargo ID (Ex: CG001)", max_chars=5)
    
    if st.button("Search", type="primary"):
        if cargo_id_input:
            cargo = get_cargo_details(cargo_id_input)
            if cargo:
                st.subheader("Live Status")
                # Progress bar visualization based on status
                pval = get_progress_value(cargo['CurrentStatus'])
                st.progress(pval)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**From:** {cargo['FromCity']}")
                    st.write(f"**To:** {cargo['ToCity']}")
                with c2:
                    st.write(f"**Sender:** {cargo['SenderName']}")
                    st.write(f"**Receiver:** {cargo['ReceiverName']}")
                
                st.info(f"Current Status: {cargo['CurrentStatus']}")
            else:
                st.error("Cargo not found in the system.")

# --- DASHBOARD ---
def show_dashboard():
    """Main management dashboard with branch metrics and global charts"""
    br_id = st.session_state.get('branch_id', 'BR001')
    c_count, rev, act_br = get_dashboard_stats(br_id)
    
    st.title("📊 Logistics Dashboard")
    st.subheader(f"Overview for Branch: {br_id}")
    
    # Key Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Cargo Count", c_count)
    col2.metric("Revenue", f"₺{rev:,.2f}")
    col3.metric("Active Branches", act_br)
    
    st.divider()
    
    # Visual Analytics
    df = pd.DataFrame(get_branch_cargo_distribution())
    if not df.empty:
        fig = px.bar(df, x='BranchName', y='CargoCount', title="Global Cargo Volume by Branch",
                     labels={'BranchName': 'Branch', 'CargoCount': 'Total Shipments'})
        st.plotly_chart(fig, use_container_width=True)

# --- ALL SHIPMENTS ---
def show_all_shipments():
    st.title("📋 Branch Shipments")
    
    # Retrieve the admin's branch ID from session state
    br_id = st.session_state.get('branch_id')
    
    if br_id:
        st.info(f"📍 Showing all shipments for branch: **{br_id}**")
        data = get_all_shipments_list(br_id)
        
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("No shipments found for your branch.")
    else:
        st.error("Error: Branch information not found. Please log in again.")

# --- EMPLOYEE MANAGEMENT ---
def show_employee_management():
    """Module for handling staff hiring, updates, and records"""
    st.title("👥 Employee Management")
    
    br_id = st.session_state.get('branch_id', 'BR001')
    
    # Admin context info
    st.info(f"📍 You are currently acting as the administrator for branch: {br_id}.")

    cust_d, branches_d, services_d, roles_d = get_dropdown_data()
    roles_opt = {r['RoleName']: r['RoleID'] for r in roles_d}
    branch_names = {b['BranchID']: b['BranchName'] for b in branches_d}
    current_branch_name = branch_names.get(br_id, "Unknown Branch")

    tab1, tab2, tab3 = st.tabs(["🌍 See All Staff", "➕ Add Staff", "✏️ Manage My Staff"])
    
    # TAB 1: MASTER LIST
    with tab1:
        st.subheader("Global Company Directory")
        df = pd.DataFrame(get_all_employees_extended())
        st.dataframe(df, use_container_width=True, hide_index=True)

    # TAB 2: HIRING FORM
    with tab2:
        st.markdown(f"### Register New Staff for {current_branch_name}")
        
        with st.form("add_emp_form", clear_on_submit=False):
            r1c1, r1c2 = st.columns(2)
            with r1c1: nm = st.text_input("First Name")
            with r1c2: sn = st.text_input("Last Name")
            
            r2c1, r2c2 = st.columns(2)
            with r2c1: sal = st.number_input("Salary (₺)", min_value=17002.0, value=22005.0)
            with r2c2: ph = st.text_input("Phone Number")
            
            r3c1, r3c2 = st.columns(2)
            with r3c1: hdate = st.date_input("Hire Date")
            with r3c2: role = st.selectbox("Position", list(roles_opt.keys()))
            
            st.text_input("Assigned Branch", value=current_branch_name, disabled=True)
            
            r5c1, r5c2 = st.columns(2)
            with r5c1: usn = st.text_input("System Username")
            with r5c2: pwd = st.text_input("Initial Password", type="password")
            
            if st.form_submit_button("Submit Registration", type="primary"):
                if nm and sn and usn:
                    new_eid = add_new_employee_logic(nm, sn, ph, roles_opt[role], sal, hdate, br_id, usn, pwd)
                    st.success(f"✅ Employee Successfully Registered! ID: {new_eid}")
                else:
                    st.error("Please fill in all required fields.")

    # TAB 3: STAFF ADJUSTMENTS
    with tab3:
        st.subheader("Personnel Record Management")
        my_staff = get_my_branch_employees(br_id)
        
        if my_staff:
            # Selection of existing branch personnel
            opts = {f"{e['EmployeeName']} {e['EmployeeLastName']}": e['EmployeeID'] for e in my_staff}
            sel_name = st.selectbox("Select Staff Member to Edit", list(opts.keys()))
            sel_id = opts[sel_name]
            
            # Retrieve existing data for the selected employee
            curr_emp = next(item for item in my_staff if item["EmployeeID"] == sel_id)
            
            with st.form("edit_staff_form"):
                c1, c2 = st.columns(2)
                
                # Determine current role index for the selectbox default
                curr_role_name = next((k for k, v in roles_opt.items() if v == curr_emp['RoleID']), list(roles_opt.keys())[0])
                try:
                    role_index = list(roles_opt.keys()).index(curr_role_name)
                except:
                    role_index = 0

                with c1:
                    n_role = st.selectbox("Updated Position", list(roles_opt.keys()), index=role_index)
                    n_phone = st.text_input("Registration Number / Phone", value=curr_emp['EmployeeNumber'])
                
                with c2:
                    n_sal = st.number_input("Updated Salary", value=float(curr_emp['Salary']), step=500.0)
                    st.text_input("Branch", value=current_branch_name, disabled=True)
                
                st.write("") 
                
                # Action Buttons
                b_col1, b_col2 = st.columns([3, 1])
                
                with b_col1:
                    update_btn = st.form_submit_button("Update Records", type="primary", use_container_width=True)
                with b_col2:
                    delete_btn = st.form_submit_button("Terminate 🗑️", type="secondary", use_container_width=True)
                
                if update_btn:
                    update_employee_logic(sel_id, roles_opt[n_role], n_sal, n_phone)
                    st.success("✅ Employee records updated successfully!")
                    time.sleep(1)
                    st.rerun()
                    
                if delete_btn:
                    delete_employee_logic(sel_id)
                    st.warning("⚠️ Employee record removed from system.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("No personnel currently assigned to your branch.")

# --- ADMIN OPERATIONS ---
def show_admin_tools():
    """Advanced tools for status updates, fleet management, and shipping creation"""
    st.title("🔧 Admin Operations Center")
    
    tab_upd, tab_new, tab_vec = st.tabs(["🔄 Update Status", "📦 New Shipment", "🚛 Fleet Management"])

    # --- STATUS UPDATE LOGIC ---
    with tab_upd:
        br_id = st.session_state.get('branch_id', 'BR001')
        active_cargos = run_query("SELECT CargoID, CurrentStatus FROM Cargos WHERE OriginBranchID = %s AND CurrentStatus != 'Delivered'", (br_id,))
        
        if active_cargos:
            opts = {f"{c['CargoID']} (Status: {c['CurrentStatus']})": c['CargoID'] for c in active_cargos}
            sel_txt = st.selectbox("Select Shipment", list(opts.keys()))
            new_st = st.selectbox("New Status", ["Picked Up", "In Transit", "Out for Delivery", "Delivered"])
            
            if st.button("Commit Status Change", type="primary"):
                update_cargo_status_logic(opts[sel_txt], new_st, br_id, st.session_state['user_id'])
                st.success(f"Status for {opts[sel_txt]} updated to {new_st}!")
                time.sleep(1)
                st.rerun()
        else:
            st.info("No active shipments awaiting updates at this branch.")

    # --- NEW SHIPMENT CREATION ---
    # --- CREATE SHIPMENT (Auto-Pricing Version) ---
    with tab_new:
        st.subheader("📦 Register New Shipment")
        st.caption("Enter Customer IDs and logistics details to generate a new cargo entry.")
        
        # We still need branch and service data for the other dropdowns
        _, br_d, srv_d, _ = get_dropdown_data()
        b_opt = {b['BranchName']: b['BranchID'] for b in br_d}
        s_opt = {s['ServiceType']: s['ServiceTypeID'] for s in srv_d}
        
        current_branch_id = st.session_state.get('branch_id', 'BR001')
        curr_br_name = next((b['BranchName'] for b in br_d if b['BranchID'] == current_branch_id), current_branch_id)

        with st.form("ship_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                # CHANGED: Now using text_input for IDs
                snd_id = st.text_input("Sender Customer Full Name", placeholder="Ex: Berke Ünal")
                rcv_id = st.text_input("Receiver Customer Full Name", placeholder="Ex: Kudret Çatal")
                
                st.text_input("Originating Branch", value=curr_br_name, disabled=True)
                dst_name = st.selectbox("Destination Branch", list(b_opt.keys()))

            with c2:
                srv_name = st.selectbox("Service Level", list(s_opt.keys()))
                pay = st.selectbox("Payment Method", ["Credit Card", "Cash", "Collect on Delivery"])
                actual_w = st.number_input("Cargo Weight (kg)", min_value=0.1, step=0.5, value=1.0)
            
            st.markdown("**Package Dimensions (cm)**")
            d1, d2, d3 = st.columns(3)
            with d1: l = st.number_input("Length", value=10, min_value=1)
            with d2: wid = st.number_input("Width", value=10, min_value=1)
            with d3: h = st.number_input("Height", value=10, min_value=1)

            if st.form_submit_button("Calculate & Finalize Shipment", type="primary"):
                # 1. VALIDATION: Check if IDs are provided
                if not snd_id or not rcv_id:
                    st.error("❌ Please enter both Sender and Receiver Customer IDs.")
                    return

                # 2. AUTO-PRICING LOGIC
                vol_w = (l * wid * h) / 5000
                chargeable_w = max(actual_w, vol_w)
                
                base_fee = 50.0
                per_kg_rate = 15.0
                service_multiplier = 1.6 if "Express" in srv_name else 1.0
                is_same_branch = (dst_name == curr_br_name)
                distance_multiplier = 1.0 if is_same_branch else 1.5

                calculated_cost = (base_fee + (chargeable_w * per_kg_rate)) * service_multiplier * distance_multiplier

                # 3. DATABASE OPERATIONS
                try:
                    nid = create_shipment_logic(
                        snd_id,     # Using the ID from text_input directly
                        rcv_id,     # Using the ID from text_input directly
                        current_branch_id, 
                        b_opt[dst_name], 
                        s_opt[srv_name], 
                        actual_w, 
                        calculated_cost, 
                        pay, 
                        (l, wid, h), 
                        st.session_state['user_id']
                    )

                    st.success(f"✅ Shipment Registered Successfully!")
                    st.balloons()
                    
                    with st.expander("View Receipt Details", expanded=True):
                        res_col1, res_col2 = st.columns(2)
                        res_col1.write(f"**Tracking ID:** {nid}")
                        res_col1.write(f"**Chargeable Weight:** {chargeable_w:.2f} kg")
                        res_col2.write(f"**Total Fee:** ₺{calculated_cost:,.2f}")
                
                except Exception as e:
                    # This catches errors if the typed ID does not exist in the DB (Foreign Key Violation)
                    st.error(f"❌ Error: Customer ID not found. Please check the IDs and try again.")

    # --- FLEET MANAGEMENT ---
    with tab_vec:
        current_branch = st.session_state.get('branch_id', 'BR001')
        
        c1, c2 = st.columns([1,2])
        with c1:
            st.subheader("Add New Vehicle")
            st.caption(f"Registering to Branch: {current_branch}")
            with st.form("v_form"):
                plt = st.text_input("License Plate (e.g., 34ABC123)")
                typ = st.selectbox("Vehicle Category", ["Truck", "Van", "Motorcycle"])
                if st.form_submit_button("Register Vehicle", type="primary"):
                    if plt:
                        vid = add_new_vehicle(plt, typ, current_branch)
                        st.success(f"Vehicle Registered! System ID: {vid}")
                        st.rerun()
                    else:
                        st.warning("Valid license plate required.")
        with c2:
            st.subheader(f"Active Fleet at {current_branch}")
            v_data = get_vehicles_by_branch(current_branch)
            if v_data: 
                st.dataframe(pd.DataFrame(v_data), use_container_width=True, hide_index=True)
            else: 
                st.info(f"No vehicles currently assigned to {current_branch}.")