import csv

from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    """Management-команда для загрузки ингредиентов в БД."""

    help = 'Загрузка ингредиентов в БД'

    def handle(self, *args, **kwargs):
        with open(
                f'{settings.DATA_FILES_DIR}/ingredients.csv', encoding='utf-8'
        ) as file:
            csv_reader = csv.reader(file, delimiter=',', quotechar='"')
            amount = 0
            for row in csv_reader:
                amount += 1
                name = row[0]
                measurement_unit = row[1]
                Ingredient.objects.create(
                    name=name, measurement_unit=measurement_unit
                )
        self.stdout.write(
            self.style.SUCCESS(f'В БД загружно {amount} ингредиент(ов)')
        )
