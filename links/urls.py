from django.urls import path
from .views import CreateLinkAPIView

urlpatterns = [
    path('create/', CreateLinkAPIView.as_view(), name='api_create_link')
]
