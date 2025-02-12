import sqlite3
import os
from datetime import datetime

# Get the absolute path to the database
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'medical_records.db')

def calculate_age(date_of_birth):
    """Calculate age from date of birth."""
    if not date_of_birth:
        return None
    try:
        dob = datetime.strptime(date_of_birth, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except (ValueError, TypeError):
        return None

def create_database():
    """Create the SQLite database with all necessary tables."""
    
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create the patients table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patient_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        date_of_birth DATE,
        gender TEXT,
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
    
    # Create a view for patient records that includes calculated age
    cursor.execute('''
    DROP VIEW IF EXISTS patient_records_with_age;
    ''')
    
    cursor.execute('''
    CREATE VIEW patient_records_with_age AS
    SELECT 
        *,
        CASE 
            WHEN date_of_birth IS NOT NULL THEN
                (CAST(strftime('%Y.%m%d', 'now') - strftime('%Y.%m%d', date_of_birth) AS INTEGER))
            ELSE NULL
        END as age
    FROM patient_records;
    ''')
    
    # Create a trigger to update the updated_at timestamp
    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_patient_timestamp 
    AFTER UPDATE ON patient_records
    BEGIN
        UPDATE patient_records SET updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.id;
    END;
    ''')
    
    # Check if we need to add a test patient
    cursor.execute("SELECT COUNT(*) FROM patient_records")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Add a test patient
        cursor.execute('''
        INSERT INTO patient_records (
            first_name, last_name, date_of_birth, gender,
            symptoms, vital_signs, medications, allergies,
            medical_history, family_history, diagnosis,
            treatment_plan, follow_up_date, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'John', 'Doe', '1979-01-15', 'Male',
            'Headache, Fever', 'BP 120/80, Temp 38.5°C', 'Aspirin',
            'Penicillin', 'Hypertension', 'Father: Heart Disease',
            'Common Cold', 'Rest and fluids', '2024-02-15',
            'Patient reports feeling better'
        ))
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()

def update_record(patient_id: int, data: dict):
    """
    Update an existing patient record in the database.
    Appends new data to existing fields without duplicating information.
    
    Args:
        patient_id: ID of the patient to update
        data: Dictionary containing the updated patient record data
    """
    # If all values are None, don't update
    if not any(value is not None for value in data.values()):
        print("No data to update (all values are null)")
        return
        
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if patient exists
    cursor.execute('SELECT * FROM patient_records WHERE id = ?', (patient_id,))
    current_record = cursor.fetchone()
    if not current_record:
        print(f"No patient found with ID {patient_id}")
        conn.close()
        return
    
    # Convert current record to dictionary
    columns = [description[0] for description in cursor.description]
    current_data = dict(zip(columns, current_record))
    
    # List of fields that should never be updated from transcripts
    protected_fields = ['id', 'first_name', 'last_name', 'date_of_birth', 'gender', 'created_at', 'updated_at']
    
    # Filter out protected fields and prepare updates
    update_data = {}
    for key, new_value in data.items():
        if key in protected_fields or new_value is None:
            continue
            
        current_value = current_data.get(key)
        if current_value in [None, "None", ""]:  # Handle empty or None values
            # If current value is empty/None, just use the new value
            update_data[key] = new_value
        elif key != 'notes':  # Notes are handled separately
            # Split both current and new values into individual items
            current_items = {item.strip().lower() for item in str(current_value).split(',') if item.strip() and item.strip().lower() != 'none'}
            new_items = {item.strip().lower() for item in str(new_value).split(',') if item.strip()}
            
            # Only add items that don't exist (case-insensitive comparison)
            new_unique_items = new_items - current_items
            
            if new_unique_items:  # Only update if there are new unique items
                # Combine existing items with new unique items
                all_items = current_items | new_unique_items
                # Convert back to original case using the new values where possible
                final_items = []
                for item in sorted(all_items):
                    # Try to find original case from new values first, then use lowercase if not found
                    original_case = next((x.strip() for x in str(new_value).split(',') if x.strip().lower() == item), 
                                      next((x.strip() for x in str(current_value).split(',') if x.strip().lower() == item),
                                           item))
                    final_items.append(original_case)
                update_data[key] = ', '.join(final_items)
    
    # Handle notes separately - always append with timestamp
    if data.get('notes'):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_notes = current_data.get('notes')
        if current_notes in [None, "None", ""]:
            new_notes = f"[{timestamp}]\n{data['notes']}"
        else:
            new_notes = f"{current_notes}\n\n[{timestamp}]\n{data['notes']}"
        update_data['notes'] = new_notes
    
    if update_data:
        # Construct the update query
        update_query = 'UPDATE patient_records SET ' + ', '.join(f'{k} = ?' for k in update_data.keys()) + ' WHERE id = ?'
        cursor.execute(update_query, list(update_data.values()) + [patient_id])
        conn.commit()
        print(f"Record updated successfully for patient ID: {patient_id}")
        
        # Print what was updated
        print("\nUpdated fields:")
        for key, value in update_data.items():
            if key == 'notes':
                print(f"{key}: Added new entry with timestamp")
            else:
                if current_data.get(key) in [None, "None", ""]:
                    print(f"{key}: Set initial value to: {value}")
                else:
                    current_items = {item.strip().lower() for item in str(current_data[key]).split(', ') if item.strip() and item.strip().lower() != 'none'}
                    new_items = {item.strip().lower() for item in str(value).split(', ') if item.strip()}
                    added_items = new_items - current_items
                    if added_items:
                        print(f"{key}: Added new items: {', '.join(sorted(added_items))}")
                    else:
                        print(f"{key}: No new items to add")
    
    conn.close()

def get_patient_record(patient_id: int) -> dict:
    """
    Retrieve a single patient record from the database.
    
    Args:
        patient_id: ID of the patient to retrieve
        
    Returns:
        Dictionary containing the patient record, or None if not found
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Use the view that includes calculated age
    cursor.execute('SELECT * FROM patient_records_with_age WHERE id = ?', (patient_id,))
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
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Use the view that includes calculated age
    cursor.execute('SELECT * FROM patient_records_with_age')
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
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Use the view that includes calculated age
    cursor.execute('SELECT id, first_name, last_name, age, gender FROM patient_records_with_age')
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