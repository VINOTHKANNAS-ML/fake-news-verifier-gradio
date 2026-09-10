"""Text processing utilities."""
import re
import string
from typing import List


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)

    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"').replace('\'', "'")

    return text.strip()


def extract_claims(text: str) -> List[str]:
    """Extract verifiable claims from text."""
    if not text:
        return []

    claims = []
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        # Look for claim indicators
        claim_indicators = [
            r'\b(is|are|was|were|will be|has been|have been)\b',
            r'\b(study|research|report|survey|poll)\b',
            r'\b(percent|%|million|billion|thousand)\b',
            r'\b(according to|cited by|reported by)\b',
            r'\b(said|claimed|stated|announced)\b'
        ]

        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in claim_indicators):
            claims.append(sentence)

    return claims[:10]  # Limit to top 10 claims


def calculate_text_complexity(text: str) -> dict:
    """Calculate text complexity metrics."""
    words = text.split()
    sentences = re.split(r'[.!?]+', text)

    avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
    avg_sentence_length = len(words) / len(sentences) if sentences else 0

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_word_length": round(avg_word_length, 2),
        "avg_sentence_length": round(avg_sentence_length, 2)
    }
