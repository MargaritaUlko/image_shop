from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Artwork, CartItem, Order, User

# class LoginForm(forms.Form):
#     username = forms.CharField()
#     password = forms.CharField(widget=forms.PasswordInput)

# class RegisterForm(UserCreationForm):
#     class Meta:
#         model = User
#         fields = ['username', 'password1', 'password2']

# class AddToCartForm(forms.Form):
#     quantity = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={
#         'class': 'quantity-input',
#         'min': '1'
#     }))

class OrderForm(forms.Form):
    address = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 3,
        'placeholder': 'Введите адрес доставки'
    }))
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class AddToCartForm(forms.Form):
    class Meta:
        model = CartItem
        

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']

class ArtworkCreateForm(forms.ModelForm):
    class Meta:
        model = Artwork
        fields = ['title', 'description', 'price', 'image']  # Убрали artist
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }