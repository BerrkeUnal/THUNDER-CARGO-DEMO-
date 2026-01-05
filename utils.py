import random
import string
import datetime
from database import run_query 

# --- GENERAL HELPER FUNCTIONS ---

def generate_id():
    """Generates a random 5-digit ID (e.g., AB123)"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def get_progress_value(status):
    """Returns the value for the tracking progress bar based on status"""
    status = str(status).lower()
    if "ready" in status or "created" in status or "hazır" in status: 
        return 25
    elif "transit" in status or "way" in status or "yol" in status: 
        return 50
    elif "distribution" in status or "delivery" in status or "dağıtım" in status: 
        return 75
    elif "delivered" in status or "completed" in status or "teslim" in status: 
        return 100
    return 0

# --- 1. LOGIN & AUTHENTICATION ---

def check_login(username, password):
    """Verifies credentials for both Employees and Customers"""
    emp = run_query("SELECT * FROM Employees WHERE Username = %s AND PasswordHash = %s AND IsActive = 1", (username, password))
    if emp: return {"type": "admin", "data": emp[0]}
    
    cust = run_query("SELECT * FROM Customers WHERE Username = %s AND PasswordHash = %s", (username, password))
    if cust: return {"type": "customer", "data": cust[0]}
    return None

def register_customer(name, surname, phone, email, address, city, username, password):
    """Registers a new customer and returns the generated ID"""
    new_id = "CU" + str(random.randint(100, 999))
    sql = """
    INSERT INTO Customers (CustID, FirstName, LastName, CustNumber, Email, Address, Country, City, Username, PasswordHash, LastLogin) 
    VALUES (%s, %s, %s, %s, %s, %s, 'Turkey', %s, %s, %s, NOW())
    """
    run_query(sql, (new_id, name, surname, phone, email, address, city, username, password))
    return new_id

# --- 2. DASHBOARD ---

def get_dashboard_stats(branch_id):
    """Retrieves basic metrics for a specific branch"""
    c_count = run_query("SELECT COUNT(*) as cnt FROM Cargos WHERE OriginBranchID = %s", (branch_id,))[0]['cnt']
    rev = run_query("SELECT SUM(ShippingCost) as total FROM Cargos WHERE OriginBranchID = %s", (branch_id,))[0]['total'] or 0
    act_br = run_query("SELECT COUNT(*) as cnt FROM CargoBranches")[0]['cnt']
    return c_count, rev, act_br

def get_branch_cargo_distribution():
    """Returns shipment counts grouped by branch for charts"""
    return run_query("SELECT b.BranchName, COUNT(c.CargoID) as CargoCount FROM Cargos c JOIN CargoBranches b ON c.OriginBranchID = b.BranchID GROUP BY b.BranchName")

# --- 3. TRACKING ---

def get_cargo_details(cargo_id):
    """Retrieves detailed information for a single shipment"""
    sql = """
    SELECT c.CargoID, c.CurrentStatus, c.CargoWeight, st.ServiceType,
           sender.FirstName as SenderName, receiver.FirstName as ReceiverName,
           origin.BranchCity as FromCity, dest.BranchCity as ToCity
    FROM Cargos c
    JOIN Customers sender ON c.SenderCustID = sender.CustID
    JOIN Customers receiver ON c.ReceiverCustID = receiver.CustID
    JOIN CargoBranches origin ON c.OriginBranchID = origin.BranchID
    JOIN CargoBranches dest ON c.DestBranchID = dest.BranchID
    JOIN ServiceTypes st ON c.ServiceTypeID = st.ServiceTypeID
    WHERE c.CargoID = %s
    """
    data = run_query(sql, (cargo_id,))
    return data[0] if data else None

def get_all_shipments_list(branch_id):
    """Returns a list of all shipments originating from the admin's specific branch"""
    sql = "SELECT * FROM Cargos WHERE OriginBranchID = %s ORDER BY LastUpdated DESC"
    return run_query(sql, (branch_id,))

# --- 4. EMPLOYEE OPERATIONS ---

def get_all_employees_extended():
    """Retrieves all employees with role and branch details"""
    sql = """
    SELECT e.EmployeeID, e.EmployeeName, e.EmployeeLastName, r.RoleName, 
           e.Salary, b.BranchName, e.HireDate, e.EmployeeNumber
    FROM Employees e
    LEFT JOIN CargoBranches b ON e.BranchID = b.BranchID
    LEFT JOIN EmployeeRoles r ON e.RoleID = r.RoleID
    ORDER BY b.BranchID ASC
    """
    return run_query(sql)

def add_new_employee_logic(name, surname, phone, role_id, salary, hire_date, branch_id, username, password):
    """Creates a new employee record and returns the generated ID"""
    new_id = generate_id()
    sql = """
    INSERT INTO Employees 
    (EmployeeID, EmployeeName, EmployeeLastName, EmployeeNumber, BranchID, RoleID, Salary, HireDate, Username, PasswordHash, IsActive) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
    """
    run_query(sql, (new_id, name, surname, phone, branch_id, role_id, salary, hire_date, username, password))
    return new_id

def get_my_branch_employees(branch_id):
    """Returns a list of employees working at a specific branch"""
    return run_query("SELECT * FROM Employees WHERE BranchID = %s", (branch_id,))

def update_employee_logic(emp_id, role_id, salary, phone):
    """Updates existing employee information"""
    run_query("UPDATE Employees SET RoleID = %s, Salary = %s, EmployeeNumber = %s WHERE EmployeeID = %s", (role_id, salary, phone, emp_id))

def delete_employee_logic(emp_id):
    """Deletes an employee record"""
    run_query("DELETE FROM Employees WHERE EmployeeID = %s", (emp_id,))

# --- 5. DROPDOWN DATA ---

def get_dropdown_data():
    """Retrieves lookup data for selectboxes and dropdowns"""
    cust = run_query("SELECT CustID, FirstName, LastName FROM Customers")
    branches = run_query("SELECT BranchID, BranchName FROM CargoBranches")
    services = run_query("SELECT ServiceTypeID, ServiceType FROM ServiceTypes")
    roles = run_query("SELECT RoleID, RoleName FROM EmployeeRoles")
    return cust, branches, services, roles

# --- 6. ADMIN OPERATIONS ---

def update_cargo_status_logic(cargo_id, new_status, branch_id, emp_id):
    """Updates shipment status and creates a record in the Tracking Log"""
    run_query("UPDATE Cargos SET CurrentStatus = %s, LastUpdated = NOW() WHERE CargoID = %s", (new_status, cargo_id))
    # ST005 represents a status update event
    run_query("INSERT INTO TrackingLog (TrackID, LogTimestamps, CargoID, BranchID, EmployeeID, StatusID) VALUES (LEFT(UUID(), 5), NOW(), %s, %s, %s, 'ST005')", (cargo_id, branch_id, emp_id))

def create_shipment_logic(sender_id, receiver_id, origin_id, dest_id, service_id, weight, cost, pay_type, dims, creator_id):
    """Creates a new cargo shipment and logs the initial 'Order Created' event"""
    new_id = generate_id()
    l, w, h = dims
    sql = """
    INSERT INTO Cargos (CargoID, SenderCustID, ReceiverCustID, OriginBranchID, DestBranchID, 
    CargoWeight, CargoLength, CargoWidth, CargoHeight, ShippingCost, ServiceTypeID, PaymentType, 
    CurrentStatus, PaymentStatus, LastUpdated) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Order Created', 'Pending', NOW())
    """
    run_query(sql, (new_id, sender_id, receiver_id, origin_id, dest_id, weight, l, w, h, cost, service_id, pay_type))
    
    # ST001 represents the 'Order Created' status in the log
    run_query("INSERT INTO TrackingLog (TrackID, LogTimestamps, CargoID, BranchID, EmployeeID, StatusID) VALUES (LEFT(UUID(), 5), NOW(), %s, %s, %s, 'ST001')", (new_id, origin_id, creator_id))
    return new_id

# --- 7. VEHICLE MANAGEMENT ---

def add_new_vehicle(plate, v_type, branch_id):
    """Registers a new vehicle for a specific branch"""
    new_vid = generate_id()
    sql = "INSERT INTO Vehicles (VehicleID, LicensePlate, VehicleType, CurrentBranchID) VALUES (%s, %s, %s, %s)"
    run_query(sql, (new_vid, plate, v_type, branch_id))
    return new_vid

def get_vehicles_by_branch(branch_id):
    """Retrieves all vehicles currently assigned to a branch"""
    return run_query("SELECT * FROM Vehicles WHERE CurrentBranchID = %s", (branch_id,))

# --- 8. CUSTOMER PANEL ---

def get_customer_summary(cust_id):
    """Returns summary statistics for a customer's shipments and spending"""
    outgoing = run_query("SELECT COUNT(*) as cnt FROM Cargos WHERE SenderCustID = %s", (cust_id,))[0]['cnt']
    incoming = run_query("SELECT COUNT(*) as cnt FROM Cargos WHERE ReceiverCustID = %s", (cust_id,))[0]['cnt']
    spent_res = run_query("SELECT SUM(TotalAmount) as total FROM Invoice WHERE CustID = %s", (cust_id,))
    spent = spent_res[0]['total'] if spent_res and spent_res[0]['total'] else 0
    return outgoing, incoming, spent

def get_my_shipments(cust_id):
    """Retrieves all outgoing shipments for a specific customer"""
    sql = """
    SELECT c.CargoID, r.FirstName as ReceiverName, r.City as Destination, 
           c.CurrentStatus, c.ShippingCost, c.LastUpdated
    FROM Cargos c
    JOIN Customers r ON c.ReceiverCustID = r.CustID
    WHERE c.SenderCustID = %s ORDER BY c.LastUpdated DESC
    """
    return run_query(sql, (cust_id,))