
from rest_framework.permissions import BasePermission

class IsInstructor(BasePermission):
    message = "Only instructors or organizations can access this."

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.role in ["instructor",]
        )


# class IsOrganization(BasePermission):
#     message = "Only organizations can access this."

#     def has_permission(self, request, view):
#         return request.user and request.user.is_authenticated and \
#                request.user.groups.filter(name='Organizations').exists()
               
               
               
class IsInstructorOrOrganization(BasePermission):
    message = "Only instructors or organizations can access this."

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.role in ["instructor", "organization"]
        )
        
        
class IsStudent(BasePermission):
    message = "Only instructors or organizations can access this."

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.role in ["student",]
        )
        
        
class IsAffiliate(BasePermission):
    message = "Only affiliates can access this."

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.role in ["affiliate",]
        )
        
class IsOrganization(BasePermission):
    message = "Only Organizations can access this."

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.role in ["Or_admin",]
        )
        
        