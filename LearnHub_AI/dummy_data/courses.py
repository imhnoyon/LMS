# dummy_data/courses.py
# Dummy course data that mirrors the real Django API response structure.
# Used for local testing without a running Django backend.

DUMMY_COURSES = [
    {
        "id": 33,
        "title": "Mastering Modern Web Development 2026",
        "subtitle": "Learn HTML, CSS, JavaScript, React, Node.js & Full Stack Development from Beginner to Advanced",
        "Category": "Web Development",
        "topic": "Web Development",
        "language": "en",
        "description": "Build modern and responsive web applications using the latest technologies. This course covers frontend and backend development step by step with real-world projects, authentication systems, APIs, databases, deployment, and advanced development techniques.",
        "level": "intermediate",
        "price": "1000.00",
        "rating": 0,
        "duration": None,
        "discount_price": "950.00",
        "coupon_code": "mahedi50",
        "is_wishlisted": False,
        "expiry_type": "3_months",
        "reviews_count": 0,
        "status": "accepted",
        "modules": 1,
        "lectures": 2,
        "quizes": 1,
        "instructor": {
            "id": "ddde375b-5c91-4ad7-b844-e3c33de6fa25",
            "name": "Mahedi",
            "email": "mahedijvai950@gmail.com",
            "phone": "01345979578",
            "get_biography": "Web Developer.",
            "avatar": "https://via.placeholder.com/150"
        },
        "advance_info": {
            "id": 32,
            "thumbnail": "https://via.placeholder.com/800x450?text=Web+Development+Course",
            "trailer_video": None,
            "description": "Build modern and responsive web applications using the latest technologies."
        },
        "outcomes": [
            {"id": 173, "text": "HTML5 & CSS3 Fundamentals", "order": 1},
            {"id": 174, "text": "Responsive Web Design", "order": 2},
            {"id": 175, "text": "JavaScript ES6+", "order": 3},
            {"id": 176, "text": "React.js Development", "order": 4}
        ],
        "requirements": [
            {"id": 178, "text": "Basic computer knowledge", "order": 1},
            {"id": 179, "text": "Internet connection", "order": 2},
            {"id": 180, "text": "No prior coding experience required", "order": 3}
        ],
        "sections": [
            {
                "id": 25,
                "name": "Introduction to HTML",
                "order": 0,
                "lectures": [
                    {
                        "id": 56,
                        "name": "Basic structure of HTML",
                        "order": 1,
                        "description": "Learn the foundational structure of an HTML document including doctype, head, and body.",
                        "video_file": None,
                        "LectureAttachment": None,
                        "LectureNoteFile": None,
                        "lecture_notes": "HTML stands for HyperText Markup Language. Every HTML document starts with <!DOCTYPE html>."
                    },
                    {
                        "id": 57,
                        "name": "How to install VS Code",
                        "order": 2,
                        "description": "Step-by-step guide to installing and configuring Visual Studio Code for web development.",
                        "video_file": None,
                        "LectureAttachment": None,
                        "LectureNoteFile": None,
                        "lecture_notes": "VS Code is a free, open-source editor by Microsoft. Download from https://code.visualstudio.com"
                    }
                ]
            }
        ],
        "related_courses": [
            {"id": 10, "title": "Frontend Development"},
            {"id": 11, "title": "Java Development"}
        ]
    },
    {
        "id": 10,
        "title": "Frontend Development Masterclass",
        "subtitle": "Deep dive into HTML, CSS, Tailwind, and React",
        "Category": "Web Development",
        "topic": "Frontend Development",
        "language": "en",
        "description": "A comprehensive course covering all aspects of modern frontend development including responsive design, component-based architecture, and state management.",
        "level": "beginner",
        "price": "800.00",
        "rating": 4.5,
        "duration": "12 hours",
        "discount_price": "750.00",
        "coupon_code": "front20",
        "is_wishlisted": False,
        "expiry_type": "6_months",
        "reviews_count": 120,
        "status": "accepted",
        "modules": 3,
        "lectures": 18,
        "quizes": 3,
        "instructor": {
            "id": "aabbcc11-1234-5678-abcd-ef1234567890",
            "name": "Sara Khan",
            "email": "sara.khan@example.com",
            "phone": "01712345678",
            "get_biography": "Senior Frontend Engineer with 8 years of experience.",
            "avatar": "https://via.placeholder.com/150"
        },
        "advance_info": {
            "id": 10,
            "thumbnail": "https://via.placeholder.com/800x450?text=Frontend+Development",
            "trailer_video": None,
            "description": "Master the art of building beautiful, performant web interfaces."
        },
        "outcomes": [
            {"id": 101, "text": "Build responsive layouts with CSS Grid & Flexbox", "order": 1},
            {"id": 102, "text": "Style applications with Tailwind CSS", "order": 2},
            {"id": 103, "text": "Build React components and manage state", "order": 3},
            {"id": 104, "text": "Deploy frontend apps to Vercel and Netlify", "order": 4}
        ],
        "requirements": [
            {"id": 201, "text": "Basic HTML knowledge", "order": 1},
            {"id": 202, "text": "A code editor (VS Code recommended)", "order": 2}
        ],
        "sections": [
            {
                "id": 30,
                "name": "CSS Fundamentals",
                "order": 0,
                "lectures": [
                    {
                        "id": 60,
                        "name": "Box Model and Layout",
                        "order": 1,
                        "description": "Understanding the CSS box model and how layout works in the browser.",
                        "video_file": None,
                        "LectureAttachment": None,
                        "LectureNoteFile": None,
                        "lecture_notes": "Every HTML element is a box. The box model consists of: content, padding, border, and margin."
                    }
                ]
            },
            {
                "id": 31,
                "name": "React Basics",
                "order": 1,
                "lectures": [
                    {
                        "id": 61,
                        "name": "What is React?",
                        "order": 1,
                        "description": "Introduction to React.js and the component-based architecture.",
                        "video_file": None,
                        "LectureAttachment": None,
                        "LectureNoteFile": None,
                        "lecture_notes": "React is a JavaScript library for building user interfaces, developed by Facebook."
                    }
                ]
            }
        ],
        "related_courses": [
            {"id": 33, "title": "Mastering Modern Web Development 2026"}
        ]
    }
]
