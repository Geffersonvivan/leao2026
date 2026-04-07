from django.db import migrations


def criar_planos(apps, schema_editor):
    Plano = apps.get_model('assinatura', 'Plano')

    Plano.objects.update_or_create(
        slug='pessoal',
        defaults={
            'nome': 'Pessoal',
            'tipo': 'pessoal',
            'preco_anual': '49.90',
            'preco_por_token': '0.00',
            'min_tokens': 1,
            'max_declaracoes': 1,
            'chat_ilimitado': True,
            'permite_upload_docs': True,
            'permite_ganho_capital': True,
            'permite_exterior': True,
            'ativo': True,
            'destaque': True,
            'descricao_curta': 'Ideal para declarar o seu próprio IR',
        },
    )

    Plano.objects.update_or_create(
        slug='contabilidade',
        defaults={
            'nome': 'Contabilidade',
            'tipo': 'tokens',
            'preco_anual': '0.00',
            'preco_por_token': '19.90',
            'min_tokens': 10,
            'max_declaracoes': -1,
            'chat_ilimitado': True,
            'permite_upload_docs': True,
            'permite_ganho_capital': True,
            'permite_exterior': True,
            'ativo': True,
            'destaque': False,
            'descricao_curta': 'Para contadores e escritórios de contabilidade',
        },
    )


def remover_planos(apps, schema_editor):
    Plano = apps.get_model('assinatura', 'Plano')
    Plano.objects.filter(slug__in=['pessoal', 'contabilidade']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('assinatura', '0003_plano_tokens_saldo_compra'),
    ]

    operations = [
        migrations.RunPython(criar_planos, remover_planos),
    ]
