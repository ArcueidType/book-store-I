import jieba
from jieba.analyse import textrank
import re


def get_keywords(text) -> list:
    if not isinstance(text, str):
        return []

    text = re.sub(r'\n+', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.replace(' ', '，')
    keywords = textrank(text)
    return keywords


def get_prefix(text) -> list:
    if not isinstance(text, str):
        return []

    prefix = []
    for i in range(1, len(text) + 1):
        prefix.append(text[:i])
    return prefix


def get_words_suffix(text) -> list:
    if not isinstance(text, str):
        return []

    suffix = []
    words = jieba.lcut(text)
    sub_text = ''
    length = len(words)
    for i in range(length):
        sub_text = words[length - i - 1] + sub_text
        suffix += get_prefix(sub_text)
    suffix = list(set(suffix))
    return suffix


def parse_country_author(text) -> (str, str):
    if not isinstance(text, str):
        return '', ''

    country, author = '', ''
    country_state = False

    for char in text:
        if char in ')]}）】」':
            country_state = False
        elif char in '([{（【「':
            country_state = True
            if country != '':
                country += '_'
        elif country_state:
            country += char
        else:
            author += char

    return country, author


def parse_name(text) -> list:
    if not isinstance(text, str):
        return []

    names = []
    name_buff = ''
    for char in text:
        name_buff += char
        if char in '·・ ,，.':
            if name_buff != '':
                names.append(name_buff)
            name_buff = ''
    if name_buff != '':
        names.append(name_buff)

    return names
