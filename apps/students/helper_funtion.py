from apps.courses.models import Section, Lecture, LecturesProgress, Quiz, QuizAttempt
from django.db.models import Q

def is_quiz_passed(user, quiz):
    """Check if the user has passed the specified quiz."""
    if not quiz:
        return True
    
    last_attempt = QuizAttempt.objects.filter(user=user, quiz=quiz).order_by('-submitted_at').first()
    if last_attempt and last_attempt.score_percentage >= quiz.passing_score:
        return True
    return False

def is_lecture_accessible(user, lecture):
    """
    Checks if a student can access a lecture based on prerequisites:
    1. All previous sections must be fully completed (lectures done + quizzes passed).
    2. All previous lectures in current section must be completed.
    """
    section = lecture.section
    course = section.course

    # 1. Check all previous sections
    previous_sections = Section.objects.filter(course=course, order__lt=section.order)
    for prev_sec in previous_sections:
        unfinished_lectures = Lecture.objects.filter(section=prev_sec).exclude(
            id__in=LecturesProgress.objects.filter(user=user, is_completed=True).values_list('lecture_id', flat=True)
        ).exists()
        if unfinished_lectures:
            return False
        
        quizzes = Quiz.objects.filter(section=prev_sec)
        for quiz in quizzes:
            if not is_quiz_passed(user, quiz):
                return False

    # 2. Check previous lectures in current section (using order and id)
    previous_lectures = Lecture.objects.filter(section=section).filter(
        Q(order__lt=lecture.order) | Q(order=lecture.order, id__lt=lecture.id)
    )
    
    unfinished_prev_lectures = previous_lectures.exclude(
        id__in=LecturesProgress.objects.filter(user=user, is_completed=True).values_list('lecture_id', flat=True)
    ).exists()
    
    if unfinished_prev_lectures:
        return False

    return True

def get_next_lecture(current_lecture):
    """Utility to find the next lecture in the course (robust against duplicated order)."""
    current_section = current_lecture.section
    course = current_section.course

    # Try next lecture in same section (order, id)
    next_lecture = Lecture.objects.filter(section=current_section).filter(
        Q(order__gt=current_lecture.order) | Q(order=current_lecture.order, id__gt=current_lecture.id)
    ).order_by("order", "id").first()

    if next_lecture:
        return next_lecture

    # Try first lecture of next section
    next_section = Section.objects.filter(
        course=course,
        order__gt=current_section.order
    ).order_by("order").first()

    if next_section:
        return next_section.lectures.order_by("order", "id").first()

    return None
