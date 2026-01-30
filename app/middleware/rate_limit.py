"""
Rate limiting middleware using slowapi.

Provides in-memory rate limiting for authentication endpoints to prevent
brute force attacks and abuse.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter with get_remote_address key function
# Uses in-memory storage (default)
limiter = Limiter(key_func=get_remote_address)
