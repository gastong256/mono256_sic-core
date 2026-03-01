from rest_framework.routers import DefaultRouter

from apps.companies.api.views import CompanyViewSet

app_name = "companies"

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")

urlpatterns = router.urls
