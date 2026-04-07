import secrets
from datetime import timedelta

from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Usuario, TokenVerificacaoEmail
from declaracao.models import VideoAjuda


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    video_ajuda = VideoAjuda.objects.filter(passo=0, ativo=True).exclude(url_youtube='').first()
    return render(request, 'home.html', {'video_ajuda': video_ajuda})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        return render(request, 'usuarios/login.html', {'form': {'errors': True}})

    return render(request, 'usuarios/login.html')


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip().lower()
        cpf        = request.POST.get('cpf', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')

        if password1 != password2:
            return render(request, 'usuarios/registro.html', {'erro': 'As senhas não coincidem.'})

        if len(password1) < 8:
            return render(request, 'usuarios/registro.html', {'erro': 'A senha deve ter pelo menos 8 caracteres.'})

        if Usuario.objects.filter(email=email).exists():
            return render(request, 'usuarios/registro.html', {'erro': 'Este e-mail já está cadastrado.'})

        if cpf and Usuario.objects.filter(cpf=cpf).exists():
            return render(request, 'usuarios/registro.html', {'erro': 'Este CPF já está cadastrado.'})

        user = Usuario.objects.create_user(
            username=email,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            cpf=cpf or None,
            email_verified=True,
        )

        login(request, user)
        messages.success(request, f'Bem-vindo, {first_name}! Sua conta foi criada com sucesso.')
        return redirect('dashboard')

    return render(request, 'usuarios/registro.html')


def verificar_email_view(request, token):
    try:
        obj = TokenVerificacaoEmail.objects.select_related('usuario').get(token=token)
    except TokenVerificacaoEmail.DoesNotExist:
        return render(request, 'usuarios/email_verificado.html', {'erro': 'Link inválido.'})

    if obj.expirado():
        obj.delete()
        return render(request, 'usuarios/email_verificado.html', {
            'erro': 'Este link expirou. Faça login e solicite um novo e-mail de verificação.',
        })

    user = obj.usuario
    user.email_verified = True
    user.save(update_fields=['email_verified'])
    obj.delete()

    login(request, user)
    messages.success(request, f'Bem-vindo, {user.first_name}! Sua conta foi confirmada.')
    return redirect('dashboard')


def reenviar_verificacao_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        try:
            user = Usuario.objects.get(email=email, email_verified=False)
            _enviar_email_verificacao(request, user)
        except Usuario.DoesNotExist:
            pass  # não revelar se o e-mail existe ou não
        return render(request, 'usuarios/aguardando_verificacao.html', {
            'email': email,
            'reenviado': True,
        })
    return redirect('login')


def _enviar_email_verificacao(request, user):
    # Cria ou substitui token
    TokenVerificacaoEmail.objects.filter(usuario=user).delete()
    expira_em = timezone.now() + timedelta(hours=24)
    token_str = secrets.token_urlsafe(32)
    TokenVerificacaoEmail.objects.create(
        usuario=user,
        token=token_str,
        expira_em=expira_em,
    )

    scheme = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    link = f'{scheme}://{host}/auth/verificar-email/{token_str}/'

    send_mail(
        subject='Confirme seu e-mail — Leão 2026',
        message=(
            f'Olá, {user.first_name}!\n\n'
            f'Clique no link abaixo para confirmar seu e-mail e acessar o Leão 2026:\n\n'
            f'{link}\n\n'
            f'O link expira em 24 horas.\n\n'
            f'Se você não criou esta conta, ignore este e-mail.'
        ),
        from_email='noreply@leao2026.com.br',
        recipient_list=[user.email],
        fail_silently=True,
    )


@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    declaracoes = request.user.declaracoes.order_by('-ano_base')
    return render(request, 'usuarios/dashboard.html', {'declaracoes': declaracoes})


def verificar_obrigatoriedade(request):
    criterios = [
        'Recebeu rendimentos tributáveis acima de R$ 33.888 no ano (salário, aposentadoria, pensão, aluguel, autônomo).',
        'Recebeu rendimentos isentos, não tributáveis ou tributados exclusivamente na fonte acima de R$ 200.000 (FGTS, herança, LCI, LCA, dividendos, etc.).',
        'Obteve ganho de capital na alienação de bens ou direitos, sujeito à incidência do imposto.',
        'Realizou operações em bolsa de valores com soma de vendas acima de R$ 40.000, ou com lucro tributável em qualquer valor.',
        'Teve receita bruta de atividade rural acima de R$ 169.440.',
        'Pretende compensar prejuízo de atividade rural de anos anteriores.',
        'Possuía bens e direitos acima de R$ 800.000 em 31/12/2024.',
        'Passou à condição de residente no Brasil durante 2024.',
        'Optou pela isenção de ganho de capital na venda de imóvel residencial com compra de outro em até 180 dias.',
        'Atualizou bens imóveis com a taxa diferenciada autorizada pela Lei 14.973/2024.',
        'Obteve rendimentos de ativos no exterior (offshores, trusts, contas e investimentos internacionais).',
    ]
    return render(request, 'verificar_obrigatoriedade.html', {'criterios': criterios})
