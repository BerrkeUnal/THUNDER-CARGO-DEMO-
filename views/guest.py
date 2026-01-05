import streamlit as st
import pandas as pd
import random
from database import run_query
import string
from captcha.image import ImageCaptcha
import io

def show_about():
    st.title("About Thunder Cargo")
    st.markdown("Established in 2025 by Berke Ünal, Thunder Cargo was born from a vision to redefine modern logistics. We combine cutting-edge technology with a robust global network to ensure your shipments are delivered with lightning speed and precision. Whether it's local distribution or international transit, our mission is simple: to bridge distances reliably and efficiently.")

def mask_name(full_name):
    """Masks names for privacy compliance: Ahmet Yılmaz -> A**** Y*****"""
    if not full_name or str(full_name) == 'nan': return "******"
    parts = full_name.split()
    masked_parts = [p[0] + "*" * (len(p)-1) if len(p) > 1 else p for p in parts]
    return " ".join(masked_parts)

def init_captcha():
    """Generates a new captcha if it doesn't exist in session state"""
    if 'captcha_text' not in st.session_state:
        # Generate 5-digit random string with uppercase letters and digits
        chars = string.ascii_uppercase + string.digits
        captcha_text = ''.join(random.choice(chars) for _ in range(5))
        st.session_state['captcha_text'] = captcha_text
        
        # Generate image in memory
        image = ImageCaptcha(width=280, height=90)
        data = image.generate(captcha_text)
        st.session_state['captcha_image'] = data.getvalue()

def show_captcha():
    init_captcha()
    st.image(st.session_state['captcha_image'], caption='Please enter the code shown in the image')
    user_input = st.text_input("Verification Code", key="captcha_input")
    
    if st.button("Verify Code"):
        if user_input.upper() == st.session_state['captcha_text']:
            st.success("Verification Successful!")
        else:
            st.error("Invalid code! Please try again.")
            # Clear captcha to force regeneration
            del st.session_state['captcha_text']
            st.rerun()

def verify_captcha(user_input):
    """Checks the user input against the generated captcha"""
    if 'captcha_text' in st.session_state:
        return user_input.upper() == st.session_state['captcha_text'].upper()
    return False

def show_price_calculator():
    st.title("💰 Shipping Cost Calculator")
    st.write("Calculate the estimated shipping cost based on the weight and volume of your package.")

    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📦 Package Information")
            # Actual weight input
            actual_weight = st.number_input("Actual Weight (kg)", min_value=0.1, step=0.5, value=1.0)
            
            st.markdown("**Dimensions**")
            d_col1, d_col2, d_col3 = st.columns(3)
            with d_col1: length = st.number_input("Length (cm)", min_value=1, value=20)
            with d_col2: width = st.number_input("Width (cm)", min_value=1, value=20)
            with d_col3: height = st.number_input("Height (cm)", min_value=1, value=20)

        with col2:
            st.subheader("🚚 Shipping Preferences")
            service_type = st.selectbox("Service Level", ["Standard Shipping", "Express Delivery (Lightning)"])
            distance_range = st.selectbox("Distance Range", ["Local (Within City)", "Regional (Nearby Cities)", "Long Distance"])

        # CALCULATION LOGIC
        # Volumetric Weight (Dim Weight) Formula: (L*W*H) / 5000
        volumetric_weight = (length * width * height) / 5000
        
        # Chargeable Weight is the higher of Actual vs Volumetric
        chargeable_weight = max(actual_weight, volumetric_weight)

        # Pricing Factors
        base_price = 50.0  # Minimum starting price in TL
        per_kg_rate = 15.0 # Price per kg
        
        # Multipliers
        service_mult = 1.6 if "Express" in service_type else 1.0
        distance_map = {"Local (Within City)": 1.0, "Regional (Nearby Cities)": 1.2, "Long Distance": 1.7}
        dist_mult = distance_map[distance_range]

        # Final Formula: (Base + (Weight * Rate)) * Multipliers
        estimated_total = (base_price + (chargeable_weight * per_kg_rate)) * service_mult * dist_mult

        st.divider()
        
        # DISPLAY RESULTS
        res_c1, res_c2, res_c3 = st.columns(3)
        res_c1.metric("Actual Weight", f"{actual_weight} kg")
        res_c2.metric("Volumetric Weight", f"{volumetric_weight:.2f} kg")
        res_c3.metric("Estimated Cost", f"₺{estimated_total:,.2f}")

        st.info("💡 **Note:** Logistics companies charge based on the **higher value** between actual weight and volumetric weight (size).")

# --- BRANCH LOCATOR ---

def show_branch_locator():
    st.title("📍 Find a Branch")
    st.write("Locate the nearest Thunder Cargo branch for shipping and pickup.")
    
    # Fetch cities
    cities_res = run_query("SELECT DISTINCT BranchCity FROM CargoBranches ORDER BY BranchCity")
    cities = [row['BranchCity'] for row in cities_res] if cities_res else []
    
    selected_city = st.selectbox("Select City", ["Choose..."] + cities)
    
    if selected_city != "Choose...":
        # Fetch districts based on selected city
        districts_res = run_query("SELECT DISTINCT BranchDistrict FROM CargoBranches WHERE BranchCity = %s ORDER BY BranchDistrict", (selected_city,))
        districts = [row['BranchDistrict'] for row in districts_res] if districts_res else []
        
        selected_district = st.selectbox("Select District", ["All Districts"] + districts)
        
        # Build query based on selection
        query = "SELECT * FROM CargoBranches WHERE BranchCity = %s"
        params = [selected_city]
        
        if selected_district != "All Districts":
            query += " AND BranchDistrict = %s"
            params.append(selected_district)
            
        branches = run_query(query, tuple(params))
        
        st.divider()
        st.subheader(f"Branches in {selected_city}")
        
        if branches:
            # Display branch details in containers
            for b in branches:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### 🏢 {b['BranchName']}")
                        st.markdown(f"**📍 Address:** {b['BranchAddress']}")
                        st.markdown(f"**🏙️ District:** {b['BranchDistrict']} / {b['BranchCity']}")
                    with c2:
                        st.markdown(f"**📞 Phone:**\n`{b['BranchNumber']}`")
                        st.markdown(f"**📧 Email:**\n{b['BranchEmail']}")
                        st.button(f"Show on Map", key=b['BranchID'], disabled=True, help="Map integration requires Lat/Long data.")
        else:
            st.warning("No branches found in this location.")

# --- PUBLIC SHIPMENT TRACKING ---

def show_public_tracking():
    st.title("🔎 Track Your Shipment")
    st.write("Enter your tracking number to see the live status of your cargo.")
    
    # Captcha Initialization and Display
    init_captcha() 
    
    st.image(st.session_state['captcha_image'], width=250)
    captcha_input = st.text_input("Enter the code from the image", placeholder="Verification code", key="tracking_captcha")

    # Tracking Input
    tracking_no = st.text_input("Tracking Number (Cargo ID)", placeholder="Ex: CG001", max_chars=5)
    
    search_btn = st.button("Track Cargo", type="primary", use_container_width=True)

    if search_btn:
        # Verify Captcha
        if not captcha_input or not verify_captcha(captcha_input):
            st.error("❌ Security check failed. Please enter the code correctly.")
            if 'captcha_text' in st.session_state:
                del st.session_state['captcha_text']
            st.rerun()
            return 

        if tracking_no:
            # Database query for cargo details
            cargo_sql = """
            SELECT c.CargoID, c.CurrentStatus, c.LastUpdated,
                   s.FirstName as SenderName, s.LastName as SenderLast,
                   r.FirstName as ReceiverName, r.LastName as ReceiverLast,
                   ob.BranchCity as Origin, db.BranchCity as Dest
            FROM Cargos c
            JOIN Customers s ON c.SenderCustID = s.CustID
            JOIN Customers r ON c.ReceiverCustID = r.CustID
            JOIN CargoBranches ob ON c.OriginBranchID = ob.BranchID
            JOIN CargoBranches db ON c.DestBranchID = db.BranchID
            WHERE c.CargoID = %s
            """
            cargo_res = run_query(cargo_sql, (tracking_no,))
            
            if cargo_res:
                cargo = cargo_res[0]
                st.success(f"✅ Shipment Found: {tracking_no}")
                
                # Summary Cards
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Current Status", cargo['CurrentStatus'])
                    c2.metric("Origin", cargo['Origin'])
                    c3.metric("Destination", cargo['Dest'])
                    # Masked Name for Privacy
                    c4.metric("Receiver", mask_name(f"{cargo['ReceiverName']} {cargo['ReceiverLast']}"))

                # Database query for movement logs
                log_sql = """
                SELECT t.LogTimestamps, st.StatusDescription, b.BranchName, b.BranchCity
                FROM TrackingLog t
                JOIN CargoStatusType st ON t.StatusID = st.StatusID
                JOIN CargoBranches b ON t.BranchID = b.BranchID
                WHERE t.CargoID = %s
                ORDER BY t.LogTimestamps DESC
                """
                logs = run_query(log_sql, (tracking_no,))
                
                st.subheader("📅 Shipment Journey")
                
                if logs:
                    # Timeline visualization
                    for i, log in enumerate(logs):
                        ts = log['LogTimestamps']
                        date_str = ts.strftime("%d.%m.%Y")
                        time_str = ts.strftime("%H:%M")
                        
                        icon = "🟢" if i == 0 else "⬇️"
                        if "Delivered" in log['StatusDescription']: icon = "🏁"
                        
                        with st.container():
                            tc1, tc2, tc3 = st.columns([1, 1, 6])
                            tc1.caption(f"{date_str}\n{time_str}")
                            tc2.markdown(f"<h3 style='text-align: center;'>{icon}</h3>", unsafe_allow_html=True)
                            tc3.markdown(f"**{log['StatusDescription']}**")
                            tc3.write(f"📍 {log['BranchName']} ({log['BranchCity']})")
                            st.divider()
                else:
                    st.info("No movement history available yet.")
            else:
                st.warning("⚠️ No shipment found with this Tracking Number.")
        else:
            st.warning("⚠️ Please enter a Tracking Number.")