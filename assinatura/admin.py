from django.contrib import admin
from .models import Plano, Assinatura


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'preco_anual', 'max_declaracoes', 'chat_ilimitado', 'destaque', 'ativo')
    prepopulated_fields = {'slug': ('nome',)}
    list_editable = ('ativo', 'destaque')


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'plano', 'status', 'valida_ate', 'criada_em')
    list_filter = ('status', 'plano')
    search_fields = ('usuario__email', 'stripe_session_id', 'stripe_customer_id')
    readonly_fields = ('stripe_session_id', 'stripe_customer_id', 'stripe_payment_intent', 'criada_em', 'atualizada_em')
