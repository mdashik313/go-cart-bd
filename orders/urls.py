from django.urls import path

from . import views

from payments import views as payment_views

app_name = "orders"

checkout_urlpatterns = [
    path("", views.CheckoutView.as_view(), name="checkout"),
]

customer_urlpatterns = [
    path("", views.OrderListView.as_view(), name="order-list"),
    path("<str:order_number>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("<str:order_number>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),
    path("<str:order_number>/payment/", payment_views.PaymentInitiateView.as_view(), name="order-payment-initiate"),
    path("<str:order_number>/payments/", payment_views.PaymentHistoryView.as_view(), name="order-payment-history"),
]

admin_urlpatterns = [
    path("", views.AdminOrderListView.as_view(), name="admin-order-list"),
    path("<str:order_number>/", views.AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path("<str:order_number>/status/", views.AdminOrderStatusView.as_view(), name="admin-order-status"),
]
