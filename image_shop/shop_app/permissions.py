# permissions.py (если требуется кастомная проверка)
from rest_framework import permissions

class IsArtistOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.groups.filter(name='Artists').exists()