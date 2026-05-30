import csv

from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Tag


class Command(BaseCommand):
    """Management-команда для загрузки тегов в БД."""

    help = 'Загрузка тегов в БД'

    def handle(self, *args, **kwargs):
        with open(
                f'{settings.DATA_FILES_DIR}/tags.csv', encoding='utf-8'
        ) as file:
            csv_reader = csv.reader(file, delimiter=',', quotechar='"')
            amount = 0
            for row in csv_reader:
                amount += 1
                name = row[0]
                slug = row[1]
                Tag.objects.create(
                    name=name, slug=slug
                )
        self.stdout.write(
            self.style.SUCCESS(f'В БД загружно {amount} тег(ов)')
        )
