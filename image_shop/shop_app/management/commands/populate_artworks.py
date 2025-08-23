# shop/management/commands/populate_artworks.py
from django.core.management.base import BaseCommand

import random

from requests import request

from ...models import Artist, Artwork
from ...utils.unsplash_utils import download_unsplash_image
from django.contrib.auth import get_user_model
class Command(BaseCommand):
    help = 'Populate database with test artworks from Unsplash'
    
    def handle(self, *args, **options):
        # Создаем или получаем тестовых художников
        # artists = [
        #     Artist.objects.get_or_create(name="Клод Моне")[0],
        #     Artist.objects.get_or_create(name="Винсент Ван Гог")[0],
        #     Artist.objects.get_or_create(name="Пабло Пикассо")[0],
        # ]

        # Темы для разных стилей
        styles = {
            'horror' : ['bridge', 'bridge', 'bridge'],
            # 'post-impressionism': ['starry night', 'sunflowers', 'wheat field'],
            # 'cubism': ['abstract face', 'geometric portrait', 'modern art']
        }

        # Создаем по 3 artwork для каждого стиля
        for style, queries in styles.items():
            self.stdout.write(f"Creating {style} artworks...")
            
            for query in queries:
                User = get_user_model()
                artist = User.objects.get(username="Bebrita123")
                data = download_unsplash_image(query, artist)
                
                if data:
                    artwork = Artwork.objects.create(
                        title=data['title'],
                        description="description",
                        artist=artist,
                        price=random.randint(1000, 10000),
                        image=data['image']
                    )
                    self.stdout.write(f"Created artwork: {artwork.title}")

        self.stdout.write(self.style.SUCCESS("Successfully populated artworks"))