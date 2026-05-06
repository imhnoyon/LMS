# EduHub API

A comprehensive Django REST Framework backend for an online learning management system. EduHub provides a scalable, feature-rich platform for instructors to create and manage courses, handle payments, and track student progress.

## 🚀 Features

### Core Learning Platform
- **Course Management** - Create, publish, and manage courses with detailed structure
- **Instructor Dashboard** - Complete control over courses, earnings, and student engagement
- **Student Enrollment** - Flexible enrollment system with progress tracking
- **Live Classes** - Schedule and conduct live sessions via Google Meet or Zoom
- **Certificates** - Auto-generate certificates for course completion

### Content Management
- **Lecture System** - Upload videos, attachments, and lecture notes
- **Quiz & Assessments** - Create quizzes with multiple question types
- **Sections & Structure** - Organize courses into logical sections
- **Course Reviews** - Student ratings and feedback system

### Payments & Revenue
- **Stripe Integration** - Secure payment processing
- **Commission Management** - Track instructor earnings and withdrawals
- **Invoice System** - Automated invoice generation for orders
- **Financial Analytics** - Revenue charts and earnings reports

### Communication & Engagement
- **Real-time Messaging** - WebSocket-based instructor-student messaging
- **Notifications** - Email and in-app notifications
- **Student Analytics** - Track enrollments, completions, and engagement metrics

### Organization Features
- **Multi-level Accounts** - Support for individual and organization instructors
- **Team Management** - Organization membership and role management
- **Affiliate System** - Commission tracking and affiliate management

### Administrative
- **Instructor Approval Workflow** - Review and approve instructor applications
- **User Management** - Role-based access control (Admin, Instructor, Student)
- **Content Moderation** - Manage course status and featured content

## 🛠 Tech Stack

### Backend
- **Django 3.2+** - Python web framework
- **Django REST Framework** - RESTful API development
- **PostgreSQL/SQLite** - Database
- **Celery** - Asynchronous task queue
- **Redis** - Caching and real-time features

### Payment & Integration
- **Stripe** - Payment processing
- **Django-Cors-Headers** - CORS handling
- **Python-Decouple** - Environment configuration

### Real-time Communication
- **Django Channels** - WebSocket support for messaging
- **Daphne** - ASGI server

### Email & Notifications
- **Django-Email** - Email handling
- **Custom Email Templates** - Branded email communications

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL (or SQLite for development)
- Redis (for caching and real-time features)
- Stripe account (for payment processing)

## 🔧 Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd backend
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the project root:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/eduhub
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLIC_KEY=pk_test_xxxxx
REDIS_URL=redis://localhost:6379/0
EMAIL_HOST_PASSWORD=your-email-password
```

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Create superuser
```bash
python manage.py createsuperuser
```

### 7. Collect static files
```bash
python manage.py collectstatic --noinput
```

### 8. Run development server
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/`

## 📁 Project Structure

```
backend/
├── apps/
│   ├── affiliates/           # Affiliate management
│   ├── analytics/            # Analytics and reporting
│   ├── core/                 # Core functionality
│   ├── courses/              # Course management
│   ├── enrollments/          # Student enrollments
│   ├── instructors/          # Instructor profiles
│   ├── messaging/            # Real-time messaging
│   ├── notifications/        # Notification system
│   ├── orders/               # Order management
│   ├── organizations/        # Organization features
│   ├── payments/             # Payment processing
│   ├── students/             # Student profiles
│   └── users/                # User authentication
├── config/                   # Django settings
├── media/                    # User uploads
├── static/                   # Static assets
├── templates/                # Email templates
├── utils/                    # Utility functions
├── manage.py                 # Django management
└── requirements.txt          # Python dependencies
```

## 🔌 API Endpoints Overview

### Authentication
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/logout/` - User logout
- `POST /api/v1/auth/refresh/` - Refresh token

### Instructors
- `GET /api/v1/instructors/instructor/me/` - Get current instructor profile
- `PATCH /api/v1/instructors/instructor/me/` - Update instructor profile
- `GET /api/v1/instructors/pending/` - List pending instructor approvals (Admin)
- `PATCH /api/v1/instructors/{id}/approve/` - Approve instructor (Admin)

### Courses
- `GET /api/v1/courses/` - List courses
- `POST /api/v1/courses/` - Create course
- `GET /api/v1/courses/{id}/` - Get course details
- `PUT /api/v1/courses/{id}/` - Update course
- `DELETE /api/v1/courses/{id}/` - Delete course

### Enrollments
- `GET /api/v1/enrollments/` - List student enrollments
- `POST /api/v1/enrollments/` - Enroll in course
- `GET /api/v1/enrollments/{id}/progress/` - Get enrollment progress

### Payments
- `POST /api/v1/payments/process/` - Process payment
- `GET /api/v1/payments/invoices/` - List invoices
- `GET /api/v1/earnings/` - Get instructor earnings

### Messaging
- `GET /api/v1/messages/` - List messages
- `POST /api/v1/messages/` - Send message
- WebSocket: `ws://localhost:8000/ws/messages/{room_name}/` - Real-time messaging

## ⚙️ Configuration

### Database Setup
```bash
# PostgreSQL (Recommended for production)
DATABASE_URL=postgresql://user:password@localhost:5432/eduhub

# SQLite (Development only)
DATABASE_URL=sqlite:///db.sqlite3
```

### Stripe Configuration
1. Get API keys from [Stripe Dashboard](https://dashboard.stripe.com/)
2. Add to `.env`:
```env
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLIC_KEY=pk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

### Email Configuration
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
```

### Redis Configuration
```env
REDIS_URL=redis://localhost:6379/0
CACHE_TIMEOUT=300
```

## 🚀 Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Using Docker
```bash
docker build -t eduhub-api .
docker run -p 8000:8000 eduhub-api
```

### Environment for Production
```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 📊 API Response Format

### Success Response
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "id": 1,
    "name": "Example"
  }
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error message",
  "errors": {
    "field_name": ["Error detail"]
  }
}
```

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication:

```bash
# Get token
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Use token in requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/instructors/instructor/me/
```

## 📝 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/api/schema/swagger/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Coding Standards
- Follow PEP 8 conventions
- Write meaningful commit messages
- Add docstrings to functions and classes
- Create tests for new features

## 🐛 Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
psql -U postgres

# Reset migrations (development only)
python manage.py migrate zero
python manage.py migrate
```

### Static Files Not Loading
```bash
python manage.py collectstatic --clear --noinput
```

### Redis Connection Error
```bash
# Verify Redis is running
redis-cli ping
```

### Stripe Integration Issues
- Verify API keys in `.env`
- Check webhook endpoint in Stripe Dashboard
- Review Stripe API logs for detailed errors

## 📞 Support

For support, email: mahedi.dev2002@gmail.com or open an issue on GitHub.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Django and Django REST Framework communities
- Stripe for payment processing
- All contributors and users

## 📈 Roadmap

- [ ] Mobile app integration
- [ ] Advanced analytics dashboard
- [ ] AI-powered course recommendations
- [ ] Gamification features
- [ ] Certificate blockchain verification
- [ ] Multi-language support
- [ ] Advanced video player with adaptive bitrate streaming

---

**Last Updated**: May 2026


