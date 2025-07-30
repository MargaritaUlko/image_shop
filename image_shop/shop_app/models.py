from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
# Create your models here.
from django.db import models
# from django.contrib.auth.models import User


class User(AbstractUser):
    class Meta:
        db_table = 'auth_user'

# 1. Модель для RabbitMQ-совместимых событий
# class UserActionEvent(models.Model):
#     ACTION_TYPES = [
#         ('view', 'Просмотр'),
#         ('like', 'Лайк'),
#         ('purchase', 'Покупка'),
#     ]
    
#     user_id = models.IntegerField(null=True, blank=True)  # Для анонимных пользователей
#     session_id = models.CharField(max_length=255)  # Идентификатор сессии
#     artwork_id = models.IntegerField()  # Не ForeignKey для ускорения записи
#     action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
#     timestamp = models.DateTimeField(auto_now_add=True)
#     duration_sec = models.IntegerField(default=0)
#     is_processed = models.BooleanField(default=False)  # Для фоновой обработки

#     class Meta:
#         indexes = [
#             models.Index(fields=['timestamp']),  # Для аналитики по времени
#             models.Index(fields=['artwork_id', 'action_type']),  # Для топ-N
#         ]
class UserActionEvent(models.Model):
    user_id = models.BigIntegerField(null=True)
    artwork_id = models.BigIntegerField()
    action_type = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def create_from_event(cls, event_data):
        return cls.objects.create(
            user_id=event_data.get('user_id'),
            artwork_id=event_data['artwork_id'],
            action_type=event_data['action_type']
        )
# 2. Модель для рекомендаций (кеш в Redis + БД)
class ArtworkRecommendation(models.Model):
    SOURCE_TYPES = [
        ('tags', 'Теги'),
        ('artist', 'Автор'),
        ('hybrid', 'Гибридная'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Изменено здесь
    artwork = models.ForeignKey('Artwork', on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    source = models.CharField(max_length=10, choices=SOURCE_TYPES)
    expires_at = models.DateTimeField()

    class Meta:
        unique_together = ('user', 'artwork')

# 3. Оптимизированная модель картины
class Artwork(models.Model):
    title = models.CharField(max_length=200)
    artist= models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tags = models.ManyToManyField('Tag')
    view_count = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='artworks/', default='artworks/default.jpg')
    created_at = models.DateTimeField(default=timezone.now)   # Денормализация для скорости

    def update_view_count(self):
        self.view_count = UserActionEvent.objects.filter(
            artwork_id=self.id, 
            action_type='view'
        ).count()
        self.save()

class Artist(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
    
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'В обработке'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"Order #{self.id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE)
    # quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} x {self.artwork.title}"

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart of {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)


class ButtonClickEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def create_from_event(cls, user, event_data):
        return cls.objects.create(user=user)