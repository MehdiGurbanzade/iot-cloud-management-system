import mysql.connector
import os
import time


def init_db():
    db_host = os.getenv("MYSQL_HOST")
    db_user = os.getenv("MYSQL_USER")
    db_pass = os.getenv("MYSQL_PASSWORD")
    db_name = os.getenv("MYSQL_DB")

    print("Waiting for MySQL to start...")
    connection = None
    for i in range(30):
        try:
            connection = mysql.connector.connect(
                host=db_host,
                user=db_user,
                password=db_pass,
                database=db_name
            )
            if connection.is_connected():
                print("Connected to MySQL!")
                break
        except Exception as e:
            print(f"Waiting... ({e})")
            time.sleep(2)

    if not connection or not connection.is_connected():
        print("Could not connect to MySQL. Exiting.")
        return

    cursor = connection.cursor()

    # Device registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        device_name VARCHAR(255) NOT NULL,
        location VARCHAR(255) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE
    )
    """)
    print("Table 'devices' ensured.")

    # Telemetry history (replaces MongoDB)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor_readings (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        device_id VARCHAR(255) NOT NULL,
        temperature FLOAT NOT NULL,
        humidity FLOAT NOT NULL,
        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_device_time (device_id, timestamp)
    )
    """)
    print("Table 'sensor_readings' ensured.")

    # room names
    devices = [
        ("Sensor-001", "Server Room A (Main)", True),     # server room (must be cold)
        ("Sensor-002", "Cold Storage Unit 4", True),      # storage for medicines and drugs
        ("Sensor-003", "Warehouse Logistics Zone", True), # logistic zone
        ("Sensor-004", "Backup Generator Room", True)     # back room
    ]

    insert_query = """
    INSERT INTO devices (device_name, location, is_active)
    SELECT %s, %s, %s WHERE NOT EXISTS (
        SELECT * FROM devices WHERE device_name = %s
    )
    """

    for dev in devices:
        cursor.execute(insert_query, (dev[0], dev[1], dev[2], dev[0]))

    connection.commit()
    print("Industrial devices inserted successfully.")

    cursor.close()
    connection.close()


if __name__ == "__main__":
    init_db()
