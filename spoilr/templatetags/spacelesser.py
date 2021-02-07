import re

from django import template

register = template.Library()

# Copied from gph-site

@register.tag
def spacelesser(parser, token):
    nodelist = parser.parse(('endspacelesser',))
    parser.delete_first_token()
    return SpacelesserNode(nodelist)

class SpacelesserNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def replace(self, match):
        if match.start() == 0 or match.string[match.start() - 1] == '>':
            return ''
        if match.end() == len(match.string) or match.string[match.end()] == '<':
            return ''
        return ' '

    def render(self, context):
        return re.sub(r'\s+', self.replace, self.nodelist.render(context))
