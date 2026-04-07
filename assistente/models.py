from django.db import models


class Conversa(models.Model):
    declaracao = models.ForeignKey(
        'declaracao.Declaracao',
        on_delete=models.CASCADE,
        related_name='conversas',
    )
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conversa"
        verbose_name_plural = "Conversas"

    def __str__(self):
        return f"Conversa #{self.pk} — {self.declaracao}"


class Mensagem(models.Model):
    PAPEL_CHOICES = [
        ('user', 'Usuário'),
        ('assistant', 'Assistente'),
    ]

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name='mensagens')
    papel = models.CharField(max_length=10, choices=PAPEL_CHOICES)
    conteudo = models.TextField()
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
        ordering = ['criada_em']

    def __str__(self):
        return f"[{self.papel}] {self.conteudo[:60]}"
