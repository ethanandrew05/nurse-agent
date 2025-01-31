import sqlite3
from datetime import datetime

def create_database():
    """Create the SQLite database with all necessary tables."""
    
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect('medical_records.db')
    cursor = conn.cursor()
    
    # Create the patients table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patient_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        age INTEGER,
        gender TEXT,
        date_of_birth DATE,
        symptoms TEXT,
        vital_signs TEXT,
        medications TEXT,
        allergies TEXT,
        medical_history TEXT,
        family_history TEXT,
        diagnosis TEXT,
        treatment_plan TEXT,
        follow_up_date DATE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create a trigger to update the updated_at timestamp if it doesn't exist
    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_patient_timestamp 
    AFTER UPDATE ON patient_records
    BEGIN
        UPDATE patient_records SET updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.id;
    END;
    ''')
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()

def update_record(patient_id: int, data: dict):
    """
    Update an existing patient record in the database.
    
    Args:
        patient_id: ID of the patient to update
        data: Dictionary containing the updated patient record data
    """
    # If all values are None, don't update
    if not any(value is not None for value in data.values()):
        print("No data to update (all values are null)")
        return
        
    conn = sqlite3.connect('medical_records.db')
    cursor = conn.cursor()
    
    # Check if patient exists
    cursor.execute('SELECT id FROM patient_records WHERE id = ?', (patient_id,))
    if not cursor.fetchone():
        print(f"No patient found with ID {patient_id}")
        conn.close()
        return
    
    # Prepare the fields and values for update
    updates = []
    values = []
    
    for field, value in data.items():
        if value is not None:  # Only include non-null values
            updates.append(f"{field} = ?")
            values.append(value)
    
    # If no fields to update, return
    if not updates:
        print("No fields to update")
        conn.close()
        return
    
    # Add patient_id to values
    values.append(patient_id)
    
    # Construct and execute the UPDATE query
    query = f'''
    UPDATE patient_records 
    SET {', '.join(updates)}
    WHERE id = ?
    '''
    
    cursor.execute(query, values)
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"Record updated successfully for patient ID: {patient_id}")

def get_patient_record(patient_id: int) -> dict:
    """
    Retrieve a single patient record from the database.
    
    Args:
        patient_id: ID of the patient to retrieve
        
    Returns:
        Dictionary containing the patient record, or None if not found
    """
    conn = sqlite3.connect('medical_records.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM patient_records WHERE id = ?', (patient_id,))
    record = cursor.fetchone()
    
    if record:
        # Get column names
        columns = [description[0] for description in cursor.description]
        # Convert to dictionary
        result = dict(zip(columns, record))
    else:
        result = None
    
    conn.close()
    return result

def get_all_records():
    """Retrieve all records from the database."""
    conn = sqlite3.connect('medical_records.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM patient_records')
    records = cursor.fetchall()
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    
    # Convert to list of dictionaries
    result = []
    for record in records:
        result.append(dict(zip(columns, record)))
    
    conn.close()
    return result

def list_patients():
    """List all patients with their basic information."""
    conn = sqlite3.connect('medical_records.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, first_name, last_name, age, gender FROM patient_records')
    patients = cursor.fetchall()
    
    if not patients:
        print("No patients in database")
        return
    
    print("\nAvailable patients:")
    print("-" * 50)
    for patient in patients:
        patient_id, first_name, last_name, age, gender = patient
        full_name = f"{first_name or ''} {last_name or ''}".strip()
        print(f"ID: {patient_id}")
        print(f"Name: {full_name or 'Not specified'}")
        print(f"Age: {age or 'Not specified'}")
        print(f"Gender: {gender or 'Not specified'}")
        print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    create_database()
    list_patients() 