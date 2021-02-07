import re

def normalize_answer(answer):
    regex = re.compile('[^A-Z]')
    return regex.sub('', answer.upper())
