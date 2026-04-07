from django.urls import path
from . import views

urlpatterns = [
    path('assistente/<int:pk>/', views.chat, name='assistente_chat'),
    path('assistente/<int:pk>/mensagem/', views.mensagem, name='assistente_mensagem'),
]
