import sqlite3

def test_database_creation(temp_db):
    """Test that the DB manager correctly creates files and schemas."""
    
    # 1. Action: Ask the fixture to create a new file
    success = temp_db.set_file("test_run")
    assert success is True
    
    # 2. Verify: Try to create it again, it should fail (file exists)
    success_again = temp_db.set_file("test_run")
    assert success_again is False

def test_database_insertion(temp_db):
    """Test that we can insert and read time-series data."""
    temp_db.set_file("sensor_data")
    
    # 1. Action: Insert mock data
    temp_db.insert_reading("2026-06-02T12:00:00", "Main_PSU", 1, "Voltage", 5.0)
    
    # 2. Verify: Query it directly with sqlite3
    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT * FROM readings")
    rows = cursor.fetchall()
    
    assert len(rows) == 1
    assert rows[0][1] == "Main_PSU"
    assert rows[0][4] == 5.0