from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.utils import generate_unique_slug

class Category(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'sort_order']),
            models.Index(fields=['parent', 'is_active'])
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Category, self.name)
        super().save(*args, **kwargs)
        
    @property
    def full_path(self):
        path = [self.name]
        curr = self.parent
        while curr is not None:
            path.append(curr.name)
            curr = curr.parent
        return ' > '.join(reversed(path))
