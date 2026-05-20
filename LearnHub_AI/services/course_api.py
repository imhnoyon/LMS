# services/course_api.py
# Handles all communication with the Django REST API.
# Falls back to dummy data when USE_DUMMY_DATA=True or API is unreachable.

import os
import requests
from typing import Optional
from dotenv import load_dotenv

# from dummy_data.courses import DUMMY_COURSES

load_dotenv()

DJANGO_API_BASE_URL = os.getenv("DJANGO_API_BASE_URL", "https://rs0hfx59-8001.asse.devtunnels.ms")
DJANGO_API_COURSE_ENDPOINT = os.getenv("DJANGO_API_COURSE_ENDPOINT", "/api/courses")
DJANGO_API_AUTH_TOKEN = os.getenv("DJANGO_API_AUTH_TOKEN", "")

REQUEST_TIMEOUT = 10  # seconds


def _build_headers() -> dict:
    """Build request headers, including auth token if configured."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if DJANGO_API_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {DJANGO_API_AUTH_TOKEN}"
    return headers


def fetch_all_courses(use_dummy: bool = False) -> tuple[list[dict], str | None]:
    """
    Fetch all courses from the Django API.

    Args:
        use_dummy: If True, return dummy data without calling the API.

    Returns:
        Tuple of (courses_list, error_message).
        error_message is None on success.
    """
    # if use_dummy:
    #     return DUMMY_COURSES, None

    base = DJANGO_API_BASE_URL.rstrip('/')
    endpoint = DJANGO_API_COURSE_ENDPOINT.strip('/')
    url = f"{base}/{endpoint}/"
    try:
        response = requests.get(url, headers=_build_headers(), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        data = response.json()
        print("API RESPONSE TYPE:", type(data))
        print("API RESPONSE:", data)
        # Handle both list responses and paginated DRF responses
        if isinstance(data, list):
            return data, None
        elif isinstance(data, dict) and "data" in data:
            return data["data"], None
        else:
            return [], "Unexpected API response format."
    except requests.exceptions.ConnectionError:
        return [], f"Could not connect to Django API at `{url}`. Is the server running?"
    except requests.exceptions.Timeout:
        return [], f"Request to Django API timed out after {REQUEST_TIMEOUT}s."
    except requests.exceptions.HTTPError as e:
        return [], f"Django API returned an error: {e.response.status_code} {e.response.reason}"
    except Exception as e:
        return [], f"An unexpected error occurred: {str(e)}"


def fetch_course_by_id(course_id: int, use_dummy: bool = False) -> tuple[Optional[dict], str | None]:
    """
    Fetch a single course by ID from the Django API.

    Args:
        course_id: The integer ID of the course.
        use_dummy: If True, search dummy data instead of calling the API.

    Returns:
        Tuple of (course_dict, error_message).
        error_message is None on success.
    """
    # if use_dummy:
    #     course = next((c for c in DUMMY_COURSES if c["id"] == course_id), None)
    #     if course:
    #         return course, None
    #     return None, f"No dummy course found with ID {course_id}."

    base = DJANGO_API_BASE_URL.rstrip('/')
    endpoint = DJANGO_API_COURSE_ENDPOINT.strip('/')
    url = f"{base}/{endpoint}/{course_id}/"
    try:
        response = requests.get(url, headers=_build_headers(), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "data" in data:
            return data["data"], None
        return data, None
    except requests.exceptions.ConnectionError:
        return None, f"Could not connect to Django API at `{url}`."
    except requests.exceptions.Timeout:
        return None, f"Request timed out after {REQUEST_TIMEOUT}s."
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None, f"Course with ID {course_id} not found."
        return None, f"Django API error: {e.response.status_code} {e.response.reason}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"
