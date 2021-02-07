from django import template
import math

register = template.Library()

@register.filter
def scav_hunt_points(size):
    try:
        size = float(size)
    except:
        size = 100
    return 13 + math.ceil(size/3.+math.sqrt(size)/2.)
