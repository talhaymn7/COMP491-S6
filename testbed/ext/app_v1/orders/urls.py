from django.urls import path
from . import views
urlpatterns = [
    path("api/report/", views.report),
    path("api/<str:resource>/", views.collection),
    path("api/<str:resource>/<int:pk>/", views.detail),
]
