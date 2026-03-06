"""
Shared tokenizer module.
Must be importable by both shield360_engine.py and app.py
so pickle can find make_tokens when loading the vectorizer.
"""

def make_tokens(f):
    tokens_by_slash = str(f).split('/')
    total_tokens = []
    for i in tokens_by_slash:
        tokens = str(i).split('-')
        tokens_dot = []
        for j in tokens:
            temp_tokens = str(j).split('.')
            tokens_dot = tokens_dot + temp_tokens
        total_tokens = total_tokens + tokens + tokens_dot
    total_tokens = list(set(total_tokens))
    for noise in ('com', 'www', 'https:', 'http:', ''):
        if noise in total_tokens:
            total_tokens.remove(noise)
    return total_tokens
