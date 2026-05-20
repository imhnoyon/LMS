# services/ai_service.py
# Handles all OpenAI interactions.
# Each method builds a focused system + user prompt from course data
# and returns the AI-generated text response.

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o-mini"
MAX_TOKENS = 2048


def _get_client() -> OpenAI:
    """Initialise and return an OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise ValueError(
            "OPENAI_API_KEY is not set. Please add it to your .env file."
        )
    return OpenAI(api_key=api_key)


def _course_context(course: dict) -> str:
    """
    Serialise the core course metadata into a clean text block
    to use as context in every AI prompt.
    """
    outcomes = "\n".join(
        f"  - {o.get('text', '')}" for o in (course.get("outcomes") or [])
    )
    requirements = "\n".join(
        f"  - {r.get('text', '')}" for r in (course.get("requirements") or [])
    )
    sections_text = ""
    for section in (course.get("sections") or []):
        lectures = "\n".join(
            f"    • Lecture {l.get('order', '')}: {l.get('name', '')}"
            for l in (section.get("lectures") or [])
        )
        sections_text += f"\n  Section: {section.get('name', '')}\n{lectures}"

    price = course.get('price', 'N/A')
    discount_price = course.get('discount_price', '')
    coupon = course.get('coupon_code', '')
    
    pricing_str = f"{price}"
    if discount_price:
        pricing_str += f" (Discount Price: {discount_price})"
    if coupon:
        pricing_str += f" [Coupon Code: {coupon}]"

    return f"""
Course Title: {course.get('title', 'N/A')}
Topic: {course.get('topic', 'N/A')}
Level: {course.get('level', 'N/A')}
Pricing: {pricing_str}
Description: {course.get('description', 'N/A')}

Learning Outcomes:
{outcomes or '  Not specified'}

Requirements:
{requirements or '  Not specified'}

Course Structure:
{sections_text or '  Not specified'}
""".strip()


def chat_with_assistant(
    course: dict,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    """
    Continue a multi-turn conversation with the AI teaching assistant
    about the given course.

    Args:
        course: The full course dict from the Django API.
        conversation_history: List of prior {"role": ..., "content": ...} messages.
        user_message: The latest message from the user.

    Returns:
        The assistant's response string.
    """
    client = _get_client()

    system_prompt = f"""You are an expert AI teaching assistant helping instructors and students 
with the following course. You have deep knowledge of instructional design, pedagogy, and content creation.


{_course_context(course)}

Your responsibilities:
- Answer questions about the course content, structure, and learning objectives.
- Help suggest improvements, lesson ideas, quiz questions, and learning activities.
- Be concise, professional, and actionable in your responses.
- If a question is unrelated to the course or education, politely redirect.
- Always ground your answers in the course context provided above."""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def suggest_course_structure(course: dict) -> str:
    """
    Generate a recommended full course structure based on the course metadata.
    """
    client = _get_client()

    system_prompt = """You are an expert instructional designer. 
Your task is to suggest a detailed, well-organised course structure.
Format your response as a clear numbered outline with modules, sections, and lecture titles.
Be specific and practical."""

    user_prompt = f"""Based on the following course information, suggest a comprehensive and 
well-structured course outline that improves on or expands the current structure:

{_course_context(course)}

Provide:
1. A revised/expanded list of modules with section names
2. 3-5 lecture titles per section
3. A brief rationale for the structure"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def generate_lesson_draft(course: dict, lecture_name: str, lecture_notes: str) -> str:
    """
    Generate a full lesson draft for a specific lecture.

    Args:
        course: The course dict.
        lecture_name: The name of the lecture to draft.
        lecture_notes: Existing notes for the lecture (may be empty).

    Returns:
        A formatted lesson draft as a string.
    """
    client = _get_client()

    system_prompt = """You are an expert curriculum developer and technical writer.
Your task is to write a detailed, engaging lesson draft for an online course.
Use clear headings, bullet points, and examples. Write for the specified audience level."""

    existing_notes = (
        f"Existing lecture notes:\n{lecture_notes}"
        if lecture_notes
        else "No existing notes provided."
    )

    user_prompt = f"""Write a complete lesson draft for the following lecture:

Course context:
{_course_context(course)}

Lecture to develop: "{lecture_name}"
{existing_notes}

Your lesson draft should include:
1. **Learning Objectives** (3–5 specific, measurable objectives)
2. **Introduction** (Hook and overview — 1-2 paragraphs)
3. **Core Content** (Detailed explanation with examples, broken into logical sub-sections)
4. **Practical Exercise** (A hands-on activity or task for students)
5. **Summary** (Key takeaways in bullet points)
6. **Further Reading** (2–3 resource suggestions)"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def create_quiz_questions(course: dict, topic: str, num_questions: int = 5) -> str:
    """
    Generate multiple-choice quiz questions for a given topic within the course.

    Args:
        course: The course dict.
        topic: The specific topic or section to focus questions on.
        num_questions: How many questions to generate.

    Returns:
        Formatted quiz questions as a string.
    """
    client = _get_client()

    system_prompt = """You are an expert assessment designer for online courses.
Create clear, unambiguous multiple-choice questions that test genuine understanding,
not just memorisation. Each question must have exactly 4 options with one correct answer."""

    user_prompt = f"""Create {num_questions} multiple-choice quiz questions for the topic: "{topic}"

Course context:
{_course_context(course)}

Format each question as:
**Q[N]: [Question text]**
A) [Option]
B) [Option]
C) [Option]
D) [Option]
✅ Correct Answer: [Letter] — [Brief explanation of why this is correct]

---

Ensure questions range from recall to application-level thinking."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def improve_content(course: dict, content_to_improve: str, improvement_goal: str) -> str:
    """
    Rewrite or improve a piece of existing course content.

    Args:
        course: The course dict.
        content_to_improve: The raw content text to improve.
        improvement_goal: What the improvement should achieve (e.g. "more engaging", "clearer").

    Returns:
        Improved content as a string.
    """
    client = _get_client()

    system_prompt = """You are an expert educational content editor.
Your task is to improve course content to be clearer, more engaging, and pedagogically sound.
Preserve the original intent while enhancing quality."""

    user_prompt = f"""Improve the following course content with this goal: "{improvement_goal}"

Course context:
{_course_context(course)}

Original content to improve:
---
{content_to_improve}
---

Provide:
1. **Improved Version** of the content
2. **Summary of Changes** — a brief bullet list of what was changed and why"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def generate_learning_objectives(course: dict, section_name: str = "") -> str:
    """
    Generate SMART learning objectives for the course or a specific section.

    Args:
        course: The course dict.
        section_name: Optional section name to scope objectives to.

    Returns:
        Learning objectives as a formatted string.
    """
    client = _get_client()

    system_prompt = """You are an expert instructional designer specialising in writing 
SMART (Specific, Measurable, Achievable, Relevant, Time-bound) learning objectives.
Use Bloom's Taxonomy action verbs (remember, understand, apply, analyse, evaluate, create)."""

    scope = f'for the section: "{section_name}"' if section_name else "for the entire course"

    user_prompt = f"""Write comprehensive SMART learning objectives {scope}.

Course context:
{_course_context(course)}

Provide:
1. **Overall Course Objective** (1 overarching goal statement)
2. **Knowledge Objectives** (what students will know — 3-4 objectives)
3. **Skill Objectives** (what students will be able to do — 3-4 objectives)
4. **Attitude/Mindset Objectives** (professional disposition — 1-2 objectives)

Use action verbs from Bloom's Taxonomy. Be specific and measurable."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
