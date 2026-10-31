"""Analyzers: how a field's text becomes terms. A field picks one by name in `schema.FIELDS`.

text     Prose. Case-folded words, stop words dropped, the rest stemmed.
words    Short free-form values (tags are the only user today). Case-folded words; nothing is dropped
         or stemmed, so a value can be found exactly as it was typed.
keyword  The whole value, trimmed and case-folded, as a single term.

Positions are those of the original words, so dropping a stop word leaves a gap.
"""
from . import stopwords
from .stemmer import stem
from .tokenizer import Token, tokenize

# Positions of consecutive values of a multi-valued field are this far apart, so a phrase never
# matches across two values.
VALUE_GAP = 100


def analyze_text(text):
    out = []
    for tok in tokenize(text):
        if stopwords.is_stop(tok.term):
            continue
        out.append(Token(stem(tok.term), tok.position, tok.start, tok.end))
    return out


def analyze_words(text):
    return tokenize(text)


def analyze_keyword(text):
    value = " ".join(text.split()).casefold()
    return [Token(value, 0, 0, len(text))] if value else []


ANALYZERS = {
    "text": analyze_text,
    "words": analyze_words,
    "keyword": analyze_keyword,
}


def analyze(name, text):
    return ANALYZERS[name](text)


def analyze_values(name, values):
    """Analyze each value of a field; later values are shifted by VALUE_GAP per value."""
    out = []
    for n, value in enumerate(values):
        for tok in analyze(name, value):
            out.append(Token(tok.term, tok.position + n * VALUE_GAP, tok.start, tok.end))
    return out
