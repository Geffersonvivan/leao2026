from django.db import models
from django.conf import settings


class Declaracao(models.Model):
    MODELO_CHOICES = [
        ('simplificado', 'Simplificado'),
        ('completo', 'Completo'),
    ]
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('em_revisao', 'Em Revisão'),
        ('pronta', 'Pronta para Envio'),
        ('entregue', 'Entregue à Receita'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='declaracoes')
    ano_base = models.IntegerField()
    nome_titular = models.CharField(max_length=200, default="Titular Principal")
    cpf_titular = models.CharField(max_length=14, default="000.000.000-00")
    is_pago = models.BooleanField(default=False)
    modelo = models.CharField(max_length=20, choices=MODELO_CHOICES, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='rascunho')
    ir_devido = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ir_retido = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    resultado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                    help_text="Negativo = restituição. Positivo = imposto a pagar.")
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Declaração"
        verbose_name_plural = "Declarações"

    def __str__(self):
        return f"Declaração {self.ano_base} — {self.usuario}"


ORIGEM_CHOICES = [
    ('manual', 'Manual'),
    ('importado', 'Importado (declaração anterior)'),
    ('documento', 'Extraído de documento'),
]


class ImportacaoDeclaracao(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente de revisão'),
        ('processando', 'Processando PDF'),
        ('revisado', 'Revisado'),
        ('aplicado', 'Aplicado'),
        ('erro', 'Erro na leitura'),
    ]
    declaracao = models.OneToOneField(
        'Declaracao', on_delete=models.CASCADE, related_name='importacao'
    )
    arquivo = models.FileField(upload_to='importacoes/')
    dados_brutos = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Importação de Declaração"
        verbose_name_plural = "Importações de Declaração"

    def __str__(self):
        return f"Importação — {self.declaracao}"


class Rendimento(models.Model):
    TIPO_CHOICES = [
        ('salario', 'Salário/Pró-labore'),
        ('aluguel', 'Aluguéis'),
        ('autonomo', 'Trabalho Autônomo'),
        ('pensao_recebida', 'Pensão Alimentícia Recebida'),
        ('aposentadoria', 'Aposentadoria/Pensão INSS'),
        ('rural', 'Atividade Rural'),
        ('exterior', 'Rendimentos do Exterior'),
        ('outros_tributaveis', 'Outros Tributáveis'),
        ('isento', 'Isento / Não Tributável'),
        ('exclusivo_fonte', 'Tributado Exclusivamente na Fonte'),
        ('dividendo', 'Dividendos de Ações/FIIs (Isento)'),
        ('jcp', 'JCP — Juros sobre Capital Próprio (Exclusivo na Fonte)'),
        ('rendimento_fii', 'Rendimentos de FII (Isento)'),
    ]

    declaracao = models.ForeignKey(Declaracao, on_delete=models.CASCADE, related_name='rendimentos')
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default='manual')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    fonte_pagadora_nome = models.CharField(max_length=200)
    fonte_pagadora_cnpj_cpf = models.CharField(max_length=20, blank=True)
    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2)
    ir_retido = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inss_retido = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Rendimento"
        verbose_name_plural = "Rendimentos"

    def __str__(self):
        return f"{self.get_tipo_display()} — R$ {self.valor_bruto}"


class Dependente(models.Model):
    PARENTESCO_CHOICES = [
        ('conjuge', 'Cônjuge/Companheiro(a)'),
        ('filho', 'Filho(a)/Enteado(a)'),
        ('pai_mae', 'Pai/Mãe'),
        ('avo', 'Avô/Avó'),
        ('irmao', 'Irmão/Irmã'),
        ('menor_guarda', 'Menor sob Guarda/Tutela'),
        ('incapaz', 'Incapaz sob Tutela/Curatela'),
    ]

    declaracao = models.ForeignKey(Declaracao, on_delete=models.CASCADE, related_name='dependentes')
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default='manual')
    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14)
    data_nascimento = models.DateField()
    parentesco = models.CharField(max_length=20, choices=PARENTESCO_CHOICES)

    class Meta:
        verbose_name = "Dependente"
        verbose_name_plural = "Dependentes"

    def __str__(self):
        return f"{self.nome} ({self.get_parentesco_display()})"


class Deducao(models.Model):
    TIPO_CHOICES = [
        ('dependente', 'Dependente'),
        ('saude', 'Despesas Médicas/Saúde'),
        ('educacao', 'Educação'),
        ('inss', 'Previdência Social (INSS)'),
        ('pgbl', 'Previdência Privada (PGBL)'),
        ('pensao_paga', 'Pensão Alimentícia Paga'),
        ('livro_caixa', 'Livro-Caixa'),
    ]

    declaracao = models.ForeignKey(Declaracao, on_delete=models.CASCADE, related_name='deducoes')
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default='manual')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=300)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    cpf_cnpj_beneficiario = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Dedução"
        verbose_name_plural = "Deduções"

    def __str__(self):
        return f"{self.get_tipo_display()} — R$ {self.valor}"


class BemDireito(models.Model):
    declaracao = models.ForeignKey(Declaracao, on_delete=models.CASCADE, related_name='bens')
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default='manual')
    codigo = models.CharField(max_length=10, help_text="Código Receita Federal")
    discriminacao = models.TextField()
    valor_anterior = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         help_text="Saldo em 31/12 do ano anterior")
    valor_atual = models.DecimalField(max_digits=15, decimal_places=2,
                                      help_text="Saldo em 31/12 do ano-base")

    class Meta:
        verbose_name = "Bem ou Direito"
        verbose_name_plural = "Bens e Direitos"

    def __str__(self):
        return f"[{self.codigo}] {self.discriminacao[:60]}"


class VideoAjuda(models.Model):
    PASSO_CHOICES = [(0, 'Passo 0 — Apresentação')] + [(i, f'Passo {i}') for i in range(1, 7)]

    passo = models.IntegerField(choices=PASSO_CHOICES, unique=True)
    titulo = models.CharField(max_length=200)
    url_youtube = models.URLField(blank=True, help_text='URL do vídeo no YouTube. Deixe em branco para ocultar.')
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Vídeo de Ajuda'
        verbose_name_plural = 'Vídeos de Ajuda'
        ordering = ['passo']

    def __str__(self):
        return f'Passo {self.passo} — {self.titulo}'

    def embed_url(self):
        """Converte URL do YouTube para formato embed."""
        if not self.url_youtube:
            return ''
        url = self.url_youtube
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[-1].split('?')[0]
        elif 'watch?v=' in url:
            video_id = url.split('watch?v=')[-1].split('&')[0]
        elif 'embed/' in url:
            return url
        else:
            return url
        return f'https://www.youtube.com/embed/{video_id}'


class GanhoCapital(models.Model):
    declaracao = models.ForeignKey(Declaracao, on_delete=models.CASCADE, related_name='ganhos_capital')
    tipo_bem = models.CharField(max_length=100)
    data_aquisicao = models.DateField()
    data_alienacao = models.DateField()
    custo_aquisicao = models.DecimalField(max_digits=15, decimal_places=2)
    valor_venda = models.DecimalField(max_digits=15, decimal_places=2)
    isento = models.BooleanField(default=False)
    motivo_isencao = models.CharField(max_length=200, blank=True)
    darf_recolhido = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Ganho de Capital"
        verbose_name_plural = "Ganhos de Capital"

    def __str__(self):
        ganho = self.valor_venda - self.custo_aquisicao
        return f"{self.tipo_bem} — Ganho: R$ {ganho}"
