"""Shared rate limiter (per client IP)."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config import get_settings

limiter = Limiter(key_func=get_remote_address)

# endpoints that call the LLM
llm_limit = limiter.limit(lambda: get_settings().rate_limit)
# login / register: slows down password guessing
auth_limit = limiter.limit(lambda: get_settings().auth_rate_limit)
