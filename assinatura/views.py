import stripe
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Plano, Assinatura, SaldoTokens, CompraTokens

stripe.api_key = settings.STRIPE_SECRET_KEY

MIN_TOKENS = 10


def planos(request):
    pessoal = Plano.objects.filter(ativo=True, tipo='pessoal').first()
    tokens  = Plano.objects.filter(ativo=True, tipo='tokens').first()
    assinatura = getattr(request.user, 'assinatura', None) if request.user.is_authenticated else None
    saldo = getattr(request.user, 'saldo_tokens', None) if request.user.is_authenticated else None
    return render(request, 'assinatura/planos.html', {
        'plano_pessoal': pessoal,
        'plano_tokens': tokens,
        'assinatura': assinatura,
        'saldo': saldo,
    })


@login_required
def checkout(request, slug):
    plano = get_object_or_404(Plano, slug=slug, ativo=True)
    scheme = 'https' if request.is_secure() else 'http'
    host = request.get_host()

    if plano.tipo == 'pessoal':
        return _checkout_pessoal(request, plano, scheme, host)
    else:
        return _checkout_tokens(request, plano, scheme, host)


def _checkout_pessoal(request, plano, scheme, host):
    assinatura = getattr(request.user, 'assinatura', None)
    if assinatura and assinatura.plano == plano and assinatura.ativa:
        return redirect('assinatura_sucesso')

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'unit_amount': plano.preco_em_centavos(),
                    'product_data': {
                        'name': f'Leão 2026 — {plano.nome}',
                        'description': plano.descricao_curta or 'Acesso anual',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            customer_email=request.user.email,
            metadata={
                'tipo': 'pessoal',
                'usuario_id': str(request.user.pk),
                'plano_slug': plano.slug,
            },
            success_url=f'{scheme}://{host}/assinatura/sucesso/?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{scheme}://{host}/assinatura/cancelado/',
        )
    except stripe.StripeError:
        messages.error(request, 'Não foi possível iniciar o pagamento. Tente novamente.')
        return redirect('planos')

    Assinatura.objects.update_or_create(
        usuario=request.user,
        defaults={
            'plano': plano,
            'status': 'pendente',
            'stripe_session_id': session.id,
        },
    )
    return redirect(session.url, permanent=False)


def _checkout_tokens(request, plano, scheme, host):
    try:
        quantidade = max(int(request.POST.get('quantidade', MIN_TOKENS)), MIN_TOKENS)
    except (ValueError, TypeError):
        quantidade = MIN_TOKENS

    total_centavos = plano.preco_token_em_centavos() * quantidade

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'unit_amount': plano.preco_token_em_centavos(),
                    'product_data': {
                        'name': f'Leão 2026 — {plano.nome}',
                        'description': f'Pacote de {quantidade} declarações',
                    },
                },
                'quantity': quantidade,
            }],
            mode='payment',
            customer_email=request.user.email,
            metadata={
                'tipo': 'tokens',
                'usuario_id': str(request.user.pk),
                'plano_slug': plano.slug,
                'quantidade': str(quantidade),
            },
            success_url=f'{scheme}://{host}/assinatura/sucesso/?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{scheme}://{host}/assinatura/cancelado/',
        )
    except stripe.StripeError:
        messages.error(request, 'Não foi possível iniciar o pagamento. Tente novamente.')
        return redirect('planos')

    # Garante assinatura de plano tokens ativa
    Assinatura.objects.update_or_create(
        usuario=request.user,
        defaults={
            'plano': plano,
            'status': 'pendente',
            'stripe_session_id': session.id,
        },
    )
    return redirect(session.url, permanent=False)


@login_required
def sucesso(request):
    session_id = request.GET.get('session_id', '')
    assinatura = getattr(request.user, 'assinatura', None)

    if session_id and assinatura and assinatura.status == 'pendente':
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                _processar_pagamento(session)
                assinatura.refresh_from_db()
        except stripe.StripeError:
            pass

    saldo = getattr(request.user, 'saldo_tokens', None)
    return render(request, 'assinatura/sucesso.html', {
        'assinatura': assinatura,
        'saldo': saldo,
    })


def cancelado(request):
    return render(request, 'assinatura/cancelado.html')


@csrf_exempt
@require_POST
def webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        if session.get('payment_status') == 'paid':
            _processar_pagamento(session)

    return HttpResponse(status=200)


def _processar_pagamento(session):
    meta = session.get('metadata', {})
    tipo = meta.get('tipo', 'pessoal')
    usuario_id = meta.get('usuario_id')
    if not usuario_id:
        return

    try:
        assinatura = Assinatura.objects.select_related('usuario', 'plano').get(
            usuario_id=int(usuario_id),
            stripe_session_id=session['id'],
        )
    except Assinatura.DoesNotExist:
        return

    assinatura.status = 'ativa'
    assinatura.stripe_customer_id = session.get('customer') or ''
    assinatura.stripe_payment_intent = session.get('payment_intent') or ''
    assinatura.save(update_fields=['status', 'stripe_customer_id', 'stripe_payment_intent', 'atualizada_em'])

    usuario = assinatura.usuario
    usuario.plano = assinatura.plano
    usuario.save(update_fields=['plano'])

    if tipo == 'tokens':
        quantidade = int(meta.get('quantidade', MIN_TOKENS))
        saldo, _ = SaldoTokens.objects.get_or_create(usuario=usuario)
        saldo.tokens_disponiveis += quantidade
        saldo.save(update_fields=['tokens_disponiveis', 'atualizado_em'])

        CompraTokens.objects.create(
            usuario=usuario,
            quantidade=quantidade,
            preco_unitario=assinatura.plano.preco_por_token,
            total_pago=assinatura.plano.preco_por_token * quantidade,
            stripe_session_id=session['id'],
            stripe_payment_intent=session.get('payment_intent') or '',
        )
    else:
        assinatura.valida_ate = date.today() + timedelta(days=365)
        assinatura.save(update_fields=['valida_ate', 'atualizada_em'])
