from django.core.management.base import BaseCommand
from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Cria superuser inicial se não existir'

    def handle(self, *args, **kwargs):
        email = 'geffersonvivan@gmail.com'
        user, created = Usuario.objects.get_or_create(
            email=email,
            defaults={'username': email, 'email_verified': True},
        )
        user.is_staff = True
        user.is_superuser = True
        user.email_verified = True
        user.set_password('Leao2026@admin')
        user.save()
        status = 'criado' if created else 'atualizado para superuser'
        self.stdout.write(self.style.SUCCESS(f'Superuser {status}: {email}'))
