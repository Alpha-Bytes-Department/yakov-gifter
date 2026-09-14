from decouple import config

# Defaults to production. A missing or misspelled DJANGO_ENV on a server used to
# fall through to development settings, which turn on DEBUG, allow every host
# and open CORS to all origins — a silent, outward-facing failure. Developers
# opt in to development explicitly (see .env.example).
DJANGO_ENV = config('DJANGO_ENV', default='production')

if DJANGO_ENV == 'development':
    from .development import *  # noqa: F401,F403
else:
    from .production import *  # noqa: F401,F403
