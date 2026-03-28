import os
import sqlite3

# Clean and fix database for alumni system
instance_path = 'alumni-tracking-system-master/instance'
db_path = os.path.join(instance_path, 'database.db')

if os.path.exists(db_path):
    os.remove(db_path)
    print('✅ Database cleaned')

print('Run: python alumni-tracking-system-master/app.py')
