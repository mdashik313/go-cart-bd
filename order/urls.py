from django.urls import path
from .views import OrderCreateView, OrderDetailView, OrderListView

urlpatterns = [
    path("create/", OrderCreateView.as_view(), name="create-order"),
    path("list/", OrderListView.as_view(), name="list-order"),
    path("<int:pk>", OrderDetailView.as_view(), name="get-order"),
]