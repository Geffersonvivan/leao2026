from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, PerfilFiscal


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('email', 'get_full_name', 'cpf', 'plano', 'criado_em')
    list_filter = ('plano', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'cpf')
    fieldsets = UserAdmin.fieldsets + (
        ('Dados fiscais', {'fields': ('cpf', 'data_nascimento', 'telefone', 'plano')}),
    )


@admin.register(PerfilFiscal)
class PerfilFiscalAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_contribuinte', 'tem_dependentes', 'tem_investimentos')
    list_filter = ('tipo_contribuinte',)
