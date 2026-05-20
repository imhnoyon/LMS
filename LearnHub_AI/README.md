# AI Teaching Assistant

An AI-powered teaching assistant built with Streamlit and OpenAI (gpt-4o-mini).  
Fetches course data from a Django REST API and provides an interactive chat interface plus quick-action tools for instructors.

---

## Project Structure

```
ai_teaching_assistant/
├── app.py                      # Streamlit entry point
├── requirements.txt
├── .env                        # Your secrets (never commit this)
├── .env.example                # Template for .env
│
├── services/
│   ├── course_api.py           # Django REST API client
│   └── ai_service.py           # All OpenAI interactions
│
├── components/
│   ├── sidebar.py              # Course selector + metadata panel
│   ├── chat_panel.py           # Conversational chat UI
│   └── quick_actions.py        # Quick action buttons + forms
│
├── utils/
│   └── helpers.py              # Shared utility functions
│
└── dummy_data/
    └── courses.py              # Mock courses for local testing
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=sk-...your-key-here...
DJANGO_API_BASE_URL=http://127.0.0.1:8002
DJANGO_API_COURSE_ENDPOINT=/api/courses
DJANGO_API_AUTH_TOKEN=           # optional, only if your API requires auth
```

### 3. Run the app

```bash
streamlit run app.py
```

---

## Testing with Dummy Data

The app ships with two sample courses in `dummy_data/courses.py`.  
In the sidebar, toggle **"Use dummy data"** ON to use them without a running Django server.  
This is the default setting.

---

## Django Integration

### Option 1 — Iframe embed

Embed the Streamlit app directly in a Django template.  
Pass the course ID via query parameter so the app auto-loads the correct course:

```html
<!-- In your Django template -->
<iframe
  src="http://localhost:8501/?course_id={{ course.id }}"
  width="100%"
  height="800px"
  frameborder="0">
</iframe>
```

### Option 2 — Standalone service

Run the Streamlit app as a separate service alongside Django.  
Users navigate to it directly; course selection is available in the sidebar.

### Expected API contract

The app expects your Django API to return JSON matching this shape:

**GET** `/api/courses/` → list of course objects  
**GET** `/api/courses/{id}/` → single course object

The course object must include:
```json
{
  "id": 33,
  "title": "...",
  "topic": "...",
  "level": "beginner|intermediate|advanced",
  "description": "...",
  "price": "...",
  "discount_price": "...",
  "modules": 1,
  "lectures": 2,
  "quizes": 1,
  "instructor": { "name": "...", "get_biography": "...", "avatar": "..." },
  "advance_info": { "thumbnail": "..." },
  "outcomes": [{ "id": 1, "text": "...", "order": 1 }],
  "requirements": [{ "id": 1, "text": "...", "order": 1 }],
  "sections": [
    {
      "id": 1,
      "name": "...",
      "order": 0,
      "lectures": [
        {
          "id": 1,
          "name": "...",
          "order": 1,
          "description": "...",
          "lecture_notes": "..."
        }
      ]
    }
  ]
}
```

Paginated responses (DRF default) are supported — the client reads `results` automatically.

---

## Features

| Feature | Description |
|---|---|
| 💬 **Chat Assistant** | Full session-scoped conversation about the course |
| 🏗️ **Suggest Course Structure** | AI-recommended module & lecture outline |
| 📝 **Generate Lesson Draft** | Complete lesson with objectives, content, exercises |
| ❓ **Create Quiz Questions** | Multiple-choice questions with answers & explanations |
| ✨ **Improve Content** | Rewrite existing content with a specific goal |
| 🎯 **Learning Objectives** | SMART objectives using Bloom's Taxonomy |
| ⬇️ **Download Results** | Save any AI output as a `.txt` file |

---

## Notes

- The **"Improve Content"** quick action requires you to paste content manually, since student feedback/ratings data is not present in the API response.
- `duration` is `null` in the API — lesson drafts will omit time estimates until this field is populated.
- Quiz *content* is AI-generated from course context; there is no existing question bank in the API.
