# From-Cert API

From-Cert API is a modular Django REST Framework backend for a learning platform with course management, payments, live classes, organization workflows, affiliate tracking, real-time messaging, and AI-assisted content creation.

## Overview

The backend is split into domain-focused apps. Each app owns its own URL group under `/api/v1/`, which keeps the API surface predictable and easy to maintain. The system supports:

- Admin workflows for approvals, moderation, analytics, contacts, FAQs, and user control.
- Instructor workflows for course authoring, live classes, earnings, certificates, and profiles.
- Student workflows for enrollment, course consumption, quizzes, reviews, certificates, and purchase history.
- Organization and affiliate workflows for contracts, referrals, revenue, and partner management.
- Messaging and notifications for platform communication.
- AI-powered tools for course structure, lesson drafting, quiz generation, content improvement, and learning objectives.

## Platform Features

- JWT-based authentication and password recovery.
- Custom user model with role-based access patterns.
- Course creation with categories, basic information, advanced metadata, sections, lectures, quizzes, and publishing.
- Student course player with lecture completion tracking and quiz submissions.
- Certificate generation tied to course completion.
- Stripe checkout, webhook handling, connect accounts, dashboard links, and withdrawal requests.
- Organization onboarding, invitations, contracts, analytics, and earnings dashboards.
- Affiliate referral links, click tracking, wallet, and commission management.
- Real-time conversation messaging over Django Channels.
- Admin configuration for contact submissions, FAQs, and site settings.
- Debug-only Swagger and ReDoc documentation.

## Tech Stack

- Django
- Django REST Framework
- Django Channels
- Daphne
- drf-yasg
- `rest_framework_simplejwt`
- `corsheaders`
- Stripe

## Project Layout

```text
backend/
├── apps/
│   ├── affiliates/      # Affiliate commissions, referral links, wallets
│   ├── analytics/       # AI course helper endpoints
│   ├── core/            # Contact forms, FAQs, site config
│   ├── courses/         # Course authoring, curriculum, live classes
│   ├── enrollments/     # Enrollment and certificate domain logic
│   ├── instructors/     # Instructor dashboard, approvals, earnings
│   ├── messaging/       # Conversations, messages, websocket routing
│   ├── notifications/   # Notification APIs
│   ├── orders/          # Cart, checkout, wishlist
│   ├── organizations/   # Organization dashboards, contracts, analytics
│   ├── payments/        # Stripe checkout, connect, withdrawals
│   ├── students/        # Student dashboard, reviews, certificates
│   └── users/           # Authentication and admin user tools
├── config/              # Settings, URL routing, ASGI/WSGI
├── LearnHub_AI/         # Optional Streamlit AI teaching assistant
├── media/               # Uploaded assets
├── static/              # Static assets
├── templates/           # HTML templates and email templates
├── utils/               # Shared helper utilities
└── manage.py
```

## API Architecture

All backend REST APIs are mounted under `/api/v1/`:

- `/api/v1/core/`
- `/api/v1/users/`
- `/api/v1/courses/`
- `/api/v1/affiliates/`
- `/api/v1/analytics/`
- `/api/v1/payments/`
- `/api/v1/notifications/`
- `/api/v1/enrollments/`
- `/api/v1/orders/`
- `/api/v1/messaging/`
- `/api/v1/instructors/`
- `/api/v1/organizations/`
- `/api/v1/students/`

Documentation and realtime endpoints:

- `/swagger/`
- `/redoc/`
- `/swagger.json`
- `/ws/messaging/conversations/<conversation_id>/`

## API Reference

### Core Module

Base path: `/api/v1/core/`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/contact/` | List contact messages |
| POST | `/contact/submit/` | Submit contact form |
| GET | `/contact/<pk>/` | Contact detail |
| PATCH/PUT | `/contact/<pk>/status/` | Update contact status |
| GET | `/faq/categories/` | List FAQ categories |
| POST | `/faq/categories/create/` | Create FAQ category |
| GET | `/faq/categories/<pk>/` | FAQ category detail |
| GET | `/faq/` | List FAQs |
| POST | `/faq/create/` | Create FAQ |
| GET | `/faq/<pk>/` | FAQ detail |
| GET | `/site-config/` | Get site config |
| POST | `/site-config/create/` | Create site config |
| PATCH/PUT | `/site-config/update/` | Update site config |

### Users Module

Base path: `/api/v1/users/`

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/register/` | Register user |
| POST | `/verify-email/` | Verify email |
| POST | `/login/` | Sign in |
| POST | `/resend-verification/` | Resend verification code |
| POST | `/forgot-password/` | Start password reset |
| POST | `/verify-reset-code/` | Verify reset code |
| POST | `/reset-password/` | Reset password |
| POST | `/refresh-token/` | Refresh JWT token |
| GET | `/users/` | Admin user list |
| GET | `/users/<uuid:pk>/` | Admin user detail |
| POST | `/send-email/` | Send email |
| PATCH/PUT | `/block/<uuid:pk>/` | Block or unblock user |
| GET | `/admin/dashboard-data/` | Admin dashboard data |
| GET | `/admin/payments/` | Admin payments dashboard |
| GET | `/admin/analytics/` | Admin analytics data |
| PATCH/PUT | `/admin/profile/update/` | Update admin profile |

### Courses Module

Base path: `/api/v1/courses/`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET/POST | `/categories/` | Manage categories |
| GET | `/courses-list/` | Course list |
| GET | `/courses-lists/` | Alternate course list |
| GET | `/courses-list/<pk>/` | Course detail |
| GET | `/coursesAdmin/review-history/` | Admin review history |
| PATCH/PUT | `/course-block-unblock/<pk>/` | Block or unblock course |
| GET | `/courses-list-instructor/` | Instructor course list |
| POST | `/courses/` | Create course basic info |
| GET/PUT/PATCH | `/courses/<pk>/` | Read or update course basic info |
| PATCH/PUT | `/courses/advance-info/<pk>/` | Update advanced info |
| GET/POST | `/courses/sections/<pk>/` | Course sections |
| GET/POST | `/courses/<pk>/sections/<section_id>/` | Specific section |
| GET/POST | `/sections/lectures/<section_id>/` | Lectures in a section |
| GET/POST | `/sections/lectures/<section_id>/<lecture_id>/` | Specific lecture |
| GET/POST | `/sections/quizzes/<section_id>/` | Quizzes in a section |
| GET/POST | `/sections/quizzes/<section_id>/<quiz_id>/` | Specific quiz |
| POST | `/courses/publish/<pk>/` | Publish course |
| GET | `/courses/<course_id>/overview/` | Course overview |
| GET | `/live-classes/stats/` | Live class stats |
| GET/POST/PATCH | `/live-classes/<course_id>/` | Manage live classes |
| POST | `/joint-class/<id>/` | Mark attendance |
| GET | `/home/courses/` | Student home courses |
| GET | `/home/courses/list/` | Alternate student home list |
| GET | `/course/info/` | Course info |
| GET/POST | `/lectures/comments/` | Lecture comments |
| GET/POST | `/lectures/comments/<lecture_id>/` | Lecture comments by lecture |
| GET | `/my-courses/<pk>/` | Instructor course details |
| GET | `/courses/<course_id>/sections/` | Sections by course |
| GET | `/organizations/courses/reviews/` | Organization course reviews |
| GET/POST/PATCH | `/courses/<course_id>/live-classes/` | Live classes for a course |
| GET/POST/PATCH | `/live-classes/deshboard/` | Contract-assigned live classes |

### Affiliates Module

Base path: `/api/v1/affiliates/`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/affiliates/` | Affiliate list |
| PATCH/PUT | `/affiliates/status/<pk>/` | Update affiliate status |
| DELETE | `/delete-affiliate/<pk>/` | Delete affiliate |
| GET | `/affiliate/courses/` | Affiliate course list |
| POST | `/generate-course-referral-link/<course_id>/` | Generate referral link |
| POST | `/track-referral-click/` | Track referral click |
| GET | `/affiliate/dashboard/` | Affiliate dashboard |
| GET | `/affiliate/main-dashboard/` | Main affiliate dashboard |
| GET | `/affiliate/wallet/` | Affiliate wallet |
| GET | `/affiliate/withdrawal-requests-list/` | Withdrawal requests |
| GET | `/affiliate/profile/` | Affiliate profile |
| GET | `/affiliate/overview/` | Affiliate overview |
| PATCH/PUT | `/affiliate/block/<pk>/` | Block affiliate |
| PATCH/PUT | `/affiliate/update-commission/<pk>/` | Update commission rate |
| GET | `/affiliate/details/<pk>/` | Affiliate details |

### Analytics Module

Base path: `/api/v1/analytics/`

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/ai/chat/` | AI assistant chat |
| POST | `/ai/chat/<conversation_id>/` | Continue AI conversation |
| POST | `/ai/course-structure/` | Generate course structure |
| POST | `/ai/lesson-draft/` | Generate lesson draft |
| POST | `/ai/quiz-questions/` | Generate quiz questions |
| POST | `/ai/improve-content/` | Improve content |
| POST | `/ai/learning-objectives/` | Generate learning objectives |
| GET | `/ai/courses/` | List AI-related courses |

### Payments Module

Base path: `/api/v1/payments/`

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/stripe/checkout/<order_id>/` | Create Stripe checkout session |
| POST | `/stripe/webhook/` | Stripe webhook handler |
| GET | `/stripe/success/` | Payment success page |
| GET | `/stripe/cancel/` | Payment cancel page |
| POST | `/stripe/connect/` | Create instructor Stripe Connect account |
| GET | `/stripe/dashboard-link/` | Stripe dashboard login link |
| POST | `/withdraw/request/` | Request instructor withdrawal |
| PATCH/PUT | `/withdraw/approve/<withdraw_id>/` | Approve withdrawal |
| POST | `/instructor/withdraw/cancel/<withdraw_id>/` | Cancel instructor withdrawal |
| POST | `/affiliate/stripe/connect/` | Create affiliate Stripe Connect account |
| GET | `/affiliate/stripe/dashboard-link/` | Affiliate dashboard login link |
| POST | `/affiliate/withdraw/request/` | Request affiliate withdrawal |
| POST | `/organization/stripe/connect/` | Create organization Stripe Connect account |
| GET | `/organization/stripe/dashboard-link/` | Organization dashboard login link |
| POST | `/organization/withdraw/request/` | Request organization withdrawal |
| GET | `/stripe/return-page/` | Stripe return page |

### Notifications Module

Base path: `/api/v1/notifications/`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/notifications/` | Notification list |
| GET | `/notifications/<pk>/` | Notification detail |

### Enrollments Module

Base path: `/api/v1/enrollments/`

This app currently holds enrollment domain logic and certificate generation models. Its public URL file is reserved for future API expansion.

### Orders Module

Base path: `/api/v1/orders/`

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/cart/add/` | Add item to cart |
| GET | `/cart-view/` | View cart |
| DELETE | `/cart-remove/<item_id>/` | Remove cart item |
| POST | `/cart/checkout/` | Create order from cart |
| POST | `/wishlist/add/<course_id>/` | Add to wishlist |
| GET | `/wishlist/` | View wishlist |
| GET | `/wishlist/<course_id>/` | Wishlist lookup |

### Messaging Module

Base path: `/api/v1/messaging/`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET/POST | `/conversations/` | List or create conversations |
| GET/POST | `/conversations/<conversation_id>/messages/` | Messages in a conversation |

Websocket route:

| Protocol | Endpoint | Description |
| --- | --- | --- |
| WS | `/ws/messaging/conversations/<conversation_id>/` | Real-time conversation stream |

### Instructors Module

Base path: `/api/v1/instructors/`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/pending-instructors/` | Pending instructor applications |
| POST/PATCH | `/approve-instructor/<pk>/` | Approve instructor |
| POST/PATCH | `/feature-instructor/<pk>/` | Feature instructor |
| DELETE | `/delete-instructor/<pk>/` | Delete instructor |
| GET | `/withdrawals/` | Withdrawal requests |
| GET | `/instructors-list-admin/` | Instructor list for admin |
| GET | `/instructors-details/<pk>/` | Instructor detail for admin |
| GET | `/instructor-list-shown-by-admin/` | Admin-facing instructor list |
| GET | `/courses/` | Instructor course list |
| GET/PUT/PATCH | `/profile/` | Update instructor profile |
| GET | `/dashboard/` | Instructor dashboard |
| GET | `/earnings/` | Instructor earnings |
| GET | `/certificates-list/` | Certificates issued for instructor courses |
| POST | `/live-session/upload/<course_id>/` | Upload live session recording |
| POST | `/upload-signature/` | Upload signature image |
| GET | `/get-signature/` | Fetch instructor signature |
| GET | `/instructor/me/` | Current instructor profile |

### Organizations Module

Base path: `/api/v1/organizations/`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/unverified-organizations/` | List unverified organizations |
| POST/PATCH | `/approve-organization/<pk>/` | Approve organization |
| POST/PATCH | `/reject-organization/<pk>/` | Reject organization |
| POST | `/invite/` | Invite instructor |
| GET | `/invitation/<token>/` | Invitation detail |
| POST | `/invitation/respond/<token>/` | Respond to invitation |
| GET | `/organization/instructors/dashboard/` | Organization instructor dashboard |
| GET | `/instructors/live-classes/` | Organization instructor live class stats |
| GET/POST/PATCH | `/live-classes/<course_id>/` | Manage organization live classes |
| POST | `/courses/<course_id>/live-session/upload/` | Upload live session recording |
| GET | `/my-courses/` | Organization courses |
| GET | `/organization-deshboard/` | Organization dashboard |
| GET | `/organization-earnings/dashboard/` | Organization earnings dashboard |
| GET | `/organization-instructors-contracts/` | Organization instructors/contracts |
| GET | `/my-organization-courses/` | Organization-owned courses |
| GET/POST | `/contracts-instructors/` | Create/list contracts |
| GET/PUT/PATCH/DELETE | `/contracts-instructors/<contract_id>/` | Contract detail |
| GET | `/organization-contracts-details/<contract_id>/` | Contract detail summary |
| GET | `/members-analytics/` | Member analytics |
| GET/POST/PATCH | `/organization-profile/` | Organization profile update |
| GET | `/dashboard-statistics/` | Analytics overview |
| GET | `/revenue-trends/` | Revenue trends |
| GET | `/daily-revenue/` | Daily revenue chart |
| GET | `/course-analytics/` | Course analytics |
| GET | `/top-courses/` | Top courses |
| GET | `/recent-activity/` | Recent activity feed |
| GET | `/ratings-breakdown/` | Ratings breakdown |
| GET | `/comprehensive-report/` | Comprehensive report |
| GET | `/admin/organizations/` | Admin organization list |
| GET | `/admin/organizations/<pk>/` | Admin organization detail |
| GET | `/organization/earnings/` | Organization earnings |
| PATCH/PUT | `/membership/toggle/<pk>/` | Toggle membership status |
| GET/POST/PATCH | `/organization/profile/` | Organization profile API |
| GET | `/instructor/organizations/` | Instructor organizations |
| GET | `/instructor/contracts/courses/` | Instructor contract course list |
| GET | `/instructor/contracts/categories/` | Instructor contract category list |
| GET | `/instructor/earnings/chart/` | Instructor earnings chart |
| POST | `/sent/messages/contractus/` | Send contract-us message |
| GET | `/contact-us/messages/<message_id>/` | Contract-us message detail |

### Students Module

Base path: `/api/v1/students/`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/dashboard/` | Student dashboard |
| GET | `/courses/<course_id>/player/` | Course player |
| GET | `/courses/<course_id>/player/<lecture_id>/` | Course player with lecture |
| POST | `/lectures/<lecture_id>/complete/` | Complete lecture |
| GET | `/quizzes/<quiz_id>/` | Start quiz |
| POST | `/quizzes/<quiz_id>/submit/` | Submit quiz |
| PATCH/PUT | `/profile/` | Update student profile |
| POST | `/enroll-courses/` | Enroll in course |
| POST | `/exam-assessments-courses/` | Exam assessment flow |
| GET/POST | `/lecture-tracking/` | Lecture progress tracking |
| GET | `/course-completed/<course_id>/` | Check course completion |
| POST | `/reviews/<course_id>/` | Create review |
| PATCH/PUT | `/reviews-updated/<review_id>/` | Update review |
| DELETE | `/reviews-deleted/<review_id>/` | Delete review |
| GET | `/review-list/` | Review list |
| GET | `/quiz-attempts-list/` | Quiz attempt history |
| GET | `/student/purchase-history/` | Purchase history |
| POST | `/password-reset/` | Change password |
| DELETE | `/delete-account/` | Delete account |
| GET | `/student/live-classes/upcoming/` | Upcoming live classes |
| POST | `/joint-live-class/<live_class_id>/` | Join live class |
| GET | `/student/recordings/` | Purchased recordings |
| GET | `/student/recordings/<pk>/` | Recording detail |
| GET | `/student/certificates/` | Student certificates |

## Workflow Summary

1. A user registers or logs in through the users module.
2. Admins approve instructors and organizations when required.
3. Instructors build courses, add sections, lectures, and quizzes, then publish content.
4. Students enroll, consume lessons, complete quizzes, and generate certificates on completion.
5. Orders are created from carts, then paid through Stripe checkout.
6. Withdrawals, earnings, affiliate referrals, and organization revenue are handled in their respective modules.
7. Messaging, notifications, and AI tools support the day-to-day learning and content workflow.

## Authentication And Permissions

- The project uses a custom user model configured through `AUTH_USER_MODEL`.
- JWT refresh is exposed at `/api/v1/users/refresh-token/`.
- Admin-only APIs are concentrated in users, instructors, organizations, core, and moderation endpoints.
- Role-aware endpoints are separated by module so the frontend can map behavior cleanly.

## Local Setup

### Requirements

- Python 3.8 or later
- Virtual environment
- Stripe keys for payments
- `.env` configuration for secrets

### Install And Run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Environment Variables

```env
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLIC_KEY=pk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
EMAIL_HOST_PASSWORD=your-email-password
```

## API Documentation

If `DEBUG=True`, the project serves:

- Swagger UI at `/swagger/`
- ReDoc at `/redoc/`
- OpenAPI schema at `/swagger.json`

## Optional AI Companion App

The repository also includes `LearnHub_AI/`, a Streamlit-based AI teaching assistant. It is designed to sit alongside the backend and help instructors with:

- AI chat about a selected course
- Suggested course structure
- Lesson draft generation
- Quiz question generation
- Content improvement suggestions
- Learning objective generation

It can run independently with:

```bash
cd LearnHub_AI
pip install -r requirements.txt
streamlit run app.py
```

The app reads course data from the Django backend and can also run with dummy data for local testing.

## Deployment Notes

- Set `DEBUG=False` in production.
- Configure secure hosts, cookies, and CSRF settings.
- Serve the app behind a production ASGI server.
- Ensure Stripe webhooks and websocket routing are enabled in the deployment environment.

## License

Add a project license here before publishing the repository publicly.


