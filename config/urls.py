from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions, settings
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static


schema_view = get_schema_view(
    openapi.Info(
        title="From-Cert API",
        default_version='v1',
        description="API documentation for From-Cert",
        terms_of_service="https://www.from-cert.com/terms/",
        contact=openapi.Contact(email="mdsadiqulislam446@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Endpoints
    path('api/', include([
        path('api/v1/core/', include('apps.core.urls')),
        path('api/v1/users/', include('apps.users.urls')),
        path('api/v1/courses/', include('apps.courses.urls')),
        path('api/v1/affiliates/', include('apps.affiliates.urls')),
        path('api/v1/analytics/', include('apps.analytics.urls')),
        path('api/v1/payments/', include('apps.payments.urls')),
        path('api/v1/notifications/', include('apps.notifications.urls')),
        path('api/v1/enrollments/', include('apps.enrollments.urls')),
        path('api/v1/orders/', include('apps.orders.urls')),
        path('api/v1/messaging/', include('apps.messaging.urls')),
    ]))
]


# Swagger and Redoc UI (only in DEBUG mode)
if settings.DEBUG:
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
        path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    ]
    
# Static and Media files (only in DEBUG mode)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)