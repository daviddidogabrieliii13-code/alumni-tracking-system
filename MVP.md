# MVP DOCUMENTATION
# Online Alumni Tracking & Graduate Tracer Study System

================================================================================
                           MVP FEATURES (PHASE 1)
================================================================================

1. USER AUTHENTICATION
   - User Registration (email, password, name, degree, year graduated)
   - Secure Login with session management
   - Logout functionality
   - Role-based access (Alumni, Admin, Registrar, OSA)
   - Password hashing with werkzeug.security

2. ALUMNI PROFILE MANAGEMENT
   - Personal Information (name, gender, DOB, phone, address, photo)
   - Educational Background (degree, year graduated, student ID, honors)
   - Employment Information (employer, position, status, salary, location)
   - Additional Details (skills, certifications, volunteer work)
   - Profile photo upload capability

3. GRADUATE TRACER SURVEY
   - Educational Experience ratings (1-5)
   - Curriculum Relevance assessment
   - Facilities Rating
   - Instructor Quality evaluation
   - Research Opportunities
   - Competency Assessment (technical, soft, problem-solving, communication, leadership)
   - Employment Status tracking
   - Overall Satisfaction rating
   - Recommendation rating (1-10)
   - Suggestions/Feedback text area

4. BASIC ANALYTICS DASHBOARD (Admin)
   - Total Alumni count
   - Employment Rate calculation
   - Survey Response Rate
   - Charts: Employment distribution, Graduates by year, Degree distribution
   - Survey Average Ratings

5. ALUMNI DIRECTORY
   - Public searchable directory
   - Search by name, degree, employer
   - Filter by degree and graduation year
   - Pagination support

6. JOB BOARD
   - Job listings with details
   - Filter by job type and location
   - Job details page
   - Apply link capability

7. EVENTS CALENDAR
   - Upcoming events display
   - Event types: gathering, career_fair, workshop, reunion
   - Event details with RSVP capability

================================================================================
                        ADDITIONAL USER ROLES
================================================================================

REGISTRAR ROLE:
- Manage alumni records
- Verify alumni information
- Access to registration management
- Email: registrar@wvsu.edu.ph

OSA (Office of Student Affairs) ROLE:
- Student activity tracking
- Manage student records
- Activity management
- Email: osa@wvsu.edu.ph

================================================================================
                        CUSTOM BACKGROUND IMAGE
================================================================================

To add your custom background image:

1. Place your image in: static/images/
2. Update config.py:
   - USE_CUSTOM_BACKGROUND = True
   - CUSTOM_BACKGROUND = 'images/your-image.jpg'
   - BACKGROUND_OPACITY = 0.15 (adjust as needed)

================================================================================
                        MO Moscow Framework ASCII
================================================================================

        +------------------------------------------------------------------+
        |                                                                  |
        |                    MO SCOPE MODEL FRAMEWORK                       |
        |                                                                  |
        +------------------------------------------------------------------+
        |                                                                  |
        |  +-------------+    +-------------+    +-------------+         |
        |  |   MUST      |    |   SHOULD    |    |   COULD     |         |
        |  |   HAVE      |    |   HAVE      |    |   HAVE      |         |
        |  +-------------+    +-------------+    +-------------+         |
        |  | - Auth      |    | - API       |    | - Mobile    |         |
        |  | - Profile   |    | - Export    |    |   App       |         |
        |  | - Survey    |    | - Email     |    | - AI        |         |
        |  | - Analytics |    | - Notifs    |    |   Matching  |         |
        |  | - Directory |    | - Verify    |    | - Chatbot   |         |
        |  | - Jobs      |    |             |    |             |         |
        |  | - Events    |    |             |    |             |         |
        |  +-------------+    +-------------+    +-------------+         |
        |                                                                  |
        +------------------------------------------------------------------+

        +------------------------------------------------------------------+
        |                       SYSTEM ARCHITECTURE                         |
        +------------------------------------------------------------------+
        |                                                                  |
        |  +----------------------------------------------------------+    |
        |  |                    FRONTEND (UI)                        |    |
        |  |  +----------+ +----------+ +----------+ +----------+      |    |
        |  |  |  HTML5   | |  CSS3    | |  JS ES6  | |Chart.js  |      |    |
        |  |  +----------+ +----------+ +----------+ +----------+      |    |
        |  +----------------------------------------------------------+    |
        |                              |                                    |
        |                              v                                    |
        |  +----------------------------------------------------------+    |
        |  |                    BACKEND (API)                         |    |
        |  |  +----------+ +----------+ +----------+ +----------+      |    |
        |  |  |  Flask   | | SQLAlchemy| |Flask-    | |Werkzeug  |      |    |
        |  |  |          | |          | |Login     | |Security  |      |    |
        |  |  +----------+ +----------+ +----------+ +----------+      |    |
        |  +----------------------------------------------------------+    |
        |                              |                                    |
        |                              v                                    |
        |  +----------------------------------------------------------+    |
        |  |                     DATABASE                              |    |
        |  |  +--------------------------------------------------+     |    |
        |  |  |              SQLite (database.db)                 |     |    |
        |  |  |  - Users Table                                    |     |    |
        |  |  |  - Alumni Profile Table                           |     |    |
        |  |  |  - Survey Response Table                          |     |    |
        |  |  |  - Jobs Table                                     |     |    |
        |  |  |  - Events Table                                   |     |    |
        |  |  +--------------------------------------------------+     |    |
        |  +----------------------------------------------------------+    |
        |                                                                  |
        +------------------------------------------------------------------+

        +------------------------------------------------------------------+
        |                         MVP PRIORITY MATRIX                       |
        +------------------------------------------------------------------+
        |                                                                  |
        |  Feature              | Priority | Status  | Complexity |        |
        |  --------------------|----------|---------|------------|        |
        |  User Auth           | MUST     | DONE    | LOW        |        |
        |  Profile Mgmt        | MUST     | DONE    | MEDIUM     |        |
        |  Graduate Survey     | MUST     | DONE    | MEDIUM     |        |
        |  Analytics           | MUST     | DONE    | MEDIUM     |        |
        |  Alumni Directory    | MUST     | DONE    | LOW        |        |
        |  Job Board           | MUST     | DONE    | LOW        |        |
        |  Events Calendar     | MUST     | DONE    | LOW        |        |
        |  Registrar Role      | SHOULD   | PENDING | MEDIUM     |        |
        |  OSA Role           | SHOULD   | PENDING | MEDIUM     |        |
        |  Email Notifs       | SHOULD   | PENDING | LOW        |        |
        |  API Development    | COULD    | PENDING | HIGH       |        |
        |  Export to PDF      | COULD    | PENDING | MEDIUM     |        |
        |  Mobile App         | WONT     | PLANNED | HIGH       |        |
        |                                                                  |
        +------------------------------------------------------------------+

================================================================================
                           CONTACT & SUPPORT
================================================================================

For issues or questions:
- Email: alumni@wvsu.edu.ph
- Phone: (033) 123-4567
- Address: WVSU Pototan Campus, Iloilo, Philippines

Admin Login:
- Email: admin@wvsu.edu.ph
- Password: admin123

================================================================================
