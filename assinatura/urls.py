from django.urls import path
from . import views

urlpatterns = [
    path('planos/', views.planos, name='planos'),
    path('assinatura/checkout/<slug:slug>/', views.checkout, name='assinatura_checkout'),
    path('assinatura/sucesso/', views.sucesso, name='assinatura_sucesso'),
    path('assinatura/cancelado/', views.cancelado, name='assinatura_cancelado'),
    path('assinatura/webhook/', views.webhook, name='assinatura_webhook'),
]
