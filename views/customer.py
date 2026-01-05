import streamlit as st
import pandas as pd
from utils import get_customer_summary, get_my_shipments, run_query

def show_dashboard():
    """Displays summary metrics for the logged-in customer"""
    cust_id = st.session_state.get('user_id')
    if not cust_id: return

    outgoing, incoming, spent = get_customer_summary(cust_id)
    
    st.title("My Dashboard")
    
    # Overview Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Outgoing Shipments", outgoing)
    c2.metric("Incoming Deliveries", incoming)
    c3.metric("Total Spending", f"₺{spent:,.2f}")

    st.divider()
    st.info("Navigate to 'My Shipments' to view detailed tracking information.")

def show_my_shipments():
    """Lists all shipments sent by the user"""
    cust_id = st.session_state.get('user_id')
    st.title("📦 My Shipments")
    
    data = get_my_shipments(cust_id)
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info("No outgoing shipments found in your history.")

def show_incoming():
    """Displays active shipments currently heading to the user's address"""
    cust_id = st.session_state.get('user_id')
    st.title("📥 Incoming Deliveries")
    
    # Query for active shipments where the user is the receiver
    sql = """
    SELECT c.CargoID, s.FirstName as SenderName, s.City as Origin, 
           c.CurrentStatus, st.ServiceType
    FROM Cargos c
    JOIN Customers s ON c.SenderCustID = s.CustID
    JOIN ServiceTypes st ON c.ServiceTypeID = st.ServiceTypeID
    WHERE c.ReceiverCustID = %s AND c.CurrentStatus NOT IN ('Delivered', 'Returned')
    """
    incoming_data = run_query(sql, (cust_id,))
    
    if incoming_data:
        st.dataframe(pd.DataFrame(incoming_data), use_container_width=True)
    else:
        st.success("You have no active incoming deliveries at the moment.")

def show_invoices():
    """Lists all payment records and invoices for the customer"""
    cust_id = st.session_state.get('user_id')
    st.title("🧾 Invoices")
    
    # Fetch invoice history ordered by date
    sql = """
    SELECT InvoiceID, CargoID, InvoiceDate, TotalAmount 
    FROM Invoice 
    WHERE CustID = %s 
    ORDER BY InvoiceDate DESC
    """
    invoices = run_query(sql, (cust_id,))
    
    if invoices:
        st.dataframe(pd.DataFrame(invoices), use_container_width=True)
    else:
        st.info("No invoices found associated with this account.")