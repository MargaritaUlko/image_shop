# shop/utils/unsplash_utils.py
import requests
from io import BytesIO
from django.core.files.images import ImageFile
import random
from django.conf import settings
UNSPLASH_ACCESS_KEY = getattr(settings, 'UNSPLASH_ACCESS_KEY')

def download_unsplash_image(query, artist):
    """Загружает случайное изображение по запросу из Unsplash"""
    try:
        # Получаем случайное изображение по запросу
        url = f"https://api.unsplash.com/photos/random"
        params = {
            'query': query,
            'client_id': UNSPLASH_ACCESS_KEY,
            'count': 1
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, list):
            data = data[0]
        
        # Загружаем полноразмерное изображение
        image_url = data['urls']['regular']
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        
        # Создаем имя файла
        filename = f"unsplash_{data['id']}.jpg"
        
        return {
            'image': ImageFile(BytesIO(image_response.content), name=filename),
            'title': f"{query.capitalize()} {random.randint(1, 100)}",
            'description': data.get('description', f"Beautiful {query} artwork"),
            'artist': artist
        }
    except Exception as e:
        print(f"Error downloading from Unsplash: {e}")
        return None