#generate_api_key.py
import secrets
print(secrets.token_urlsafe(48))   # ~64–70 chars, URL-safe
