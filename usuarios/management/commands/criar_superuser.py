from django.core.management.base import BaseCommand
from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Cria superuser inicial se não existir'

    def handle(self, *args, **kwargs):
        email = 'geffersonvivan@gmail.com'
        if not Usuario.objects.filter(email=email).exists():
            Usuario.objects.create_superuser(
                username=email,
                email=email,
                password='Leao2026@admin',
                email_verified=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser criado: {email}'))
        else:
            self.stdout.write(f'Usuário {email} já existe.')
