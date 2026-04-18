from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):
    dependencies = [
        ('links', '0002_alter_link_user'),
    ]

    operations = [
        TrigramExtension(),
    ]
