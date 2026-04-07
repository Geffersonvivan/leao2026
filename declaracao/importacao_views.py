"""
Views do fluxo de importação da declaração anterior.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Declaracao, Rendimento, Dependente, Deducao, BemDireito, ImportacaoDeclaracao
from .importador_irpf import extrair_dados_irpf, ExtractionError


import threading
import time
import logging
from django.http import JsonResponse

log = logging.getLogger(__name__)

@login_required
def etapa0_upload(request, pk):
    """
    Etapa 0: pergunta se o usuário tem o PDF da declaração anterior.
    """
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if request.method == 'POST':
        if request.POST.get('pular'):
            return redirect('wizard_inicio', pk=pk)

        arquivo = request.FILES.get('pdf_anterior')
        if not arquivo:
            return render(request, 'declaracao/importacao/etapa0.html', {
                'declaracao': declaracao,
                'erro': 'Selecione um arquivo PDF.',
            })

        if not arquivo.name.lower().endswith('.pdf'):
            return render(request, 'declaracao/importacao/etapa0.html', {
                'declaracao': declaracao,
                'erro': 'Apenas arquivos PDF são aceitos.',
            })

        # Salva o arquivo imediatamente, marca como processando e dispara background
        importacao, _ = ImportacaoDeclaracao.objects.get_or_create(declaracao=declaracao)
        importacao.arquivo = arquivo
        importacao.dados_brutos = {}
        importacao.status = 'processando'
        importacao.save()
        
        # Dispara thread de IA
        t = threading.Thread(target=_thread_extracao_background, args=(importacao.id,))
        t.start()
        
        return redirect('importacao_processar', pk=pk)

    if hasattr(declaracao, 'importacao') and declaracao.importacao.status == 'aplicado':
        return redirect('wizard_inicio', pk=pk)

    return render(request, 'declaracao/importacao/etapa0.html', {'declaracao': declaracao})


@login_required
def processar_importacao(request, pk):
    """
    Tela de processamento: exibe spinner enquanto o frontend faz polling.
    """
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    importacao = get_object_or_404(ImportacaoDeclaracao, declaracao=declaracao)

    # Se ao chegar na tela a IA já terminou, podemos furar fila
    if importacao.status == 'revisado': return redirect('importacao_revisar', pk=pk)
    if importacao.status == 'erro':
        erro = importacao.dados_brutos.get('erro', 'Falha ao ler o PDF.')
        importacao.delete()
        return render(request, 'declaracao/importacao/etapa0.html', {'declaracao': declaracao, 'erro': erro})

    return render(request, 'declaracao/importacao/processando.html', {'declaracao': declaracao})


@login_required
def status_processamento(request, pk):
    """Retorna JSON para o polling da tela de processamento."""
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    importacao = getattr(declaracao, 'importacao', None)
    if not importacao:
        return JsonResponse({'status': 'inexistente'})
    
    return JsonResponse({
        'status': importacao.status,
        'erro': importacao.dados_brutos.get('erro', '')
    })

def _thread_extracao_background(importacao_id):
    """Executa a extração no Anthropic em plano de fundo."""
    t0 = time.time()
    log.warning(f"[THREAD] ▶ Background thread iniciada para importacao_id={importacao_id}")
    try:
        importacao = ImportacaoDeclaracao.objects.get(id=importacao_id)
        log.warning(f"[THREAD] 📁 Arquivo: {importacao.arquivo.path}")
        dados = extrair_dados_irpf(importacao.arquivo.path)
        importacao.dados_brutos = _serializar_dados(dados)
        importacao.status = 'revisado'
        importacao.save()
        log.warning(f"[THREAD] ✅ Concluído em {time.time()-t0:.2f}s — status=revisado")
    except Exception as e:
        log.warning(f"[THREAD] ❌ Erro após {time.time()-t0:.2f}s: {e}")
        try:
            importacao = ImportacaoDeclaracao.objects.get(id=importacao_id)
            importacao.status = 'erro'
            importacao.dados_brutos = {'erro': str(e)}
            importacao.save()
        except Exception as e2:
            log.warning(f"[THREAD] ❌❌ Falha ao salvar erro: {e2}")


@login_required
def revisar_importacao(request, pk):
    """
    Tela de revisão: exibe os itens extraídos do PDF para o usuário confirmar,
    editar ou descartar cada um antes de aplicar à declaração.
    """
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    importacao = get_object_or_404(ImportacaoDeclaracao, declaracao=declaracao)
    dados = importacao.dados_brutos

    if request.method == 'POST':
        _aplicar_itens_confirmados(declaracao, dados, request.POST)
        importacao.status = 'aplicado'
        importacao.save()
        return redirect('importacao_mudancas', pk=pk)

    return render(request, 'declaracao/importacao/revisao.html', {
        'declaracao': declaracao,
        'dados': dados,
        'ano_anterior': dados.get('ano_base'),
    })


@login_required
def mudancas_checklist(request, pk):
    """
    Checklist "O que mudou em [ano_base]?": perguntas geradas
    com base nos dados importados para capturar novidades.
    """
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    importacao = getattr(declaracao, 'importacao', None)
    dados = importacao.dados_brutos if importacao else {}

    perguntas = _gerar_perguntas_mudanca(declaracao, dados)

    if request.method == 'POST':
        # Processa respostas: cada "sim" adiciona um flag para o wizard
        flags = []
        for p in perguntas:
            if request.POST.get(f'p_{p["id"]}') == 'sim':
                flags.append(p['id'])

        # Salva flags na sessão para o wizard usar
        request.session[f'mudancas_{pk}'] = flags
        messages.success(
            request,
            'Ótimo! O wizard já está pré-preenchido com seus dados anteriores. '
            'Revise e complete o que mudou.'
        )
        return redirect('wizard_inicio', pk=pk)

    return render(request, 'declaracao/importacao/mudancas.html', {
        'declaracao': declaracao,
        'perguntas': perguntas,
        'ano_base': declaracao.ano_base,
    })


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serializar_dados(dados: dict) -> dict:
    """Converte Decimals para strings para armazenar no JSONField."""
    import decimal

    def converter(obj):
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        if isinstance(obj, dict):
            return {k: converter(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [converter(i) for i in obj]
        return obj

    return converter(dados)


def _aplicar_itens_confirmados(declaracao, dados, post):
    """
    Cria os objetos (Rendimento, Dependente, etc.) para os itens
    que o usuário confirmou na tela de revisão.
    """
    from decimal import Decimal

    # Rendimentos confirmados
    for i, r in enumerate(dados.get('rendimentos') or []):
        if post.get(f'rend_{i}') == 'confirmar':
            nome = post.get(f'rend_{i}_nome') or r['fonte_pagadora_nome']
            tipo = post.get(f'rend_{i}_tipo') or r['tipo']
            valor_bruto = Decimal(post.get(f'rend_{i}_bruto') or r['valor_bruto'])
            ir_retido = Decimal(post.get(f'rend_{i}_ir') or r.get('ir_retido') or '0')
            inss = Decimal(post.get(f'rend_{i}_inss') or r.get('inss_retido') or '0')
            Rendimento.objects.create(
                declaracao=declaracao,
                origem='importado',
                tipo=tipo,
                fonte_pagadora_nome=nome,
                fonte_pagadora_cnpj_cpf=r.get('cnpj') or '',
                valor_bruto=valor_bruto,
                ir_retido=ir_retido,
                inss_retido=inss,
            )

    # Dependentes confirmados
    for i, d in enumerate(dados.get('dependentes') or []):
        if post.get(f'dep_{i}') == 'confirmar':
            Dependente.objects.create(
                declaracao=declaracao,
                origem='importado',
                nome=post.get(f'dep_{i}_nome') or d['nome'],
                cpf=d.get('cpf') or '',
                data_nascimento=d.get('data_nascimento') or '2000-01-01',
                parentesco=d.get('parentesco') or 'filho',
            )

    # Deduções confirmadas
    for i, ded in enumerate(dados.get('deducoes') or []):
        if post.get(f'ded_{i}') == 'confirmar':
            valor = Decimal(post.get(f'ded_{i}_valor') or ded['valor'])
            Deducao.objects.create(
                declaracao=declaracao,
                origem='importado',
                tipo=ded.get('tipo') or 'saude',
                descricao=post.get(f'ded_{i}_desc') or ded.get('descricao') or '',
                valor=valor,
                cpf_cnpj_beneficiario=ded.get('cnpj_cpf') or '',
            )

    # Bens confirmados
    for i, b in enumerate(dados.get('bens') or []):
        if post.get(f'bem_{i}') == 'confirmar':
            # valor_anterior = valor_atual do PDF importado (31/12 do ano anterior)
            # valor_atual = 0, será preenchido pelo usuário no wizard (passo 5)
            valor_ant = Decimal(post.get(f'bem_{i}_valor_atual') or b.get('valor_atual') or '0')
            BemDireito.objects.create(
                declaracao=declaracao,
                origem='importado',
                codigo=b.get('codigo') or '99',
                discriminacao=post.get(f'bem_{i}_disc') or b['discriminacao'],
                valor_anterior=valor_ant,
                valor_atual=Decimal('0'),
            )


def _gerar_perguntas_mudanca(declaracao, dados) -> list:
    """
    Gera a lista de perguntas da checklist com base nos dados importados
    e no perfil da declaração atual.
    """
    perguntas = []
    pid = 0

    # Uma pergunta por rendimento de salário/autônomo (fonte pode ter mudado)
    for r in dados.get('rendimentos') or []:
        if r.get('tipo') in ('salario', 'autonomo', 'aluguel'):
            label = {
                'salario': f'Ainda trabalha / recebe de <strong>{r["fonte_pagadora_nome"]}</strong>?',
                'autonomo': f'Continua prestando serviços para <strong>{r["fonte_pagadora_nome"]}</strong>?',
                'aluguel': f'Continua recebendo aluguel de <strong>{r["fonte_pagadora_nome"]}</strong>?',
            }[r['tipo']]
            perguntas.append({'id': f'rend_{pid}', 'texto': label, 'acao': 'wizard_passo2'})
            pid += 1

    # Dependentes
    for d in dados.get('dependentes') or []:
        perguntas.append({
            'id': f'dep_{pid}',
            'texto': f'<strong>{d["nome"]}</strong> continua como seu dependente?',
            'acao': 'wizard_passo3',
            'inverso': True,  # "Não" → abre wizard passo 3 para remover
        })
        pid += 1

    # Perguntas fixas sobre novidades
    perguntas += [
        {
            'id': 'nova_renda',
            'texto': 'Teve alguma <strong>nova fonte de renda</strong> em '
                     f'{declaracao.ano_base} (novo emprego, freelance, etc.)?',
            'acao': 'wizard_passo2',
        },
        {
            'id': 'novo_dependente',
            'texto': f'Incluiu algum <strong>novo dependente</strong> em {declaracao.ano_base} '
                     '(filho nasceu, cônjuge, etc.)?',
            'acao': 'wizard_passo3',
        },
        {
            'id': 'bem_novo',
            'texto': f'<strong>Comprou ou vendeu</strong> algum bem em {declaracao.ano_base} '
                     '(imóvel, veículo, ações)?',
            'acao': 'wizard_passo5',
        },
        {
            'id': 'ganho_capital',
            'texto': f'Teve <strong>ganho de capital</strong> em {declaracao.ano_base} '
                     '(venda de imóvel acima de R$ 440 mil, ações, etc.)?',
            'acao': None,
        },
    ]

    return perguntas
