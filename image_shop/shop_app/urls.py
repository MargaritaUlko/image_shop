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
    path('artworks/<int:pk>/add-to-cart/', views.artwork_add_to_cart, name='add_to_cart'),
    path('artworks/<int:item_id>/remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),

    path('artworks/<int:pk>/like/', views.artwork_add_to_favorites, name='add_to_fav'),
    path('artworks/<int:artwork_id>/remove_like/', views.remove_from_favorites, name='remove_to_fav'),
    

    
    path('profile/', views.ProfilePage.as_view(), name='profile_page'),
    path('cart/', views.cart_view, name='cart_view'),
    path('favorites/', views.view_favorites, name='favorites_view'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/', views.order_history, name='order_history'),
    path('artwork/create/', views.ArtworkCreateView.as_view(), name='create_artwork'),
    path('recommendations/', views.artwork_recommendations, name='artwork_recommendations'),
    path('accounts/merge-cart/', views.merge_cart, name='merge_cart'),




    # path('recommendations/', views.artwork_recommendations, name='artwork_recommendations'),
    path('recommendations/', views.artwork_recommendations, name='artwork_recommendations'),
    path('api/recommendations-status/', views.recommendations_status_api, name='recommendations_status_api'),
    
]