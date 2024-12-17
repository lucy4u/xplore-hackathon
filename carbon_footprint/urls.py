from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'carbon_footprint'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', LogoutView.as_view(next_page='carbon_footprint:login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
]