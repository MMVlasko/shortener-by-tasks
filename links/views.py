from links.models import Link
from links.serializers import LinkCreateAndUpdateSerializer, LinkSerializer
from links.serializers import ErrorSerializer
from .shortener import generate_short_alias

from datetime import datetime

from django.http import HttpResponse
from django.views import View
from django.shortcuts import redirect
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated


class CreateLinkAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LinkCreateAndUpdateSerializer,
        responses={
            200: LinkSerializer,
            201: LinkSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            409: ErrorSerializer
        },
        description="Создание короткой ссылки. Для анонимных пользователей user_id=null"
    )
    def post(self, request):
        serializer = LinkCreateAndUpdateSerializer(data=request.data)

        if serializer.is_valid():
            original_url = serializer.validated_data['original']
            is_new = True

            existing_link = Link.objects.filter(
                original=original_url,
                user__isnull=True
            )

            if existing_link.exists():
                link = existing_link.first()
                is_new = False
                status_code = status.HTTP_200_OK
            else:
                short = generate_short_alias(original_url)
                if Link.objects.filter(short=short).exists():
                    for _ in range(1000):
                        short = generate_short_alias(str(datetime.now()) + original_url)
                        if Link.objects.filter(short=short).exists():
                            break
                    else:
                        return Response(
                            {'error': 'Не удалось сгенерировать короткую ссылку'},
                            status=status.HTTP_409_CONFLICT
                        )

                link = Link.objects.create(
                    original=original_url,
                    short=short
                )
                status_code = status.HTTP_201_CREATED

            response_data = LinkSerializer(link).data
            response_data['is_new'] = is_new

            return Response(response_data, status=status_code)

        return Response(
            {'error': serializer.errors['original'][0]},
            status=status.HTTP_400_BAD_REQUEST
        )


class RedirectView(View):
    @staticmethod
    def get(request, short):
        try:
            link = Link.objects.get(short=short)
            return redirect(link.original)
        except Link.DoesNotExist:
            return HttpResponse(f'''
                <html><head>
                <title>404 Not Found</title>
                </head><body>
                <h1>Not Found</h1>
                <p>The requested short URL /{short} was not found on this server.</p>
                <hr>
                <address>Shortener App by MAI S.T.</address>
                </body></html>
            ''', status=status.HTTP_404_NOT_FOUND)
