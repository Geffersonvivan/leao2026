from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assinatura', '0002_assinatura_stripe'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Novos campos em Plano
        migrations.AddField(
            model_name='plano',
            name='tipo',
            field=models.CharField(
                choices=[('pessoal', 'Pessoal'), ('tokens', 'Contabilidade / Tokens')],
                default='pessoal',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='plano',
            name='preco_por_token',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Preço por token (declaração). Apenas para plano tokens.',
                max_digits=8,
            ),
        ),
        migrations.AddField(
            model_name='plano',
            name='min_tokens',
            field=models.IntegerField(
                default=1,
                help_text='Quantidade mínima de tokens por compra.',
            ),
        ),
        # Atualiza ordering do Plano
        migrations.AlterModelOptions(
            name='plano',
            options={
                'ordering': ['tipo', 'preco_anual'],
                'verbose_name': 'Plano',
                'verbose_name_plural': 'Planos',
            },
        ),
        # Novo modelo SaldoTokens
        migrations.CreateModel(
            name='SaldoTokens',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tokens_disponiveis', models.IntegerField(default=0)),
                ('tokens_usados', models.IntegerField(default=0)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('usuario', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='saldo_tokens',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Saldo de Tokens',
                'verbose_name_plural': 'Saldos de Tokens',
            },
        ),
        # Novo modelo CompraTokens
        migrations.CreateModel(
            name='CompraTokens',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade', models.IntegerField()),
                ('preco_unitario', models.DecimalField(decimal_places=2, max_digits=8)),
                ('total_pago', models.DecimalField(decimal_places=2, max_digits=10)),
                ('stripe_session_id', models.CharField(blank=True, max_length=200)),
                ('stripe_payment_intent', models.CharField(blank=True, max_length=200)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='compras_tokens',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Compra de Tokens',
                'verbose_name_plural': 'Compras de Tokens',
                'ordering': ['-criada_em'],
            },
        ),
    ]
