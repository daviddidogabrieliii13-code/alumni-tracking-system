# WVSU Alumni Tracking System - Empty Database Ready

## Status
✅ Database emptied (only admin user ID=1 remains)
✅ Server runs: `cd alumni-tracking-system-master && python app.py`
✅ Homepage loads at http://localhost:5000
✅ Register new alumni: /register → /verify-otp (OTP: 123456)
✅ Admin login: admin@wvsu.edu.ph / admin123 → admin dashboard
✅ Role dashboards: alumni, admin, director, registrar, osa

## Run Commands (PowerShell)
```
cd alumni-tracking-system-master
python cleanup_db.py  # Already done - empties non-admin data
python app.py         # Starts server
```

## Test Flow
1. Visit http://localhost:5000
2. Click Register
3. Fill form → Submit → OTP screen shows 123456
4. Enter 123456 → Login page
5. Login with new credentials → Alumni Dashboard

Database is empty as requested!
