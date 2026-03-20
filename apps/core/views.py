from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from .models import Contact, SiteConfig, FAQCategory, FAQ
from .serializers import ContactSerializer, ContactStatusUpdateSerializer, SiteConfigSerializer, FAQCategorySerializer, FAQSerializer
from drf_yasg import openapi


# Create your views here.
@swagger_auto_schema(
    method='post',
    operation_summary="Submit Contact Form",
    operation_description="Anyone can submit a contact form.",
    request_body=ContactSerializer,
    responses={201: ContactSerializer, 400: "Validation Error"},
    tags=['Contact'],
)
@api_view(['POST'])
def submit_contact(request):
    serializer = ContactSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_summary="List All Contacts",
    operation_description="Returns all contacts. Admin only.",
    manual_parameters=[
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            description="Filter by status (pending, in_progress, resolved, closed, spam)",
            type=openapi.TYPE_STRING,
            required=False,
        ),
    ],
    responses={200: ContactSerializer(many=True)},
    tags=['Contact'],
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_contacts(request):
    contacts = Contact.objects.all()
    status_filter = request.query_params.get('status')
    if status_filter:
        contacts = contacts.filter(status=status_filter)
    serializer = ContactSerializer(contacts, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_summary="Get Contact",
    operation_description="Returns a specific contact. Admin only.",
    responses={200: ContactSerializer, 404: "Not found"},
    tags=['Contact'],
)
@swagger_auto_schema(
    method='delete',
    operation_summary="Delete Contact",
    operation_description="Deletes a specific contact. Admin only.",
    responses={204: "Deleted successfully", 404: "Not found"},
    tags=['Contact'],
)
@api_view(['GET', 'DELETE'])
@permission_classes([IsAdminUser])
def contact_detail(request, pk):
    try:
        contact = Contact.objects.get(pk=pk)
    except Contact.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ContactSerializer(contact)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        contact.delete()
        return Response({"detail": "Deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='patch',
    operation_summary="Update Contact Status",
    operation_description="Updates the status of a contact. Admin only.",
    request_body=ContactStatusUpdateSerializer,
    responses={200: ContactSerializer, 400: "Validation Error", 404: "Not found"},
    tags=['Contact'],
)
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_contact_status(request, pk):
    try:
        contact = Contact.objects.get(pk=pk)
    except Contact.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = ContactStatusUpdateSerializer(contact, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(ContactSerializer(contact).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_summary="List All FAQ Categories",
    operation_description="Returns all active FAQ categories with their FAQs.",
    responses={200: FAQCategorySerializer(many=True)},
    tags=['FAQ'],
)
@api_view(['GET'])
def list_faq_categories(request):
    categories = FAQCategory.objects.filter(is_active=True)
    serializer = FAQCategorySerializer(categories, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_summary="Create FAQ Category",
    operation_description="Creates a new FAQ category. Admin only.",
    request_body=FAQCategorySerializer,
    responses={201: FAQCategorySerializer, 400: "Validation Error"},
    tags=['FAQ'],
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_faq_category(request):
    serializer = FAQCategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_summary="Get FAQ Category",
    operation_description="Returns a specific FAQ category with its FAQs.",
    responses={200: FAQCategorySerializer, 404: "Not found"},
    tags=['FAQ'],
)
@swagger_auto_schema(
    method='put',
    operation_summary="Update FAQ Category",
    operation_description="Updates a specific FAQ category. Admin only.",
    request_body=FAQCategorySerializer,
    responses={200: FAQCategorySerializer, 400: "Validation Error", 404: "Not found"},
    tags=['FAQ'],
)
@swagger_auto_schema(
    method='delete',
    operation_summary="Delete FAQ Category",
    operation_description="Deletes a specific FAQ category. Admin only.",
    responses={204: "Deleted successfully", 404: "Not found"},
    tags=['FAQ'],
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def faq_category_detail(request, pk):
    try:
        category = FAQCategory.objects.get(pk=pk)
    except FAQCategory.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = FAQCategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        serializer = FAQCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        category.delete()
        return Response({"detail": "Deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
    
@swagger_auto_schema(
    method='get',
    operation_summary="List All FAQs",
    operation_description="Returns all active FAQs.",
    responses={200: FAQSerializer(many=True)},
    tags=['FAQ'],
)
@api_view(['GET'])
def list_faqs(request):
    faqs = FAQ.objects.filter(is_active=True)
    serializer = FAQSerializer(faqs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_summary="Create FAQ",
    operation_description="Creates a new FAQ. Admin only.",
    request_body=FAQSerializer,
    responses={201: FAQSerializer, 400: "Validation Error"},
    tags=['FAQ'],
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_faq(request):
    serializer = FAQSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_summary="Get FAQ",
    operation_description="Returns a specific FAQ.",
    responses={200: FAQSerializer, 404: "Not found"},
    tags=['FAQ'],
)
@swagger_auto_schema(
    method='put',
    operation_summary="Update FAQ",
    operation_description="Updates a specific FAQ. Admin only.",
    request_body=FAQSerializer,
    responses={200: FAQSerializer, 400: "Validation Error", 404: "Not found"},
    tags=['FAQ'],
)
@swagger_auto_schema(
    method='delete',
    operation_summary="Delete FAQ",
    operation_description="Deletes a specific FAQ. Admin only.",
    responses={204: "Deleted successfully", 404: "Not found"},
    tags=['FAQ'],
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def faq_detail(request, pk):
    try:
        faq = FAQ.objects.get(pk=pk)
    except FAQ.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = FAQSerializer(faq)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        serializer = FAQSerializer(faq, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        faq.delete()
        return Response({"detail": "Deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='get',
    operation_summary="Get Site Config",
    operation_description="Returns the site configuration.",
    responses={200: SiteConfigSerializer, 404: "Not found"},
    tags=['Site Config'],
)
@api_view(['GET'])
def get_config(request):
    config = SiteConfig.get_active()
    if not config:
        return Response({"detail": "No config found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = SiteConfigSerializer(config)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_summary="Create Site Config",
    operation_description="Creates the site configuration. Only one config allowed.",
    request_body=SiteConfigSerializer,
    responses={201: SiteConfigSerializer, 400: "Already exists or Validation Error"},
    tags=['Site Config'],
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_config(request):
    if SiteConfig.objects.exists():
        return Response({"detail": "Config already exists. Use update instead."}, status=status.HTTP_400_BAD_REQUEST)
    serializer = SiteConfigSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='put',
    operation_summary="Update Site Config",
    operation_description="Updates the site configuration.",
    request_body=SiteConfigSerializer,
    responses={200: SiteConfigSerializer, 400: "Validation Error", 404: "Not found"},
    tags=['Site Config'],
)
@api_view(['PUT'])
@permission_classes([IsAdminUser])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_config(request):
    config = SiteConfig.get_active()
    if not config:
        return Response({"detail": "No config found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = SiteConfigSerializer(config, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)