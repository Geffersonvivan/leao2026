from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import stripe

from .models import Declaracao, Rendimento, Deducao, Dependente
from .calculadora import recomendar_modelo, calcular_resultado_final
from .auditoria import auditar
from .auditoria_ia import auditar_com_ia
from .exportador import gerar_pdf, gerar_json
from .validadores import validar_cpf, formatar_cpf


@login_required
def nova_declaracao(request):
    anos_disponiveis = [2025]

    if request.method == 'POST':
        ano_base = int(request.POST.get('ano_base', 0))
        nome_titular = request.POST.get('nome_titular', '').strip()
        cpf_titular = request.POST.get('cpf_titular', '').strip()

        ctx = {'anos_disponiveis': anos_disponiveis,
               'nome_titular': nome_titular, 'cpf_titular': cpf_titular,
               'ano_base': ano_base}

        if not nome_titular:
            return render(request, 'declaracao/nova.html', {**ctx, 'erro_nome': 'Informe o nome do titular.'})

        if not validar_cpf(cpf_titular):
            return render(request, 'declaracao/nova.html', {**ctx, 'erro_cpf': 'CPF inválido. Verifique os dígitos.'})

        cpf_formatado = formatar_cpf(cpf_titular)
        decl = Declaracao.objects.create(
            usuario=request.user,
            ano_base=ano_base,
            nome_titular=nome_titular,
            cpf_titular=cpf_formatado,
        )
        return redirect('importacao_etapa0', pk=decl.pk)

    return render(request, 'declaracao/nova.html', {'anos_disponiveis': anos_disponiveis})


@login_required
def detalhe_declaracao(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    simulacao = None
    if declaracao.rendimentos.exists():
        simulacao = recomendar_modelo(declaracao)
        resultado = calcular_resultado_final(declaracao)
        declaracao.ir_devido = resultado['ir_devido']
        declaracao.ir_retido = resultado['ir_retido']
        declaracao.resultado = resultado['resultado']
        declaracao.save(update_fields=['ir_devido', 'ir_retido', 'resultado'])

    return render(request, 'declaracao/detalhe.html', {
        'declaracao': declaracao,
        'simulacao': simulacao,
    })


@login_required
def novo_rendimento(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if request.method == 'POST':
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
            messages.success(request, 'Rendimento adicionado.')
            return redirect('declaracao_detalhe', pk=pk)
        except Exception as e:
            return render(request, 'declaracao/form_rendimento.html', {
                'declaracao': declaracao, 'erro': str(e),
            })

    return render(request, 'declaracao/form_rendimento.html', {'declaracao': declaracao})


@login_required
def nova_deducao(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if request.method == 'POST':
        try:
            Deducao.objects.create(
                declaracao=declaracao,
                tipo=request.POST['tipo'],
                descricao=request.POST['descricao'],
                valor=request.POST['valor'],
                cpf_cnpj_beneficiario=request.POST.get('cpf_cnpj_beneficiario', ''),
            )
            messages.success(request, 'Dedução adicionada.')
            return redirect('declaracao_detalhe', pk=pk)
        except Exception as e:
            return render(request, 'declaracao/form_deducao.html', {
                'declaracao': declaracao, 'erro': str(e),
            })

    return render(request, 'declaracao/form_deducao.html', {'declaracao': declaracao})


@login_required
def novo_dependente(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    if request.method == 'POST':
        try:
            Dependente.objects.create(
                declaracao=declaracao,
                nome=request.POST['nome'],
                cpf=request.POST['cpf'],
                data_nascimento=request.POST['data_nascimento'],
                parentesco=request.POST['parentesco'],
            )
            messages.success(request, 'Dependente adicionado.')
            return redirect('declaracao_detalhe', pk=pk)
        except Exception as e:
            return render(request, 'declaracao/form_dependente.html', {
                'declaracao': declaracao, 'erro': str(e),
            })

    return render(request, 'declaracao/form_dependente.html', {'declaracao': declaracao})


@login_required
def auditoria_view(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    relatorio = auditar(declaracao)

    analise_ia = None
    if request.method == 'POST' and request.POST.get('acao') == 'analisar_ia':
        analise_ia = auditar_com_ia(declaracao, relatorio)

    return render(request, 'declaracao/auditoria.html', {
        'declaracao': declaracao,
        'relatorio': relatorio,
        'analise_ia': analise_ia,
    })


def _tem_assinatura_ativa(user):
    assinatura = getattr(user, 'assinatura', None)
    return assinatura is not None and assinatura.ativa


@login_required
def exportar_view(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    if not _tem_assinatura_ativa(request.user):
        messages.warning(request, 'Assine um plano para exportar sua declaração.')
        return redirect('planos')
    return render(request, 'declaracao/exportar.html', {'declaracao': declaracao})


@login_required
def exportar_pdf(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    if not _tem_assinatura_ativa(request.user):
        messages.warning(request, 'Assine um plano para exportar sua declaração.')
        return redirect('planos')
    if not declaracao.rendimentos.exists():
        messages.error(request, 'Adicione rendimentos antes de exportar.')
        return redirect('declaracao_detalhe', pk=pk)
    pdf = gerar_pdf(declaracao)
    nome = f'IRPF_{declaracao.ano_base}_{declaracao.usuario.cpf or "declaracao"}.pdf'
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nome}"'
    return response


@login_required
def exportar_json(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    if not _tem_assinatura_ativa(request.user):
        messages.warning(request, 'Assine um plano para exportar sua declaração.')
        return redirect('planos')
    dados = gerar_json(declaracao)
    nome = f'IRPF_{declaracao.ano_base}_{declaracao.usuario.cpf or "declaracao"}.json'
    response = HttpResponse(dados, content_type='application/json; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nome}"'
    return response

@login_required
def excluir_declaracao(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    ano = declaracao.ano_base
    declaracao.delete()
    messages.success(request, f'Declaração {ano} excluída com sucesso.')
    return redirect('dashboard')


@login_required
def iniciar_pagamento(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    if declaracao.is_pago:
        return redirect('declaracao_detalhe', pk=pk)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    domain_url = request.build_absolute_uri('/')[:-1]

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card', 'pix'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'brl',
                        'unit_amount': 4990,
                        'product_data': {
                            'name': f'Declaração IRPF - {declaracao.nome_titular}',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=domain_url + reverse('declaracao_detalhe', kwargs={'pk': pk}) + '?pagamento=sucesso',
            cancel_url=domain_url + reverse('declaracao_detalhe', kwargs={'pk': pk}) + '?pagamento=cancelado',
            client_reference_id=str(request.user.id),
            metadata={'declaracao_id': str(declaracao.id)}
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, f"Erro ao contatar o Stripe: {str(e)}")
        return redirect('dashboard')


@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        declaracao_id = session.get('metadata', {}).get('declaracao_id')
        if declaracao_id:
            try:
                declaracao = Declaracao.objects.get(id=declaracao_id)
                declaracao.is_pago = True
                declaracao.save(update_fields=['is_pago'])
            except Declaracao.DoesNotExist:
                pass

    return HttpResponse(status=200)
