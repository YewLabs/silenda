from django import template

register = template.Library()

def gettext(num, string):
    return '%s %s%s'%(num, string, '' if num == 1 else 's')

@register.filter
def naturalTimeDelta(timedelta):
    if not timedelta:
        return 'NEVER!'
    seconds = timedelta.total_seconds()
    if seconds < 10:
        return '%.2f seconds' % seconds
    elif seconds < 60:
        return '%.1f seconds' % seconds
    labels = ['day', 'hour', 'minute', 'second']
    counts = [24*60*60, 60*60, 60, 1]
    for i, (count, label) in enumerate(zip(counts, labels)):
        if seconds >= count:
            nextcount = counts[i+1]
            nextlabel = labels[i+1]
            num_this = int(seconds//count)
            num_next = int((seconds - num_this*count) // nextcount)
            s = gettext(num_this, label)
            if num_next and num_this < 10:
                s += ', ' + gettext(num_next, nextlabel)
            return s
