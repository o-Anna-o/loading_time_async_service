from django.contrib import admin
from django.urls import path
from loading_time import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.set_status, name='set-status'),
]