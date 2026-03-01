from django.urls import path

from .views import ItemCreateView, ItemDetailView, PingView

urlpatterns = [
    path("ping", PingView.as_view(), name="ping"),
    path("items", ItemCreateView.as_view(), name="item-create"),
    path("items/<uuid:pk>", ItemDetailView.as_view(), name="item-detail"),
]
