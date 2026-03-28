# MVP DOCUMENTATION
# Online Alumni Tracking & Graduate Tracer Study System
# Detailed MoSCoW Framework - Print-Optimized (Monospace Recommended)
# Generated: Current Date | Version: 2.0 | Status: Implemented Core MVP

================================================================================
TABLE OF CONTENTS
================================================================================
1. EXECUTIVE SUMMARY ...................................................... 2
2. MOSCOW PRIORITIZATION ................................................... 3
3. FEATURE DETAILS ......................................................... 10
4. SYSTEM ARCHITECTURE .................................................... 20
5. DEPLOYMENT & SUPPORT ................................................... 22

================================================================================
1. EXECUTIVE SUMMARY
================================================================================
The Online Alumni Tracking & Graduate Tracer Study System is a Flask/SQLite web application for tracking
alumni profiles, graduate tracer surveys, employment status, jobs, events, and
analytics. Core MVP (Must/Should) is fully implemented. This MoSCoW details
prioritization for development/expansion.

TECHNOLOGY STACK:
- Backend: Flask 3.0, SQLAlchemy 2.0
- Frontend: HTML5/CSS3/JS/Chart.js
- Database: SQLite (production-ready)
- Security: Flask-Login, Werkzeug, OTP
- Reports: ReportLab (PDF), Pandas/OpenPyXL (Excel)

================================================================================
2. MOSCOW PRIORITIZATION FRAMEWORK
================================================================================

MUST HAVE (Core MVP - Release 1.0 - IMPLEMENTED)
│ Feature │ Description │ Status │ Effort │ Dependencies │
│---------│-------------│--------│--------│--------------│
│ User Auth │ Registration/Login/OTP/Logout/ │ DONE │ Low │ Flask-Login │
│ │ Roles (5 types)/Password Reset │ │ │ Werkzeug │
│ Profile Mgmt │ CRUD personal/edu/employment/ │ DONE │ Medium │ Models/User │
│ │ skills/photo upload/completion │ │ │ Uploads │
│ Tracer Survey │ Full graduate tracer form (20+ │ DONE │ Medium │ Survey Model │
│ │ fields: ratings/employment/feedback) │ │ │ Analytics │
│ Admin Analytics │ Dashboard stats/charts (employment│ DONE │ Medium │ Chart.js/DB │
│ │ rate/survey avg/grad year distro) │ │ │ Queries │
│ Alumni Directory │ Search/filter/paginate profiles │ DONE │ Low │ DB Index │
│ Job Board │ List/filter/detail jobs (CRUD admin) │ DONE │ Low │ Job Model │
│ Events Calendar │ List/RSVP events (CRUD admin) │ DONE │ Low │ Event Model │

SHOULD HAVE (Phase 2 - High Value - PENDING)
│ Feature │ Description │ Status │ Effort │ Dependencies │
│---------│-------------│--------│--------│--------------│
│ Role Dashboards │ Registrar verify/OSA activities/ │ PENDING │ Medium │ Role Logic │
│ │ Director analytics view │ │ │ Templates │
│ PDF/Excel Export │ Surveys/profiles/directories to │ PENDING │ Medium │ ReportLab/ │
│ │ printable formats │ │ │ Pandas │
│ Email Notifications │ OTP/Reset/Events/Jobs via SMTP │ PENDING │ Low │ Flask-Mail │
│ Advanced Search │ Full-text/multi-field with facets │ PENDING │ Medium │ DB Indexes/ │
│ │ (skills/location/year) │ │ │ JS │

COULD HAVE (Phase 3 - Nice to Have - PLANNED)
│ Feature │ Description │ Status │ Effort │ Dependencies │
│---------│-------------│--------│--------│--------------│
│ REST API │ JSON endpoints for profiles/surveys │ PLANNED │ High │ Flask-RESTful │
│ Mobile Responsive │ Bootstrap/tailwind for phones │ PLANNED │ Low │ CSS/JS │
│ Real-time Notifs │ WebSockets for events/jobs │ PLANNED │ High │ Socket.io │
│ AI Insights │ Employment trend predictions │ PLANNED │ High │ ML libs │

WON'T HAVE (Future/Out of Scope v2.0)
│ Feature │ Description │ Status │ Effort │ Rationale │
│---------│-------------│--------│--------│-----------│
│ Mobile App │ Native iOS/Android │ DEFERRED │ High │ Web-first │
│ Payments │ Job posting fees │ DEFERRED │ High │ Non-core │
│ OAuth │ Google/FB login │ DEFERRED │ Medium │ Email suff. │
│ Blockchain │ Cert verification │ DEFERRED │ Extreme │ Overkill │

================================================================================
3. FEATURE DETAILS (Must-Have Only for MVP)
================================================================================
USER AUTHENTICATION:
- Fields: email, password, role enum (alumni/admin/etc.)
- Flow: Register → OTP(123456 dev) → Login → Role dashboard
- Security: Hashing, sessions, IP logs (SystemLog model)

ALUMNI PROFILE (20+ Fields):
Personal: name/gender/DOB/phone/address/photo
Edu: student_id/degree/year_grad/honors/activities
Employment: status/employer/position/salary/location/desc
Skills: skills/certs/volunteer

TRACER SURVEY (Competency Matrix):
Edu ratings (1-5): quality/curriculum/facilities/instructors/research
Skills (1-5): tech/soft/problem/comm/leadership
Employment: status/related/sector/searching
Satisfaction: overall(1-5)/recommend(1-10)/suggestions

================================================================================
4. SYSTEM ARCHITECTURE (ASCII Diagram)
================================================================================
+------------------------------------+  
|        BROWSER (localhost:5000)    |  
| HTML/CSS/JS + Chart.js             |  
+------------------------------------+  
               | REST/HTML  
               v  
+------------------------------------+  
|       FLASK APP (app.py)           |  
| SQLAlchemy + Flask-Login + Patches |  
+------------------------------------+  
               | ORM  
               v  
+------------------------------------+  
|     SQLITE DB (instance/database.db) |  
| Users/Profiles/Surveys/Jobs/Events |  
+------------------------------------+  

================================================================================
5. DEPLOYMENT & SUPPORT
================================================================================
RUN DEV:
cd alumni-tracking-system-master
python app.py

ADMIN: admin@wvsu.edu.ph / admin123
REGISTER: /register → OTP:123456

PRINT THIS DOC: Use monospace (Courier New, 10pt), landscape, no margins.

CONTACT: alumni@wvsu.edu.ph | (033) 123-4567 | WVSU Pototan Campus

================================================================================
END OF SPECIFICATION
================================================================================
