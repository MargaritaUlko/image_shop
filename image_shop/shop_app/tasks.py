# shop_app/tasks.py
from celery import shared_task
from django.core.cache import cache
from django.conf import settings
import os

from .recommendation_engine import ArtworkRecommender
from .models import Artwork, Like

MODEL_PATH = os.path.join(settings.BASE_DIR, 'shop_app', 'clip-vit-base-patch32')

# @shared_task(bind=True)
@shared_task
def generate_recommendations_task(user_id, liked_ids, disliked_ids, top_k=8, cache_key=None):
    """Генерация рекомендаций в фоновом режиме"""
    try:
        print(f"🚀 [CELERY] Начинаем генерацию для пользователя {user_id}")
        
        if not cache_key:
            liked_hash = hash(tuple(sorted(liked_ids))) if liked_ids else 0
            disliked_hash = hash(tuple(sorted(disliked_ids))) if disliked_ids else 0
            cache_key = f'recommendations_{user_id}_{liked_hash}_{disliked_hash}'
        
        print(f"🔑 [CELERY] Используем ключ кэша: {cache_key}")
        
        if not os.path.exists(MODEL_PATH):
            print(f"❌ [CELERY] Модель не найдена: {MODEL_PATH}")
            raise Exception(f"Model not found at {MODEL_PATH}")
        
        print(f"✅ [CELERY] Модель найдена: {MODEL_PATH}")
        
        recommender = ArtworkRecommender(MODEL_PATH)
        print(f"✅ [CELERY] Recommender инициализирован")
        
        all_artworks = Artwork.objects.all()
        print(f"📊 [CELERY] Загружено {all_artworks.count()} произведений")
        
        print(f"🔄 [CELERY] Генерируем рекомендации...")
        recommended_ids = recommender.get_recommendations(
            artworks=all_artworks,
            liked_ids=liked_ids or [],
            disliked_ids=disliked_ids or [],
            top_k=top_k
        )
        
        print(f"🎯 [CELERY] Получено {len(recommended_ids)} рекомендаций")
        
        cache_data = {
            'recommended_ids': recommended_ids,
            'liked_ids': liked_ids or [],
            'disliked_ids': disliked_ids or []
        }
        
        cache.set(cache_key, cache_data, timeout=3600)
        print(f"💾 [CELERY] Данные сохранены в кэш: {cache_key}")
        
        test_data = cache.get(cache_key)
        if test_data:
            print(f"✅ [CELERY] Кэш работает! Данные найдены.")
            print(f"📋 [CELERY] Содержимое кэша: рекомендаций={len(test_data.get('recommended_ids', []))}")
        else:
            print(f"❌ [CELERY] Проблема с кэшем! Данные не найдены.")
            cache.set(cache_key, cache_data, timeout=3600)
            test_data_retry = cache.get(cache_key)
            if test_data_retry:
                print(f"✅ [CELERY] Повторное сохранение успешно!")
            else:
                print(f"❌ [CELERY] Повторное сохранение не удалось!")
        
        print(f"✅ [CELERY] Задача завершена успешно для пользователя {user_id}")
        
        return {
            'status': 'success', 
            'user_id': user_id,
            'count': len(recommended_ids),
            'cache_key': cache_key
        }
        
    except Exception as exc:
        print(f"❌ [CELERY] Ошибка при генерации рекомендаций: {str(exc)}")
        import traceback
        print(f"❌ [CELERY] Полная ошибка: {traceback.format_exc()}")
        
        if cache_key:
            error_data = {
                'status': 'error',
                'error': str(exc),
                'user_id': user_id
            }
            cache.set(f"{cache_key}_error", error_data, timeout=300)  
        
        raise exc