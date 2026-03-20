from django.urls import path
from apps.core import views


# Core app URLs
urlpatterns = [
    # Contact
    path('contact/', views.list_contacts, name='contact-list'),
    path('contact/submit/', views.submit_contact, name='contact-submit'),
    path('contact/<str:pk>/', views.contact_detail, name='contact-detail'),
    path('contact/<str:pk>/status/', views.update_contact_status, name='contact-status-update'),
    
    # FAQ Category
    path('faq/categories/', views.list_faq_categories, name='faq-category-list'),
    path('faq/categories/create/', views.create_faq_category, name='faq-category-create'),
    path('faq/categories/<str:pk>/', views.faq_category_detail, name='faq-category-detail'),

    # FAQ
    path('faq/', views.list_faqs, name='faq-list'),
    path('faq/create/', views.create_faq, name='faq-create'),
    path('faq/<str:pk>/', views.faq_detail, name='faq-detail'),
    
    # Site Config
    path('site-config/', views.get_config, name='site-config-get'),
    path('site-config/create/', views.create_config, name='site-config-create'),
    path('site-config/update/', views.update_config, name='site-config-update'),
]