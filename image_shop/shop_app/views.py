from datetime import datetime
import os
from django.contrib import messages 
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .recommendation_engine import ArtworkRecommender
from .forms import AddToCartForm, ArtworkCreateForm, LoginForm, OrderForm, RegisterForm
import pika
import json
from django.conf import settings
from .models import Artist, Artwork, ButtonClickEvent, Cart, CartItem, Order, OrderItem
from django.template.defaulttags import register

@register.filter
def get_artwork(art_id):
    try:
        return Artwork.objects.get(id=art_id)
    except Artwork.DoesNotExist:
        return None

MODEL_PATH = os.path.join(settings.BASE_DIR, 'shop_app', 'clip-vit-base-patch32')
recommender = ArtworkRecommender(MODEL_PATH)




def artwork_recommendations(request):
    all_artworks = Artwork.objects.all()
    
    liked = request.GET.getlist('like', [])
    disliked = request.GET.getlist('dislike', [])
    
    try:
        liked_ids = [int(id) for id in liked]
        disliked_ids = [int(id) for id in disliked]
    except ValueError:
        liked_ids = []
        disliked_ids = []
    
    # Получаем лайкнутые работы для отображения
    liked_artworks = Artwork.objects.filter(id__in=liked_ids)
    
    recommended_ids = recommender.get_recommendations(
        artworks=all_artworks,
        liked_ids=liked_ids,
        disliked_ids=disliked_ids,
        top_k=10
    )
    
    recommended_artworks = Artwork.objects.filter(id__in=recommended_ids)
    order = {id: idx for idx, id in enumerate(recommended_ids)}
    recommended_artworks = sorted(recommended_artworks, key=lambda x: order[x.id])
    
    context = {
        'artworks': recommended_artworks,
        'liked_images': liked_ids,
        'liked_artworks': liked_artworks,  # Передаем объекты работ
        'disliked_images': disliked_ids
    }
    
    return render(request, 'shop/artwork_recommendations.html', context)







def artwork_list(request):
    artworks = Artwork.objects.all() 
    return render(request, 'shop/artwork_list.html', {'artworks': artworks})

@login_required
def create_artwork(request):
    if request.method == 'POST':
        form = ArtworkCreateForm(request.POST, request.FILES)
        if form.is_valid():
            artwork = form.save(commit=False)
            artwork.artist = request.user  # Присваиваем текущего пользователя
            artwork.save()
            messages.success(request, 'Картина успешно добавлена!')
            return redirect('artwork_detail', pk=artwork.id)
    else:
        form = ArtworkCreateForm()
    
    return render(request, 'shop/artwork_create.html', {'form': form})


def artwork_detail(request, pk):
    artwork = get_object_or_404(Artwork, pk=pk)
    form = AddToCartForm()
    
    if request.method == 'POST' and request.user.is_authenticated:
        form = AddToCartForm(request.POST)
        if form.is_valid():
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                artwork=artwork,
                defaults={'quantity': form.cleaned_data['quantity']}
            )
            if not created:
                cart_item.quantity += form.cleaned_data['quantity']
                cart_item.save()
            messages.success(request, 'Картина добавлена в корзину')
            return redirect('artwork_detail', pk=artwork.id)
    
    return render(request, 'shop/artwork_detail.html', {
        'artwork': artwork,
        'form': form,
    })

@login_required
def cart_view(request):
    cart = get_object_or_404(Cart, user=request.user)
    total = sum(item.artwork.price * item.quantity for item in cart.items.all())
    return render(request, 'shop/cart.html', {'cart': cart, 'total': total})

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Картина удалена из корзины')
    return redirect('cart_view')

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            total = sum(item.artwork.price * item.quantity for item in cart.items.all())
            order = Order.objects.create(
                user=request.user,
                total_price=total,
                address=form.cleaned_data['address']
            )
            
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    artwork=item.artwork,
                    quantity=item.quantity,
                    price=item.artwork.price
                )
            
            cart.items.all().delete()
            messages.success(request, 'Заказ успешно оформлен!')
            return redirect('order_detail', order_id=order.id)
    else:
        form = OrderForm()
    
    total = sum(item.artwork.price * item.quantity for item in cart.items.all())
    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'total': total,
        'form': form,
    })

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'shop/order_detail.html', {'order': order})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'shop/order_history.html', {'orders': orders})

def send_rabbitmq_event(user, artwork_id, action_type):
    try:
        credentials = pika.PlainCredentials('admin', 'admin123')
        parameters = pika.ConnectionParameters(
            host='rabbitmq',
            credentials=credentials,
            connection_attempts=3,
            retry_delay=5
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        message = {
            'user_id': user.id if user.is_authenticated else None,
            'artwork_id': artwork_id,
            'action_type': action_type,
            'timestamp': str(datetime.now())
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='user_actions',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        connection.close()
    except Exception as e:
        print(f"RabbitMQ error: {str(e)}")

# Оставьте ваши существующие функции для авторизации
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', None)
                if next_url:
                    return redirect(next_url)
                return redirect('artwork_list')
            else:
                form.add_error(None, "Неверные имя пользователя или пароль")
    else:
        form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('artwork_list')
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('artwork_list')

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', None)
                if next_url:
                    return redirect(next_url)
                return redirect('button_page')
            else:
                form.add_error(None, "Неверные имя пользователя или пароль")
    else:
        form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def button_page(request):
    if request.method == 'POST':
        ButtonClickEvent.objects.create(user=request.user)
        
        try:
            credentials = pika.PlainCredentials('admin', 'admin123')
            parameters = pika.ConnectionParameters(
                host='rabbitmq',
                credentials=credentials,
                connection_attempts=3,
                retry_delay=5
            )
            
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Создаем Exchange'ы
            channel.exchange_declare(exchange='direct_exchange', exchange_type='direct', durable=True)
            channel.exchange_declare(exchange='fanout_exchange', exchange_type='fanout', durable=True)
            channel.exchange_declare(exchange='topic_exchange', exchange_type='topic', durable=True)
            
            # Создаем очереди и привязываем их к Exchange'ам
            # Direct Exchange
            channel.queue_declare(queue='direct_queue', durable=True)
            channel.queue_bind(exchange='direct_exchange', queue='direct_queue', routing_key='direct_key')
            
            # Fanout Exchange (2 очереди)
            channel.queue_declare(queue='fanout_queue1', durable=True)
            channel.queue_declare(queue='fanout_queue2', durable=True)
            channel.queue_bind(exchange='fanout_exchange', queue='fanout_queue1')
            channel.queue_bind(exchange='fanout_exchange', queue='fanout_queue2')
            
            # Topic Exchange
            channel.queue_declare(queue='topic_queue_logs', durable=True)
            channel.queue_declare(queue='topic_queue_errors', durable=True)
            channel.queue_bind(exchange='topic_exchange', queue='topic_queue_logs', routing_key='logs.*')
            channel.queue_bind(exchange='topic_exchange', queue='topic_queue_errors', routing_key='*.error')
            
            message = {
                'user_id': request.user.id,
                'action': 'button_click',
                'timestamp': str(datetime.now())
            }
            
            # Отправка в Direct Exchange
            channel.basic_publish(
                exchange='direct_exchange',
                routing_key='direct_key',
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            # Отправка в Fanout Exchange
            channel.basic_publish(
                exchange='fanout_exchange',
                routing_key='',  # для fanout routing_key игнорируется
                body=json.dumps({**message, 'type': 'fanout'}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            # Отправка в Topic Exchange (2 разных routing key)
            channel.basic_publish(
                exchange='topic_exchange',
                routing_key='logs.info',
                body=json.dumps({**message, 'type': 'log_info'}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            channel.basic_publish(
                exchange='topic_exchange',
                routing_key='auth.error',
                body=json.dumps({**message, 'type': 'auth_error'}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            connection.close()
            return render(request, 'button.html', {
                'message': 'Кнопка нажата! Сообщения отправлены в 3 типа Exchange'
            })
            
        except Exception as e:
            print(f"RabbitMQ error: {str(e)}")
            return render(request, 'button.html', {'message': f'Ошибка: {str(e)}'})
    
    return render(request, 'button.html')



# from django.shortcuts import render
# from django.http import JsonResponse
# from rest_framework.response import Response
# from image_shop.shop_app import permissions
# from image_shop.shop_app.models import Artwork, UserActionEvent
# from image_shop.shop_app.serializers import ArtworkSerializer
# from rest_framework import generics  # Для Generic-классов (ListCreateAPIView и др.)
# from rest_framework import permissions
# # Create your views here.
# from .management.commands.service import RabbitMQ

# # def track_action(request):
# #     rabbit = RabbitMQ()
# #     rabbit.publish('user_actions', {
# #         'user_id': request.user.id,
# #         'artwork_id': request.POST['artwork_id'],
# #         'action_type': 'view'
# #     })
# #     return JsonResponse({'status': 'queued'})


# import pika
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# import json

# @csrf_exempt
# def user_actions(request):
#     if request.method == 'POST':
#         try:
#             # Подключение к RabbitMQ
#             connection = pika.BlockingConnection(
#                 pika.ConnectionParameters(
#                     host='rabbitmq',
#                     credentials=pika.PlainCredentials('admin', 'admin123')
#                 )
#             )
#             channel = connection.channel()
#             channel.queue_declare(queue='user_actions', durable=True)
            
#             # Отправка сообщения
#             channel.basic_publish(
#                 exchange='',
#                 routing_key='user_actions',
#                 body=json.dumps(request.POST),
#                 properties=pika.BasicProperties(
#                     delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
#                 )
#             )
            
#             connection.close()
#             return JsonResponse({'status': 'success'})
            
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)
    
#     return JsonResponse({'error': 'Method not allowed'}, status=405)

# class RabbitMQService:
#     _connection = None
    
#     @classmethod
#     def get_connection(cls):
#         if cls._connection is None or cls._connection.is_closed:
#             cls._connection = pika.BlockingConnection(
#                 pika.ConnectionParameters(
#                     host='rabbitmq',
#                     credentials=pika.PlainCredentials('admin', 'admin123')
#                 )
#             )
#         return cls._connection
    

# class ArtworkListCreateAPIView(generics.ListCreateAPIView):
#     queryset = Artwork.objects.select_related('artist').all()
#     serializer_class = ArtworkSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]

#     def perform_create(self, serializer):
#         # Логирование события создания
#         artwork = serializer.save()
#         UserActionEvent.objects.create(
#             user_id=self.request.user.id if self.request.user.is_authenticated else None,
#             artwork_id=artwork.id,
#             action_type='create'
#         )
#         return artwork

# class ArtworkRetrieveAPIView(generics.RetrieveAPIView):
#     queryset = Artwork.objects.select_related('artist').all()
#     serializer_class = ArtworkSerializer

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         # Логирование просмотра
#         UserActionEvent.objects.create(
#             user_id=request.user.id if request.user.is_authenticated else None,
#             artwork_id=instance.id,
#             action_type='view'
#         )
#         instance.update_view_count()  # Обновляем счетчик просмотров
#         serializer = self.get_serializer(instance)
#         return Response(serializer.data)