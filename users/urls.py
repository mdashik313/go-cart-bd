

from django.urls import path

from . import views

auth_urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshTokenView.as_view(), name="refresh"),
    path("me/", views.MeView.as_view(), name="me"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
]

address_urlpatterns = [
    path("addresses/", views.AddressListCreateView.as_view(), name="address-list-create"),
    path("addresses/<int:pk>/", views.AddressDetailView.as_view(), name="address-detail"),
    path(
        "addresses/<int:pk>/set-default/",
        views.AddressSetDefaultView.as_view(),
        name="address-set-default",
    ),
]

