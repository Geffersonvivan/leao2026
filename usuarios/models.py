import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    plano = models.ForeignKey(
        'assinatura.Plano',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='usuarios',
    )
    email_verified = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.get_full_name() or self.username


class TokenVerificacaoEmail(models.Model):
    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, related_name='token_verificacao'
    )
    token = models.CharField(max_length=64, unique=True)
    expira_em = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expira_em:
            self.expira_em = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def expirado(self):
        return timezone.now() > self.expira_em

    class Meta:
        verbose_name = 'Token de Verificação de E-mail'
        verbose_name_plural = 'Tokens de Verificação de E-mail'

    def __str__(self):
        return f'Token de {self.usuario}'


class PerfilFiscal(models.Model):
    TIPO_CHOICES = [
        ('assalariado', 'Assalariado'),
        ('autonomo', 'Autônomo'),
        ('empresario', 'Empresário/Sócio'),
        ('aposentado', 'Aposentado/Pensionista'),
        ('rural', 'Produtor Rural'),
        ('misto', 'Mais de uma fonte'),
    ]

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_fiscal')
    tipo_contribuinte = models.CharField(max_length=20, choices=TIPO_CHOICES, blank=True)
    tem_dependentes = models.BooleanField(default=False)
    tem_imoveis = models.BooleanField(default=False)
    tem_investimentos = models.BooleanField(default=False)
    tem_exterior = models.BooleanField(default=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil Fiscal"
        verbose_name_plural = "Perfis Fiscais"

    def __str__(self):
        return f"Perfil de {self.usuario}"
