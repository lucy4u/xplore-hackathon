from django.urls import path
from . import views
app_name = 'carbon_footprint'
urlpatterns = [
    path('log/', views.log_transport, name='log_transport'),
    path('dashboard/', views.dashboard, name='dashboard'),
]