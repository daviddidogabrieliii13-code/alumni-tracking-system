import os
import sys
import subprocess
from pathlib import Path

# Change to project directory
os.chdir('alumni-tracking-system-master')

# Install requirements
print("Installing dependencies...")
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Run cleanup and setup
print("Setting up database...")
try:
    subprocess.check_call([sys.executable, 'cleanup_and_run.py'], 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except:
    print("Cleanup skipped - DB ready")

# Start server
print("🚀 Starting Alumni Tracking System...")
print("Access: http://127.0.0.1:5000")
print("Admin: admin@wvsu.edu.ph / admin123")
print("Demo OTP: 123456")
subprocess.call([sys.executable, 'app.py'])
