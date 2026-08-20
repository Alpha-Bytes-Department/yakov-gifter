from django.utils.text import slugify

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def generate_unique_slug(model_class, value, slug_field='slug'):
    slug = slugify(value)
    unique_slug = slug
    num = 1
    while model_class.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f'{slug}-{num}'
        num += 1
    return unique_slug

def normalize_email(email):
    return email.strip().lower() if email else ''
