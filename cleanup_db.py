import sqlite3

# Connect to database
conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

# First, let's see all users
cursor.execute("SELECT id, email, role FROM user")
users = cursor.fetchall()
print("All Users:")
for u in users:
    print(f"  ID {u[0]}: {u[1]} (Role: {u[2]})")

print("\n--- DELETING SAMPLE ALUMNI ---")

# Delete sample alumni (keep admin ID 1 and user ID 10 which is David's)
# IDs 2-9 are sample data to delete
sample_user_ids = [2, 3, 4, 5, 6, 7, 8, 9]

for user_id in sample_user_ids:
    # Delete alumni profile first
    cursor.execute("DELETE FROM alumni_profile WHERE user_id = ?", (user_id,))
    # Delete user
    cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
    print(f"Deleted user ID: {user_id}")

conn.commit()

# Verify
cursor.execute("SELECT id, email, role FROM user")
users = cursor.fetchall()
print("\nRemaining Users:")
for u in users:
    print(f"  ID {u[0]}: {u[1]} (Role: {u[2]})")

cursor.execute("SELECT COUNT(*) FROM alumni_profile")
print(f"\nTotal Alumni Profiles: {cursor.fetchone()[0]}")

conn.close()
print("\n✓ Database cleaned! Only your account remains.")
