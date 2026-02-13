"""
Vocabulary service for Story Engine.
Builds a word list from tiktoken tokenizer validated against NLTK dictionary.
Lazy-builds on first use, cached for subsequent calls.
"""

import random
import logging
import threading

logger = logging.getLogger(__name__)

# Module-level cache
_vocab_words = None
_vocab_lock = threading.Lock()


def _build_vocab(max_id=75000, min_len=4, max_len=15):
    """Build vocabulary from tiktoken tokens validated against NLTK dictionary."""
    import tiktoken
    import nltk

    nltk.download('words', quiet=True)
    from nltk.corpus import words as nltk_words

    english_dict = set(w.lower() for w in nltk_words.words())

    enc = tiktoken.get_encoding("cl100k_base")
    real_words = []

    for i in range(max_id):
        try:
            token = enc.decode([i])
            if token.startswith(" "):
                word = token.strip().lower()
                if (word.isalpha() and
                        min_len <= len(word) <= max_len and
                        word in english_dict):
                    real_words.append(word)
        except Exception:
            continue

    return list(set(real_words))


def _get_vocab():
    """Get or build the vocabulary (thread-safe, lazy)."""
    global _vocab_words
    if _vocab_words is not None:
        return _vocab_words

    with _vocab_lock:
        # Double-check after acquiring lock
        if _vocab_words is not None:
            return _vocab_words
        logger.info("Building vocabulary from tiktoken + NLTK...")
        _vocab_words = _build_vocab()
        logger.info(f"Vocabulary built: {len(_vocab_words)} words")
        return _vocab_words


def warm_up():
    """Pre-warm the vocabulary cache. Call from a background thread at startup."""
    _get_vocab()


def sample_words(n=20):
    """Sample n random words from the vocabulary."""
    vocab = _get_vocab()
    return random.sample(vocab, min(n, len(vocab)))
