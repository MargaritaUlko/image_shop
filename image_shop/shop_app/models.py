from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
# Create your models here.
from django.db import models

from .services.redis_service import RedisViewCounter
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
# class ArtworkRecommendation(models.Model):
#     # SOURCE_TYPES = [
#     #     ('tags', 'Теги'),
#     #     ('artist', 'Автор'),
#     #     ('hybrid', 'Гибридная'),
#     # ]
    
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Изменено здесь
#     artwork = models.ForeignKey('Artwork', on_delete=models.CASCADE)
#     score = models.FloatField(default=0.0)
#     # source = models.CharField(max_length=10, choices=SOURCE_TYPES)
#     expires_at = models.DateTimeField()

#     class Meta:
#         unique_together = ('user', 'artwork')


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
    def record_view(self, user=None, request=None):
        """Интерфейс для регистрации просмотра"""
        RedisViewCounter.increment_view(self.id, user, request)
    
    @property
    def view_stats(self):
        """Получение статистики просмотров"""
        return RedisViewCounter.get_counts(self.id)['total']
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
        ('payment_processing', 'Обработка платежа'),
        ('paid', 'Оплачено'),
        ('shipped', 'Отправлено'),
        ('delivered', 'Доставлено'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
        ('refunded', 'Возвращен'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.TextField(null=True)  # Добавляем адрес доставки
    
    def __str__(self):
        return f"Order #{self.id}"
    
    @property
    def seller(self):
        # Предполагаем что в заказе все картины от одного продавца
        first_item = self.items.first()
        return first_item.artwork.artist if first_item else None
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

class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE)
    liked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'artwork')
class ButtonClickEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def create_from_event(cls, user, event_data):
        return cls.objects.create(user=user)
    

class EscrowTransaction(models.Model):
    STATUS_CHOICES = [
        ('waiting_payment', 'Ожидание оплаты'),
        ('funds_held', 'Средства заблокированы'),
        ('shipped', 'Товар отправлен'),
        ('delivered', 'Доставлено'),
        ('completed', 'Завершено'),
        ('timeout_refunded', 'Возврат по таймауту'),
        ('cancelled', 'Отменено'),
        ('disputed', 'Спор'),
    ]
    
    payment_id = models.CharField(max_length=100, unique=True)  # ID платежа в ЮKassa
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='escrow')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='escrow_purchases')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='escrow_sales')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Статус и временные метки
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting_payment')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    track_number = models.CharField(max_length=100, blank=True)
    shipping_service = models.CharField(max_length=50, default='pochta_russia')
    
    delivery_address = models.TextField()
    
    yookassa_payment_data = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Escrow #{self.id} - {self.status}"
    
    @property
    def can_be_shipped(self):
        return self.status == 'funds_held'
    
    @property
    def can_be_confirmed(self):
        return self.status == 'shipped'
    
    @property
    def days_since_shipped(self):
        if self.shipped_at:
            return (timezone.now() - self.shipped_at).days
        return 0

class DeliveryTracking(models.Model):
    escrow = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE, related_name='tracking')
    track_number = models.CharField(max_length=100)
    last_status = models.CharField(max_length=100, blank=True)
    last_check = models.DateTimeField(null=True, blank=True)
    is_delivered = models.BooleanField(default=False)
    delivery_attempts = models.IntegerField(default=0)
    
    status_history = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"Tracking {self.track_number}"
# class Order(models.Model):
#     STATUS_CHOICES = (
#         ('pending', 'В обработке'),
#         ('completed', 'Завершен'),
#         ('cancelled', 'Отменен'),
#     )
    
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
#     total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
#     def __str__(self):
#         return f"Order #{self.id}"