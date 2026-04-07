from django.urls import path
from . import views

urlpatterns = [
    path('declaracao/<int:pk>/documentos/', views.upload, name='documentos_upload'),
    path('declaracao/<int:pk>/documentos/<int:doc_pk>/processar/', views.processar, name='documentos_processar'),
    path('declaracao/<int:pk>/documentos/<int:doc_pk>/remover/', views.remover, name='documentos_remover'),
]
