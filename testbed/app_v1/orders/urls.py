from django.urls import path
from . import views
urlpatterns = [
    path("orders/", views.orders),
    path("orders/<int:pk>/", views.order_detail),
    path("report/", views.report),
]
