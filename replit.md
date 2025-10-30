# Electronic Complaints System (نظام الشكاوى الإلكتروني)

## Overview
This project is an Arabic electronic complaints management system built with Flask (backend) and React (frontend). It enables traders to submit complaints and allows technical and higher committees to review them and generate reports. The system includes robust features such as user authentication with role-based access control, an annual subscription payment system with an admin review workflow, comprehensive complaint tracking, and advanced reporting capabilities including Excel/PDF export. Key ambitions include providing a streamlined, secure, and efficient platform for managing complaints in an Arabic-first environment, with a strong focus on data integrity, user experience, and administrative oversight.

## User Preferences
- Language: Arabic (RTL interface)
- Database: SQLite (pre-existing, preserved)

## Initial Setup Instructions

### First-Time Database Initialization
After importing the project, you **must** initialize the database with default roles and settings:

1. **Initialize the database with roles and categories:**
   ```bash
   cd complaints_backend && python init_db.py
   ```
   This creates:
   - 3 default roles: Trader, Technical Committee, Higher Committee
   - 5 complaint categories
   - 7 complaint statuses

2. **Initialize system settings and payment methods:**
   ```bash
   cd complaints_backend && python src/init_settings.py
   ```
   This creates:
   - Subscription pricing (default: 50000 YER/year)
   - Grace period settings
   - Payment methods (Yemen Mobile, MTN)

3. **Create the first admin account:**
   - Navigate to `/setup` in your browser
   - Fill in the form with:
     - **Username**: English letters and numbers only (e.g., `admin`)
     - **Email**: Valid email address
     - **Password**: Must meet all requirements:
       - 8 characters minimum
       - At least one uppercase letter (A-Z)
       - At least one lowercase letter (a-z)
       - At least one number (0-9)
       - At least one special character (!@#$%^&*)
     - **Full Name**: Can be in Arabic
     - **Phone** and **Address**: Optional
   - Example valid password: `Admin@123`

### Password Policy
The system enforces strict password requirements for security:
- Minimum 8 characters
- Must contain uppercase, lowercase, numbers, and special characters
- Cannot contain common patterns or sequential characters
- Cannot be a commonly used password

## System Architecture

### UI/UX Decisions
The frontend is built with React and Vite, utilizing Radix UI components and Tailwind CSS for styling, ensuring a modern and responsive user interface with full Arabic (RTL) support. 

**Enhanced Authentication Experience:**
- **Progressive Login Flow**: Multi-step authentication (username → password → OTP) with smooth transitions and visual feedback
- **Modern Setup Wizard**: 4-step guided setup with organization info, admin account creation, security preferences, and completion confirmation
- **Password Security**: Real-time password strength indicator, breach detection via HIBP API, sequential/repeated character detection, and cryptographically secure password generation
- **Smart User Feedback**: RTL-aware toast notifications with contextual icons, connection status indicators, and account lockout warnings
- **Session Management**: "Remember me" functionality, refresh token rotation, and automatic session expiry handling

### Technical Implementations
- **Backend**: Flask 3.1.1, SQLAlchemy ORM with SQLite, JWT for authentication, Flask-CORS, Gunicorn for production.
- **Frontend**: React 19.1.0, Vite 6.3.5, React Router DOM, Axios for HTTP requests, pnpm for package management.
- **Deployment**: Autoscale (stateless web application) using Gunicorn on port 5000, with frontend assets built and served statically by Flask.
- **Security**:
    - **Authentication**: JWT with dual access/refresh token system, refresh token rotation, and Redis-backed session management.
    - **Authorization**: Role-based access control (Trader, Technical Committee, Higher Committee).
    - **Input Validation**: Comprehensive Marshmallow-based validation for all API endpoints.
    - **Password Policy**: Strong password requirements, history checks, and Arabic error messages.
    - **Rate Limiting**: Redis-backed Flask-Limiter for various endpoints (login, password change, setup).
    - **Account Lockout**: Mechanism for locking accounts after multiple failed login attempts.
    - **Security Headers**: Injection of industry-standard security headers (e.g., X-Content-Type-Options, X-Frame-Options, CSP).
- **Payment & Subscription**:
    - Annual subscription model with configurable pricing, grace periods, and renewal reminders.
    - Admin review workflow for payment approvals/rejections.
    - Enforcement of active subscriptions for Trader access.
- **Notifications**:
    - Email and SMS notifications for critical events (e.g., payment approval, subscription expiry, complaint status changes).
    - Asynchronous processing via RQ (Redis Queue) with graceful degradation to synchronous execution.
    - Arabic RTL-formatted email templates.
- **Reporting & Analytics**:
    - Excel and PDF export capabilities with Arabic RTL support for complaints, payments, users, and subscriptions.
    - Automated PostgreSQL database backups with retention policies and optional S3 upload.
    - Advanced analytics endpoints providing dashboard metrics, complaint trends, subscription metrics, and payment summaries, cached with Redis.

### Feature Specifications
- User authentication and role-based authorization.
- Annual subscription payment system with admin approval.
- Complaint submission, tracking, and comment functionality.
- Report generation for various data types.
- Export of data to Excel and PDF formats, supporting Arabic RTL.
- Automated database backups.
- Advanced analytics and reporting dashboards.
- Background notification system via email and SMS.
- Admin-only user creation (self-registration is disabled).
- Initial setup wizard for first-time administration.

**Recent Enhancements (October 2025):**
1. **PWA Support**: Progressive Web App capabilities with service worker, offline support, and installable experience
2. **Enhanced Subscription Management**:
   - Real-time subscription countdown banner with expiry warnings
   - Grace period enforcement (7-day default)
   - Comprehensive admin subscription panel with filtering and extension capabilities
3. **Advanced Analytics Dashboard**:
   - Interactive charts using Recharts (complaints by status, category, timeline)
   - Revenue tracking and monthly trend analysis
   - Resolution time statistics and performance metrics
   - Admin-only dashboard with KPIs and visualizations
4. **Security Enhancements**:
   - Two-Factor Authentication (2FA) with QR code setup for admin users
   - Comprehensive security event logging and monitoring
   - Real-time security statistics dashboard
5. **Comprehensive Audit Log**:
   - Full audit trail with advanced filtering (action type, user, date range)
   - Pagination support for large datasets
   - CSV export functionality for compliance and reporting

### System Design Choices
- **Modularity**: Separation of concerns between backend (Flask) and frontend (React).
- **Scalability**: Stateless backend design for autoscale deployment, asynchronous task processing with Redis.
- **Internationalization**: Full Arabic language support with RTL layouts for both UI and generated documents (Excel, PDF, Emails).
- **Resilience**: Graceful degradation for Redis-dependent features if Redis is unavailable (though not recommended for production).

## External Dependencies

- **Database**: SQLite (local development), PostgreSQL (production for automated backups).
- **Redis**: Used for caching analytics, JWT refresh token storage, session management, rate limiting, and background job queuing (RQ).
- **Twilio**: For SMS notifications.
- **Flask-Mail**: For email notifications.
- **WeasyPrint**: For PDF generation.
- **Pandas, Openpyxl**: For Excel data manipulation and generation.
- **Arabic-reshaper, Python-bidi**: For proper Arabic RTL text rendering in documents and notifications.
- **Matplotlib, Plotly**: For chart generation in reports.
- **Gunicorn**: Production WSGI HTTP server for Flask.
- **Axios**: HTTP client for frontend-backend communication.
- **Radix UI**: Frontend UI components.
- **Tailwind CSS**: Utility-first CSS framework for styling.
- **Recharts**: Interactive charting library for admin analytics dashboard.
- **PyOTP**: Python One-Time Password library for 2FA implementation.
- **QRCode**: QR code generation for 2FA setup.

## Recent API Additions (October 2025)

### Subscription Management APIs
- `GET /api/subscriptions/user/{user_id}/status` - Get user subscription status with days remaining
- `GET /api/subscriptions/admin/all` - Admin endpoint to view all subscriptions
- `POST /api/subscriptions/admin/{id}/extend` - Extend subscription by specified months
- `GET /api/subscriptions/check-access/{user_id}` - Check subscription access with grace period logic
- `GET /api/subscriptions/admin/stats` - Subscription statistics for admin dashboard

### Analytics APIs
- `GET /api/analytics/dashboard/summary` - Dashboard KPIs (complaints, users, revenue, resolution time)
- `GET /api/analytics/complaints/by-status` - Complaints distribution by status
- `GET /api/analytics/complaints/by-category` - Complaints distribution by category
- `GET /api/analytics/complaints/timeline` - 6-month complaint submission timeline
- `GET /api/analytics/revenue/monthly` - Monthly revenue trends
- `GET /api/analytics/performance/resolution-time` - Resolution time statistics and distribution

### Security APIs
- `POST /api/security/2fa/setup` - Generate 2FA QR code and secret
- `POST /api/security/2fa/enable` - Enable 2FA with verification code
- `POST /api/security/2fa/disable` - Disable 2FA (requires password)
- `GET /api/security/audit-log` - Comprehensive audit log with filtering and pagination
- `GET /api/security/security-events` - Recent security events (logins, 2FA, password changes)
- `GET /api/security/stats` - Security statistics (login attempts, 2FA adoption, etc.)