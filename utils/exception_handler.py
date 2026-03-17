from rest_framework.views import exception_handler
from rest_framework import status
from utils.api_response import APIResponse

def custom_exception_handler(exc, context):
    """
    Custom exception handler that standardizes exception responses
    using the APIResponse utility.
    """
    
    response = exception_handler(exc, context)
    if response is not None:
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            return APIResponse.error(
                message="Validation failed",
                errors=response.data,
                status_code=response.status_code
            )
        
       
        message = "An error occurred"
        if isinstance(response.data, dict) and 'detail' in response.data:
            message = response.data['detail']
          
        elif isinstance(response.data, list):
             message = str(response.data[0]) 
             
        return APIResponse.error(
            message=message,
            errors=response.data if not isinstance(response.data, dict) or 'detail' not in response.data else None,
            status_code=response.status_code
        )

    return response
