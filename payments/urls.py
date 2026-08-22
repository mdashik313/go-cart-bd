from django.urls import path

from . import views

app_name = "payments"

webhook_urlpatterns = [
    path("webhook/", views.PaymentWebhookView.as_view(), name="webhook"),
]

admin_urlpatterns = [
    path("", views.AdminPaymentListView.as_view(), name="admin-payment-list"),
    path("<int:payment_id>/", views.AdminPaymentDetailView.as_view(), name="admin-payment-detail"),
    path("<int:payment_id>/refund/", views.AdminPaymentRefundView.as_view(), name="admin-payment-refund"),
]
