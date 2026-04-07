from django.db import models
from django.conf import settings


class Plano(models.Model):
    TIPO_CHOICES = [
        ('pessoal', 'Pessoal'),
        ('tokens',  'Contabilidade / Tokens'),
    ]

    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='pessoal')
    preco_anual = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                      help_text="Preço anual para plano pessoal. Ignorado para plano tokens.")
    preco_por_token = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                          help_text="Preço por token (declaração). Apenas para plano tokens.")
    min_tokens = models.IntegerField(default=1,
                                     help_text="Quantidade mínima de tokens por compra.")
    max_declaracoes = models.IntegerField(default=1, help_text="-1 = ilimitado")
    chat_ilimitado = models.BooleanField(default=True)
    permite_upload_docs = models.BooleanField(default=True)
    permite_ganho_capital = models.BooleanField(default=True)
    permite_exterior = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    destaque = models.BooleanField(default=False, help_text="Exibe badge 'Mais popular'")
    descricao_curta = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Plano"
        verbose_name_plural = "Planos"
        ordering = ['tipo', 'preco_anual']

    def __str__(self):
        return self.nome

    def preco_em_centavos(self):
        return int(self.preco_anual * 100)

    def preco_token_em_centavos(self):
        return int(self.preco_por_token * 100)


class SaldoTokens(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saldo_tokens',
    )
    tokens_disponiveis = models.IntegerField(default=0)
    tokens_usados = models.IntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Saldo de Tokens'
        verbose_name_plural = 'Saldos de Tokens'

    def __str__(self):
        return f'{self.usuario} — {self.tokens_disponiveis} tokens'

    def consumir(self):
        """Consome 1 token. Retorna True se bem-sucedido."""
        if self.tokens_disponiveis > 0:
            self.tokens_disponiveis -= 1
            self.tokens_usados += 1
            self.save(update_fields=['tokens_disponiveis', 'tokens_usados', 'atualizado_em'])
            return True
        return False


class Assinatura(models.Model):
    STATUS_CHOICES = [
        ('ativa',     'Ativa'),
        ('pendente',  'Pendente de pagamento'),
        ('expirada',  'Expirada'),
        ('cancelada', 'Cancelada'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assinatura',
    )
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT, related_name='assinaturas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    stripe_session_id = models.CharField(max_length=200, blank=True)
    stripe_customer_id = models.CharField(max_length=200, blank=True)
    stripe_payment_intent = models.CharField(max_length=200, blank=True)
    valida_ate = models.DateField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"

    def __str__(self):
        return f"{self.usuario} — {self.plano} ({self.status})"

    @property
    def ativa(self):
        from django.utils import timezone
        if self.plano.tipo == 'tokens':
            return self.status == 'ativa'
        return (
            self.status == 'ativa'
            and self.valida_ate is not None
            and self.valida_ate >= timezone.now().date()
        )


class CompraTokens(models.Model):
    """Registro histórico de cada compra de tokens."""
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='compras_tokens',
    )
    quantidade = models.IntegerField()
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    total_pago = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_session_id = models.CharField(max_length=200, blank=True)
    stripe_payment_intent = models.CharField(max_length=200, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Compra de Tokens'
        verbose_name_plural = 'Compras de Tokens'
        ordering = ['-criada_em']

    def __str__(self):
        return f'{self.usuario} — {self.quantidade} tokens — R$ {self.total_pago}'
