

import os
import django

from ...models import Artwork

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'image_shop.settings')
django.setup()


artworks = Artwork.objects.all() 
print(artworks)