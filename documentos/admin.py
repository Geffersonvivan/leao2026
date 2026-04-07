from django.contrib import admin
from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('declaracao', 'tipo', 'status_processamento', 'criado_em')
    list_filter = ('tipo', 'status_processamento')
    readonly_fields = ('dados_extraidos', 'criado_em')
