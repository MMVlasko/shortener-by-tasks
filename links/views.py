from links.models import Link, Visit
from links.serializers import LinkCreateAndUpdateSerializer, LinkSerializer, GetLinkSerializer, VisitSerializer
from users.serializers import ErrorSerializer
from .shortener import generate_short_alias

import threading
from io import BytesIO
from datetime import datetime

import qrcode
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.shortcuts import redirect
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated


class LinkAndVisitLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100


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

            user = request.user if request.user.is_authenticated else None

            if user:
                existing_link = Link.objects.filter(
                    original=original_url,
                    user=user
                )
            else:
                existing_link = Link.objects.filter(
                    original=original_url,
                    user__isnull=True
                )

            if existing_link.exists():
                link = existing_link.first()
                is_new = False
                status_code = status.HTTP_200_OK
            else:
                if user:
                    short = generate_short_alias(user.username + original_url)
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
                    short=short,
                    user=user
                )
                status_code = status.HTTP_201_CREATED

            response_data = LinkSerializer(link).data
            response_data['is_new'] = is_new

            return Response(response_data, status=status_code)

        return Response(
            {'error': serializer.errors['original'][0]},
            status=status.HTTP_400_BAD_REQUEST
        )


class GenerateQRCodeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        description='Генерация QR-кода по данной короткой ссылке (https://{hostname}/{short}).',
        responses={
            200: OpenApiTypes.BINARY
        },
        parameters=[
            OpenApiParameter(
                name='short',
                type=str,
                location=OpenApiParameter.PATH,
                description='Короткий идентификатор ссылки',
                required=True
            ),
            OpenApiParameter(
                name='size',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Условный размер изображения QR-кода',
                required=False
            ),
        ]
    )
    def get(self, request, short):
        size = request.query_params.get('size')
        img = qrcode.make(f'https://{request.get_host()}/{short}', box_size=size if size is not None else 10)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        image_stream = buffer.getvalue()

        return HttpResponse(image_stream, content_type='image/png')


def log(link, browser, time):
    visit = Visit(link=link, browser=browser, datetime=time)
    visit.save()


class RedirectView(View):
    @staticmethod
    def get(request, short):
        try:
            link = Link.objects.get(short=short)
            thread = threading.Thread(target=log, args=(link, request.headers.get('User-Agent', ''),
                                                        datetime.now()))
            thread.start()
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


class GetMyLinksAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = LinkAndVisitLimitOffsetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Количество записей на странице (по умолчанию 10)',
                required=False
            ),
            OpenApiParameter(
                name='offset',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Смещение от начала (по умолчанию 0)',
                required=False
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=GetLinkSerializer(many=True),
                description='Список ссылок текущего пользователя с пагинацией'
            ),
            401: ErrorSerializer,
        },
        description='Получение всех ссылок текущего пользователя с пагинацией'
    )
    def get(self, request):
        queryset = Link.objects.raw('''
            SELECT l.short, l.original, COUNT(v.id) as clicks, created_at, updated_at
            FROM links l LEFT JOIN visits v ON v.link_id = l.short
            WHERE l.user_id = %s
            GROUP BY l.short, v.link_id
        ''', (request.user.id,))

        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        serializer = GetLinkSerializer(paginated_queryset, many=True, context={'request': request})

        return paginator.get_paginated_response(serializer.data)


class SearchInMyLinksAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = LinkAndVisitLimitOffsetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Количество записей на странице (по умолчанию 10)',
                required=False
            ),
            OpenApiParameter(
                name='offset',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Смещение от начала (по умолчанию 0)',
                required=False
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=GetLinkSerializer(many=True),
                description='Список ссылок, содержащих данную подстроку'
            ),
            401: ErrorSerializer,
        },
        description='Получение всех ссылок текущего пользователя с пагинацией, содержащих данную подстроку'
    )
    def get(self, request, keyword):
        queryset = Link.objects.raw('''
            SELECT l.short, l.original, 
                   COUNT(v.id) as clicks, 
                   l.created_at, 
                   l.updated_at
            FROM links l 
            LEFT JOIN visits v ON v.link_id = l.short
            WHERE l.user_id = %s 
              AND l.original ILIKE %s
            GROUP BY l.short, l.original, l.created_at, l.updated_at
        ''', [request.user.id, f'%{keyword}%'])

        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        serializer = GetLinkSerializer(paginated_queryset, many=True, context={'request': request})

        return paginator.get_paginated_response(serializer.data)


class GetVisitsByLinkAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = LinkAndVisitLimitOffsetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Количество записей на странице (по умолчанию 10)',
                required=False
            ),
            OpenApiParameter(
                name='offset',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Смещение от начала (по умолчанию 0)',
                required=False
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=VisitSerializer(many=True),
                description='Список посещений ссылки'
            ),
            401: ErrorSerializer,
        },
        description='Получение всех посещений данной ссылки'
    )
    def get(self, request, short):
        try:
            link = Link.objects.get(short=short)

            if link.user != request.user:
                return Response(
                    {'error': 'У вас нет прав для просмотра посещений этой ссылки'},
                    status=status.HTTP_403_FORBIDDEN
                )

            queryset = Visit.objects.filter(link=link)

            queryset = queryset.order_by('-datetime')

            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(queryset, request)

            serializer = VisitSerializer(paginated_queryset, many=True, context={'request': request})

            return paginator.get_paginated_response(serializer.data)

        except Link.DoesNotExist:
            return Response(
                {'error': f'Короткая ссылка "{short}" не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )


class GetLinkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: LinkSerializer,
            401: ErrorSerializer
        },
        description='Получение информации о данной ссылке'
    )
    def get(self, request, short):
        try:
            link = Link.objects.get(short=short)

            return Response(LinkSerializer(link).data)
        except Link.DoesNotExist:
            return Response(
                {'error': f'Короткая ссылка "{short}" не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )