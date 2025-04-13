import re
import unicodedata
from typing import Optional

def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    Handles special characters, including Vietnamese.
    
    Args:
        text: The text to convert to a slug
        
    Returns:
        A URL-friendly slug
    """
    # Normalize Unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Replace Vietnamese characters
    vietnamese_chars = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y'
    }
    
    for vietnamese, latin in vietnamese_chars.items():
        text = text.replace(vietnamese, latin)
        text = text.replace(vietnamese.upper(), latin.upper())
    
    # Convert to ASCII, keep only alphanumeric chars
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    
    # Replace spaces and other separators with hyphens
    text = re.sub(r'[-\s]+', '-', text)
    
    return text

def generate_unique_slug(title: str, existing_slugs: list = None, max_length: int = 100) -> str:
    """
    Generate a unique slug from a title.
    
    Args:
        title: The title to generate a slug from
        existing_slugs: List of existing slugs to check against for uniqueness
        max_length: Maximum length of the slug
        
    Returns:
        A unique slug
    """
    slug = slugify(title)[:max_length]
    
    if not existing_slugs:
        return slug
    
    if slug not in existing_slugs:
        return slug
    
    # If slug already exists, append a number
    original_slug = slug
    counter = 1
    
    while slug in existing_slugs:
        # Make room for the counter suffix
        suffix = f"-{counter}"
        slug = f"{original_slug[:max_length - len(suffix)]}{suffix}"
        counter += 1
    
    return slug 