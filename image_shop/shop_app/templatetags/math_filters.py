from django import template

register = template.Library()

@register.filter(name='mul')
def multiply(value, arg):
    """Умножает значение на аргумент"""
    return float(value) * float(arg)