from django import template

register = template.Library()

@register.filter
def percent(a, b):
    return 100 * a // b
