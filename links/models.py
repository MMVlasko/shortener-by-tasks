from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import GinIndex


class Link(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['original'], name='link_original_idx'),
            GinIndex(
                name='link_original_trgm_idx',
                fields=['original'],
                opclasses=['gin_trgm_ops']
            )
        ]
        db_table = 'links'

    short = models.CharField(
        'Короткая ссылка',
        max_length=6,
        unique=True,
        primary_key=True
    )

    original = models.TextField('Оригинальная ссылка', null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='links',
        null=True
    )

    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
