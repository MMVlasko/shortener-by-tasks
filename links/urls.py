from django.urls import path
from .views import (
    CreateLinkAPIView,
    GetMyLinksAPIView,
    GetVisitsByLinkAPIView,
    SearchInMyLinksAPIView,
    GenerateQRCodeView,
    GetLinkAPIView
)

urlpatterns = [
    path('create/', CreateLinkAPIView.as_view(), name='api_create_link'),
    path('qrcode/<str:short>', GenerateQRCodeView.as_view(), name='generate_qr_code'),
    path('get/', GetMyLinksAPIView.as_view(), name='api_get_links'),
    path('search/<str:keyword>', SearchInMyLinksAPIView.as_view(), name='api_search_links'),
    path('get-visits/<str:short>', GetVisitsByLinkAPIView.as_view(), name='api_get_visits'),
    path('get/<str:short>', GetLinkAPIView.as_view(), name='api_get_link')
]
