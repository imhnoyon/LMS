from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import exception_handler
class APIResponse:
    """
    Standardized API Response Handler
    """

    @staticmethod
    def success(message="Success", data=None, status_code=status.HTTP_200_OK):
        """
        Returns a successful response.
        :param message: Success message string
        :param data: Data dictionary (optional)
        :param status_code: HTTP status code
        :return: Response object
        """
        response_data = {
            "success": True,
            "status": status_code,
            "message": message,
        }
        
        if data is not None:
            response_data["data"] = data
            
        return Response(response_data, status=status_code)

    # @staticmethod
    # def error(message="Error", errors=None, error_code=None, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
    #     """
    #     Returns an error response.
    #     :param message: Error message string
    #     :param errors: Detailed errors dictionary (optional)
    #     :param error_code: Application-specific error code (optional)
    #     :param status_code: HTTP status code
    #     :return: Response object
    #     """
    #     # Support 'data' as an alias for 'errors' to prevent TypeErrors
    #     if errors is None and 'data' in kwargs:
    #         errors = kwargs['data']

    #     response_data = {
    #         "success": False,
    #         "status": status_code,
    #         "message": message,
    #     }

    #     if errors:
    #         response_data["errors"] = errors
        
    #     if error_code:
    #         response_data["error_code"] = error_code

    #     return Response(response_data, status=status_code)
    
    @staticmethod
    def error(message="Error", errors=None, error_code=None, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):

        if errors is None and 'data' in kwargs:
            errors = kwargs['data']

        if errors:
            if isinstance(errors, dict):
                first_key = next(iter(errors))
                first_value = errors[first_key]

                if isinstance(first_value, list):
                    msg = first_value[0]
                else:
                    msg = str(first_value)

                # 🔥 custom clean message
                if "required" in msg.lower():
                    message = f"{first_key} is required"
                elif "invalid" in msg.lower():
                    message = f"{first_key} is invalid"
                else:
                    message = msg

            elif isinstance(errors, list):
                message = errors[0]
            else:
                message = str(errors)

        response_data = {
            "success": False,
            "status": status_code,
            "message": message,
        }

        if errors:
            response_data["errors"] = errors

        if error_code:
            response_data["error_code"] = error_code

        return Response(response_data, status=status_code)


        
        
        
        