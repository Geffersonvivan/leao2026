from django.contrib import admin
from .models import Declaracao, Rendimento, Deducao, Dependente, BemDireito, GanhoCapital, VideoAjuda


class RendimentoInline(admin.TabularInline):
    model = Rendimento
    extra = 0


class DeducaoInline(admin.TabularInline):
    model = Deducao
    extra = 0


class DependenteInline(admin.TabularInline):
    model = Dependente
    extra = 0


@admin.register(Declaracao)
class DeclaracaoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'ano_base', 'modelo', 'status', 'resultado', 'atualizada_em')
    list_filter = ('status', 'modelo', 'ano_base')
    search_fields = ('usuario__email', 'usuario__first_name')
    inlines = [RendimentoInline, DeducaoInline, DependenteInline]
    readonly_fields = ('ir_devido', 'ir_retido', 'resultado', 'criada_em', 'atualizada_em')


@admin.register(BemDireito)
class BemDireitoAdmin(admin.ModelAdmin):
    list_display = ('declaracao', 'codigo', 'discriminacao', 'valor_atual')


@admin.register(GanhoCapital)
class GanhoCapitalAdmin(admin.ModelAdmin):
    list_display = ('declaracao', 'tipo_bem', 'data_alienacao', 'valor_venda', 'isento')


@admin.register(VideoAjuda)
class VideoAjudaAdmin(admin.ModelAdmin):
    list_display = ('passo', 'titulo', 'url_youtube', 'ativo')
    list_editable = ('url_youtube', 'ativo')
    ordering = ('passo',)
