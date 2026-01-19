from django.contrib import admin
from django.urls import path
from views import ai_views

urlpatterns = [
    path('api/get/insight', ai_views.generate_insight, name="get_insight"),
    path('api/get/receipt', ai_views.parse_receipt, name="get_receipt"),
]
