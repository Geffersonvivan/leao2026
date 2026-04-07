from django.db import models


class Documento(models.Model):
    TIPO_CHOICES = [
        ('informe_rendimentos', 'Informe de Rendimentos'),
        ('recibo_medico', 'Recibo Médico'),
        ('boleto_escola', 'Comprovante de Educação'),
        ('outros', 'Outros'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('erro', 'Erro'),
    ]

    declaracao = models.ForeignKey(
        'declaracao.Declaracao',
        on_delete=models.CASCADE,
        related_name='documentos',
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    arquivo = models.FileField(upload_to='documentos/%Y/%m/')
    status_processamento = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pendente')
    dados_extraidos = models.JSONField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.declaracao}"
