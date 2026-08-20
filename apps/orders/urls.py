from rest_framework.routers import DefaultRouter
from apps.orders.views import OrderViewSet

router = DefaultRouter()
router.register(r'', OrderViewSet, basename='orders')
urlpatterns = router.urls
