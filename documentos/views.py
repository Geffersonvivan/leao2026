import os

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.conf import settings

from declaracao.models import Declaracao
from .models import Documento
from .extrator import extrair_dados
from .aplicador import aplicar_dados

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
EXTENSOES_PERMITIDAS = {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}


TIPOS_AUTO = {'informe_rendimentos', 'recibo_medico', 'boleto_escola'}


PASSO_POR_TIPO = {
    'informe_rendimentos': 'wizard_passo2',
    'recibo_medico':       'wizard_passo4',
    'boleto_escola':       'wizard_passo4',
    'outros':              'wizard_passo5',
}


@login_required
def upload(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    tipo_padrao = request.GET.get('tipo', 'informe_rendimentos')
    if tipo_padrao not in PASSO_POR_TIPO:
        tipo_padrao = 'informe_rendimentos'
    documentos = declaracao.documentos.filter(tipo=tipo_padrao).order_by('-criado_em')

    if request.method == 'POST':
        arquivos = request.FILES.getlist('arquivo')
        tipo = request.POST.get('tipo', 'outros')

        tipo_padrao = request.POST.get('tipo_padrao', 'informe_rendimentos')

        if not arquivos:
            messages.error(request, 'Selecione pelo menos um arquivo.')
            return redirect(f"{request.path}?tipo={tipo_padrao}")

        erros = []
        total_registros = 0
        docs_outros = []

        for arquivo in arquivos:
            ext = os.path.splitext(arquivo.name)[1].lower()
            if ext not in EXTENSOES_PERMITIDAS:
                erros.append(f'{arquivo.name}: formato não suportado.')
                continue
            if arquivo.size > MAX_BYTES:
                erros.append(f'{arquivo.name}: arquivo muito grande (máx. {settings.MAX_UPLOAD_SIZE_MB} MB).')
                continue

            doc = Documento.objects.create(
                declaracao=declaracao,
                tipo=tipo,
                arquivo=arquivo,
                status_processamento='pendente',
            )

            if tipo in TIPOS_AUTO:
                # Extrai e aplica automaticamente
                doc.status_processamento = 'processando'
                doc.save(update_fields=['status_processamento'])
                try:
                    dados = extrair_dados(doc)
                    doc.dados_extraidos = dados
                    if 'erro' not in dados:
                        criados = aplicar_dados(declaracao, dados)
                        total_registros += len(criados['rendimentos']) + len(criados['deducoes'])
                        doc.status_processamento = 'concluido'
                    else:
                        doc.status_processamento = 'erro'
                except Exception as e:
                    doc.dados_extraidos = {'erro': str(e)}
                    doc.status_processamento = 'erro'
                doc.save(update_fields=['dados_extraidos', 'status_processamento'])
            else:
                # "outros" — deixa pendente para revisão manual
                docs_outros.append(doc)

        for erro in erros:
            messages.error(request, erro)

        if total_registros:
            messages.success(request, f'{total_registros} registro(s) adicionado(s) à declaração.')

        # Se só tem 1 arquivo "outros", redireciona para revisão
        if not erros and len(arquivos) == 1 and docs_outros:
            return redirect('documentos_processar', pk=pk, doc_pk=docs_outros[0].pk)

        return redirect(f"{request.path}?tipo={tipo}")

    passo_retorno = PASSO_POR_TIPO.get(tipo_padrao, 'wizard_passo2')
    return render(request, 'documentos/upload.html', {
        'declaracao': declaracao,
        'documentos': documentos,
        'tipo_padrao': tipo_padrao,
        'passo_retorno': passo_retorno,
        'MAX_UPLOAD_SIZE_MB': settings.MAX_UPLOAD_SIZE_MB,
    })


@login_required
def processar(request, pk, doc_pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    documento = get_object_or_404(Documento, pk=doc_pk, declaracao=declaracao)

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'confirmar':
            if documento.dados_extraidos and 'erro' not in documento.dados_extraidos:
                criados = aplicar_dados(declaracao, documento.dados_extraidos)
                documento.status_processamento = 'concluido'
                documento.save(update_fields=['status_processamento'])

                total = (len(criados.get('rendimentos', [])) +
                         len(criados.get('deducoes', [])) +
                         len(criados.get('bens', [])))
                messages.success(request, f'{total} registro(s) adicionado(s) à declaração com sucesso.')

            tipo_doc = documento.dados_extraidos.get('tipo_documento', '')
            if tipo_doc == 'outros':
                return redirect('wizard_passo5', pk=pk)
            return redirect('wizard_passo2', pk=pk)

        elif acao == 'descartar':
            documento.status_processamento = 'erro'
            documento.save(update_fields=['status_processamento'])
            messages.info(request, 'Documento descartado. Nenhum dado foi adicionado.')
            return redirect(reverse('documentos_upload', args=[pk]) + f'?tipo={documento.tipo}')

    # GET ou primeiro acesso — faz a extração (pendente = novo; erro = reprocessar)
    if documento.status_processamento in ('pendente', 'erro'):
        documento.status_processamento = 'processando'
        documento.save(update_fields=['status_processamento'])
        try:
            dados = extrair_dados(documento)
            documento.dados_extraidos = dados
            documento.status_processamento = 'concluido' if 'erro' not in dados else 'erro'
        except Exception as e:
            documento.dados_extraidos = {'erro': str(e)}
            documento.status_processamento = 'erro'
        documento.save(update_fields=['dados_extraidos', 'status_processamento'])

    return render(request, 'documentos/processar.html', {
        'declaracao': declaracao,
        'documento': documento,
    })


@login_required
@require_POST
def remover(request, pk, doc_pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    doc = get_object_or_404(Documento, pk=doc_pk, declaracao=declaracao)
    tipo = doc.tipo
    doc.arquivo.delete(save=False)
    doc.delete()
    messages.success(request, 'Documento removido.')
    return redirect(reverse('documentos_upload', args=[pk]) + f'?tipo={tipo}')
