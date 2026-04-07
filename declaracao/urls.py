from django.urls import path
from . import views, wizard_views, importacao_views

urlpatterns = [
    # Declaração
    path('declaracao/nova/', views.nova_declaracao, name='declaracao_nova'),

    # Importação de declaração anterior
    path('declaracao/<int:pk>/importar/', importacao_views.etapa0_upload, name='importacao_etapa0'),
    path('declaracao/<int:pk>/importar/processar/', importacao_views.processar_importacao, name='importacao_processar'),
    path('declaracao/<int:pk>/importar/status/', importacao_views.status_processamento, name='importacao_status'),
    path('declaracao/<int:pk>/importar/revisar/', importacao_views.revisar_importacao, name='importacao_revisar'),
    path('declaracao/<int:pk>/importar/mudancas/', importacao_views.mudancas_checklist, name='importacao_mudancas'),
    path('declaracao/<int:pk>/', views.detalhe_declaracao, name='declaracao_detalhe'),
    path('declaracao/<int:pk>/excluir/', views.excluir_declaracao, name='declaracao_excluir'),
    path('declaracao/<int:pk>/pagamento/', views.iniciar_pagamento, name='iniciar_pagamento'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('declaracao/<int:pk>/auditoria/', views.auditoria_view, name='declaracao_auditoria'),
    path('declaracao/<int:pk>/exportar/', views.exportar_view, name='declaracao_exportar'),
    path('declaracao/<int:pk>/exportar/pdf/', views.exportar_pdf, name='declaracao_exportar_pdf'),
    path('declaracao/<int:pk>/exportar/json/', views.exportar_json, name='declaracao_exportar_json'),
    path('declaracao/<int:pk>/rendimento/novo/', views.novo_rendimento, name='rendimento_novo'),
    path('declaracao/<int:pk>/deducao/nova/', views.nova_deducao, name='deducao_nova'),
    path('declaracao/<int:pk>/dependente/novo/', views.novo_dependente, name='dependente_novo'),

    # Wizard
    path('declaracao/<int:pk>/wizard/', wizard_views.passo1_perfil, name='wizard_inicio'),
    path('declaracao/<int:pk>/wizard/1/', wizard_views.passo1_perfil, name='wizard_passo1'),
    path('declaracao/<int:pk>/wizard/2/', wizard_views.passo2_rendimentos, name='wizard_passo2'),
    path('declaracao/<int:pk>/wizard/3/', wizard_views.passo3_dependentes, name='wizard_passo3'),
    path('declaracao/<int:pk>/wizard/4/', wizard_views.passo4_deducoes, name='wizard_passo4'),
    path('declaracao/<int:pk>/wizard/5/', wizard_views.passo5_bens, name='wizard_passo5'),
    path('declaracao/<int:pk>/wizard/6/', wizard_views.passo6_revisao, name='wizard_passo6'),
    path('declaracao/<int:pk>/wizard/concluido/', wizard_views.wizard_concluido, name='wizard_concluido'),

    # Edição e remoção inline dentro do wizard
    path('declaracao/<int:pk>/wizard/rendimento/<int:rendimento_pk>/editar/',
         wizard_views.rendimento_editar, name='wizard_rendimento_editar'),
    path('declaracao/<int:pk>/wizard/rendimento/<int:rendimento_pk>/remover/',
         wizard_views.rendimento_remover, name='wizard_rendimento_remover'),
    path('declaracao/<int:pk>/wizard/dependente/<int:dependente_pk>/remover/',
         wizard_views.dependente_remover, name='wizard_dependente_remover'),
    path('declaracao/<int:pk>/wizard/deducao/<int:deducao_pk>/remover/',
         wizard_views.deducao_remover, name='wizard_deducao_remover'),
    path('declaracao/<int:pk>/wizard/bem/<int:bem_pk>/remover/',
         wizard_views.bem_remover, name='wizard_bem_remover'),
]
