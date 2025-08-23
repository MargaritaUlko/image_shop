from django_redis import get_redis_connection

class RedisViewCounter:
    @staticmethod
    def increment_view(artwork_id, user=None, request=None):
        redis = get_redis_connection()
        
        # Общий счетчик
        redis.incr(f"artwork:views:{artwork_id}")
        
        if user and user.is_authenticated:
            redis.sadd(f"artwork:auth_views:{artwork_id}", user.id)
        elif request:
            unique_id = ViewIdentifier.get_unique_id(request)
            redis.pfadd(f"artwork:anon_views:{artwork_id}", unique_id)

    @staticmethod
    def get_counts(artwork_id):
        redis = get_redis_connection()
        return {
            'total': int(redis.get(f"artwork:views:{artwork_id}") or 0),
            'auth': redis.scard(f"artwork:auth_views:{artwork_id}"),
            'anon': redis.pfcount(f"artwork:anon_views:{artwork_id}")
        }

class ViewIdentifier:
    @staticmethod
    def get_unique_id(request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        return f"{ip}:{user_agent}"