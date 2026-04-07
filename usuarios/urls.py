from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/registro/', views.registro_view, name='registro'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/verificar-email/<str:token>/', views.verificar_email_view, name='verificar_email'),
    path('auth/reenviar-verificacao/', views.reenviar_verificacao_view, name='reenviar_verificacao'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('verificar-obrigatoriedade/', views.verificar_obrigatoriedade, name='verificar_obrigatoriedade'),
]
