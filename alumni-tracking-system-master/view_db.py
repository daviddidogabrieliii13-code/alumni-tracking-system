import sqlite3

# Connect to database
conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 50)
print("DATABASE: instance/database.db")
print("=" * 50)
print("\nTables in database:")
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  - {table_name}: {count} records")

print("\n" + "=" * 50)
print("DATA SUMMARY:")
print("=" * 50)

# Show users
cursor.execute("SELECT id, email, role FROM user")
users = cursor.fetchall()
print("\nUsers:")
for user in users:
    print(f"  ID: {user[0]}, Email: {user[1]}, Role: {user[2]}")

# Show alumni profiles
cursor.execute("SELECT id, first_name, last_name, degree, year_graduated, employment_status FROM alumni_profile")
alumni = cursor.fetchall()
print("\nAlumni Profiles:")
for a in alumni:
    print(f"  ID: {a[0]}, Name: {a[1]} {a[2]}, Degree: {a[3]}, Year: {a[4]}, Status: {a[5]}")

# Show jobs
cursor.execute("SELECT id, title, company, job_type FROM job")
jobs = cursor.fetchall()
print("\nJobs:")
for job in jobs:
    print(f"  ID: {job[0]}, Title: {job[1]}, Company: {job[2]}, Type: {job[3]}")

conn.close()
