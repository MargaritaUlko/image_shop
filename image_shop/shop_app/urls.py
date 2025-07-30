from django.contrib import admin
from django.urls import path

from shop_app import views
# from shop_app.views import ArtworkListCreateAPIView, ArtworkRetrieveAPIView, user_actions


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('button/', views.button_page, name='button_page'),
    path('', views.artwork_list, name='artwork_list'),
    path('artwork/<int:pk>/', views.artwork_detail, name='artwork_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/', views.order_history, name='order_history'),
    path('artwork/create/', views.create_artwork, name='create_artwork'),
    path('recommendations/', views.artwork_recommendations, name='artwork_recommendations'),
]