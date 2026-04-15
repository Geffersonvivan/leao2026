"""
Views do Wizard de declaração — passo a passo guiado.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages

from decimal import Decimal

from usuarios.models import PerfilFiscal
from .models import Declaracao, Rendimento, Dependente, Deducao, BemDireito, VideoAjuda
from .calculadora import recomendar_modelo, calcular_resultado_final, TIPOS_TRIBUTACAO_EXCLUSIVA

PASSOS = [
    {'numero': 1, 'nome': 'Perfil'},
    {'numero': 2, 'nome': 'Rendimentos'},
    {'numero': 3, 'nome': 'Dependentes'},
    {'numero': 4, 'nome': 'Deduções'},
    {'numero': 5, 'nome': 'Bens'},
    {'numero': 6, 'nome': 'Revisão'},
]


def _ctx(declaracao, passo_atual, passo_titulo):
    video = VideoAjuda.objects.filter(passo=passo_atual, ativo=True).exclude(url_youtube='').first()
    return {
        'declaracao': declaracao,
        'passo_atual': passo_atual,
        'passo_titulo': passo_titulo,
        'total_passos': len(PASSOS),
        'passos': PASSOS,
        'video_ajuda': video,
    }


def _importacao_ctx(declaracao, request):
    """Contexto relacionado à importação: se houve import e quais mudanças o usuário sinalizou."""
    mudancas_flags = request.session.get(f'mudancas_{declaracao.pk}', [])
    tem_importacao = (
        hasattr(declaracao, 'importacao')
        and declaracao.importacao.status == 'aplicado'
    )
    return {
        'tem_importacao': tem_importacao,
        'mudancas_flags': mudancas_flags,
    }


# ─── Passo 1 — Perfil ────────────────────────────────────────────────────────

@login_required
def passo1_perfil(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    perfil, _ = PerfilFiscal.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        perfil.tipo_contribuinte = request.POST.get('tipo_contribuinte', '')
        perfil.tem_dependentes   = 'tem_dependentes' in request.POST
        perfil.tem_imoveis       = 'tem_imoveis' in request.POST
        perfil.tem_investimentos = 'tem_investimentos' in request.POST
        perfil.tem_dividas       = 'tem_dividas' in request.POST
        perfil.save()
        return redirect('wizard_passo2', pk=pk)

    tipos = PerfilFiscal.TIPO_CHOICES
    ctx = _ctx(declaracao, 1, 'Perfil')
    ctx.update({'perfil': perfil, 'tipos': tipos})
    ctx.update(_importacao_ctx(declaracao, request))
    return render(request, 'declaracao/wizard/passo1_perfil.html', ctx)


# ─── Passo 2 — Rendimentos ───────────────────────────────────────────────────

@login_required
def passo2_rendimentos(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'adicionar':
            try:
                Rendimento.objects.create(
                    declaracao=declaracao,
                    tipo=request.POST['tipo'],
                    fonte_pagadora_nome=request.POST['fonte_pagadora_nome'],
                    fonte_pagadora_cnpj_cpf=request.POST.get('fonte_pagadora_cnpj_cpf', ''),
                    valor_bruto=request.POST['valor_bruto'],
                    ir_retido=request.POST.get('ir_retido') or 0,
                    inss_retido=request.POST.get('inss_retido') or 0,
                )
            except Exception as e:
                ctx = _ctx(declaracao, 2, 'Rendimentos')
                ctx.update({'rendimentos': declaracao.rendimentos.all(), 'erro': str(e)})
                return render(request, 'declaracao/wizard/passo2_rendimentos.html', ctx)

        elif acao == 'avancar':
            if not declaracao.rendimentos.exists():
                ctx = _ctx(declaracao, 2, 'Rendimentos')
                ctx.update({
                    'rendimentos': declaracao.rendimentos.all(),
                    'erro': 'Adicione pelo menos um rendimento para continuar.',
                })
                return render(request, 'declaracao/wizard/passo2_rendimentos.html', ctx)
            return redirect('wizard_passo3', pk=pk)

    ctx = _ctx(declaracao, 2, 'Rendimentos')
    ctx['rendimentos'] = declaracao.rendimentos.all()
    ctx['perfil'] = getattr(request.user, 'perfil_fiscal', None)
    ctx.update(_importacao_ctx(declaracao, request))
    return render(request, 'declaracao/wizard/passo2_rendimentos.html', ctx)


@login_required
@require_POST
def rendimento_remover(request, pk, rendimento_pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    Rendimento.objects.filter(pk=rendimento_pk, declaracao=declaracao).delete()
    return redirect('wizard_passo2', pk=pk)


@login_required
@require_POST
def rendimento_editar(request, pk, rendimento_pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    r = get_object_or_404(Rendimento, pk=rendimento_pk, declaracao=declaracao)
    r.tipo = request.POST.get('tipo', r.tipo)
    r.fonte_pagadora_nome = request.POST.get('fonte_pagadora_nome', r.fonte_pagadora_nome)
    r.fonte_pagadora_cnpj_cpf = request.POST.get('fonte_pagadora_cnpj_cpf', r.fonte_pagadora_cnpj_cpf)
    r.valor_bruto = request.POST.get('valor_bruto') or r.valor_bruto
    r.ir_retido = request.POST.get('ir_retido') or 0
    r.inss_retido = request.POST.get('inss_retido') or 0
    r.save()
    return redirect('wizard_passo2', pk=pk)


# ─── Passo 3 — Dependentes ───────────────────────────────────────────────────

@login_required
def passo3_dependentes(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'adicionar':
            try:
                Dependente.objects.create(
                    declaracao=declaracao,
                    nome=request.POST['nome'],
                    cpf=request.POST['cpf'],
                    data_nascimento=request.POST['data_nascimento'],
                    parentesco=request.POST['parentesco'],
                )
            except Exception as e:
                ctx = _ctx(declaracao, 3, 'Dependentes')
                ctx.update({'dependentes': declaracao.dependentes.all(), 'erro': str(e)})
                return render(request, 'declaracao/wizard/passo3_dependentes.html', ctx)

        elif acao == 'avancar':
            return redirect('wizard_passo4', pk=pk)

    ctx = _ctx(declaracao, 3, 'Dependentes')
    ctx['dependentes'] = declaracao.dependentes.all()
    ctx.update(_importacao_ctx(declaracao, request))
    return render(request, 'declaracao/wizard/passo3_dependentes.html', ctx)


@login_required
@require_POST
def dependente_remover(request, pk, dependente_pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    Dependente.objects.filter(pk=dependente_pk, declaracao=declaracao).delete()
    return redirect('wizard_passo3', pk=pk)


# ─── Passo 4 — Deduções ──────────────────────────────────────────────────────

@login_required
def passo4_deducoes(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'adicionar':
            try:
                Deducao.objects.create(
                    declaracao=declaracao,
                    tipo=request.POST['tipo'],
                    descricao=request.POST['descricao'],
                    valor=request.POST['valor'],
                    cpf_cnpj_beneficiario=request.POST.get('cpf_cnpj_beneficiario', ''),
                )
            except Exception as e:
                ctx = _ctx(declaracao, 4, 'Deduções')
                ctx.update({'deducoes': declaracao.deducoes.all(), 'erro': str(e)})
                return render(request, 'declaracao/wizard/passo4_deducoes.html', ctx)

        elif acao == 'avancar':
            return redirect('wizard_passo5', pk=pk)

    ctx = _ctx(declaracao, 4, 'Deduções')
    ctx['deducoes'] = declaracao.deducoes.all()
    ctx.update(_importacao_ctx(declaracao, request))
    return render(request, 'declaracao/wizard/passo4_deducoes.html', ctx)


@login_required
@require_POST
def deducao_remover(request, pk, deducao_pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    Deducao.objects.filter(pk=deducao_pk, declaracao=declaracao).delete()
    return redirect('wizard_passo4', pk=pk)


# ─── Passo 5 — Bens e Direitos ───────────────────────────────────────────────

@login_required
def passo5_bens(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'adicionar':
            try:
                BemDireito.objects.create(
                    declaracao=declaracao,
                    codigo=request.POST['codigo'],
                    discriminacao=request.POST['discriminacao'],
                    valor_atual=request.POST['valor_atual'],
                    valor_anterior=request.POST.get('valor_anterior') or 0,
                )
            except Exception as e:
                ctx = _ctx(declaracao, 5, 'Bens e Direitos')
                ctx.update(_importacao_ctx(declaracao, request))
                ctx.update(_bens_ctx(declaracao))
                ctx['erro'] = str(e)
                return render(request, 'declaracao/wizard/passo5_bens.html', ctx)

        elif acao == 'atualizar_bem':
            bem_pk = request.POST.get('bem_pk')
            valor = request.POST.get('valor_atual_novo', '0')
            try:
                bem = get_object_or_404(BemDireito, pk=bem_pk, declaracao=declaracao)
                bem.valor_atual = Decimal(valor)
                bem.save(update_fields=['valor_atual'])
            except Exception:
                pass

        elif acao == 'editar_bem':
            bem_pk = request.POST.get('bem_pk')
            try:
                bem = get_object_or_404(BemDireito, pk=bem_pk, declaracao=declaracao)
                bem.codigo = request.POST.get('codigo', bem.codigo)
                bem.discriminacao = request.POST.get('discriminacao', bem.discriminacao)
                bem.valor_atual = Decimal(request.POST.get('valor_atual') or '0')
                bem.valor_anterior = Decimal(request.POST.get('valor_anterior') or '0')
                bem.save(update_fields=['codigo', 'discriminacao', 'valor_atual', 'valor_anterior'])
            except Exception:
                pass

        elif acao == 'avancar':
            return redirect('wizard_passo6', pk=pk)

        return redirect('wizard_passo5', pk=pk)

    ctx = _ctx(declaracao, 5, 'Bens e Direitos')
    ctx.update(_importacao_ctx(declaracao, request))
    ctx.update(_bens_ctx(declaracao))
    return render(request, 'declaracao/wizard/passo5_bens.html', ctx)


def _bens_ctx(declaracao):
    """Separa bens importados que precisam de valor atual dos demais."""
    todos = declaracao.bens.all()
    pendentes = [b for b in todos if b.origem == 'importado' and b.valor_atual == 0]
    confirmados = [b for b in todos if not (b.origem == 'importado' and b.valor_atual == 0)]
    return {'bens': confirmados, 'bens_importados_pendentes': pendentes}


@login_required
@require_POST
def bem_remover(request, pk, bem_pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    BemDireito.objects.filter(pk=bem_pk, declaracao=declaracao).delete()
    return redirect('wizard_passo5', pk=pk)


# ─── Passo 6 — Revisão ───────────────────────────────────────────────────────

@login_required
def passo6_revisao(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if not declaracao.rendimentos.exists():
        messages.warning(request, 'Adicione rendimentos antes de revisar.')
        return redirect('wizard_passo2', pk=pk)

    simulacao = recomendar_modelo(declaracao)
    resultado = calcular_resultado_final(declaracao)
    alertas = _gerar_alertas(declaracao, resultado)

    if request.method == 'POST':
        modelo = request.POST.get('modelo_escolhido', simulacao['recomendado'])
        resultado_final = calcular_resultado_final(declaracao, modelo)
        declaracao.modelo = modelo
        declaracao.ir_devido = resultado_final['ir_devido']
        declaracao.ir_retido = resultado_final['ir_retido']
        declaracao.resultado = resultado_final['resultado']
        declaracao.status = 'pronta'
        declaracao.save()
        return redirect('wizard_concluido', pk=pk)

    ctx = _ctx(declaracao, 6, 'Revisão')
    ctx.update({'simulacao': simulacao, 'resultado': resultado, 'alertas': alertas})
    return render(request, 'declaracao/wizard/passo6_revisao.html', ctx)


def _gerar_alertas(declaracao, resultado):
    alertas = []

    # IR retido muito baixo para a renda
    renda = sum(r.valor_bruto for r in declaracao.rendimentos.filter(
        tipo__in=['salario', 'autonomo', 'aluguel', 'aposentadoria']
    ))
    if renda > Decimal('50000') and resultado['ir_retido'] < resultado['ir_devido'] * Decimal('0.5'):
        alertas.append(
            'O IR retido na fonte parece baixo em relação à renda declarada. '
            'Verifique os informes de rendimento.'
        )

    # Despesas médicas sem CNPJ
    deducoes_saude_sem_cnpj = declaracao.deducoes.filter(tipo='saude', cpf_cnpj_beneficiario='')
    if deducoes_saude_sem_cnpj.exists():
        alertas.append(
            f'{deducoes_saude_sem_cnpj.count()} dedução(ões) de saúde sem CPF/CNPJ do prestador. '
            'Isso pode gerar malha fina — informe o documento do prestador.'
        )

    # PGBL acima do limite de 12%
    renda_tributavel = sum(
        r.valor_bruto for r in declaracao.rendimentos.all()
        if r.tipo not in TIPOS_TRIBUTACAO_EXCLUSIVA
    )
    pgbl_total = sum(d.valor for d in declaracao.deducoes.filter(tipo='pgbl'))
    limite_pgbl = renda_tributavel * Decimal('0.12')
    if pgbl_total > limite_pgbl:
        alertas.append(
            f'O valor do PGBL (R$ {pgbl_total:.2f}) ultrapassa o limite dedutível de 12% '
            f'da renda tributável (R$ {limite_pgbl:.2f}). O sistema já aplica o limite automaticamente.'
        )

    # Dependente duplicado no mesmo CPF
    cpfs = list(declaracao.dependentes.values_list('cpf', flat=True))
    if len(cpfs) != len(set(cpfs)):
        alertas.append('Há dependentes com CPF duplicado. Verifique a lista de dependentes.')

    return alertas


# ─── Concluído ───────────────────────────────────────────────────────────────

@login_required
def wizard_concluido(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    return render(request, 'declaracao/wizard/concluido.html', {'declaracao': declaracao})
