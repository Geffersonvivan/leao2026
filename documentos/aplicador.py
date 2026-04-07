"""
Aplica os dados extraídos de um documento na declaração do usuário.
Cria os objetos de Rendimento ou Deducao com base no JSON extraído.
"""
from decimal import Decimal, InvalidOperation

from declaracao.models import Rendimento, Deducao, BemDireito


def _decimal(valor) -> Decimal:
    try:
        return Decimal(str(valor or 0))
    except InvalidOperation:
        return Decimal('0')


def aplicar_dados(declaracao, dados: dict) -> dict:
    """
    Recebe o dict extraído e cria os registros na declaração.
    Retorna um resumo do que foi criado.
    """
    tipo_doc = dados.get('tipo_documento')
    criados = {'rendimentos': [], 'deducoes': []}

    if tipo_doc == 'informe_rendimentos':
        criados = _aplicar_informe(declaracao, dados)

    elif tipo_doc == 'recibo_medico':
        criados = _aplicar_recibo_medico(declaracao, dados)

    elif tipo_doc == 'boleto_escola':
        criados = _aplicar_educacao(declaracao, dados)

    elif tipo_doc == 'outros':
        criados = _aplicar_outros(declaracao, dados)

    return criados


def _aplicar_informe(declaracao, dados: dict) -> dict:
    rendimentos_criados = []
    for r in dados.get('rendimentos', []):
        obj = Rendimento.objects.create(
            declaracao=declaracao,
            tipo=r.get('tipo', 'outros_tributaveis'),
            fonte_pagadora_nome=dados.get('fonte_pagadora_nome', ''),
            fonte_pagadora_cnpj_cpf=dados.get('fonte_pagadora_cnpj', ''),
            valor_bruto=_decimal(r.get('valor_bruto')),
            ir_retido=_decimal(r.get('ir_retido')),
            inss_retido=_decimal(r.get('inss_retido')),
        )
        rendimentos_criados.append(obj)
    return {'rendimentos': rendimentos_criados, 'deducoes': []}


def _aplicar_recibo_medico(declaracao, dados: dict) -> dict:
    obj = Deducao.objects.create(
        declaracao=declaracao,
        tipo='saude',
        descricao=dados.get('descricao') or f"Consulta/Tratamento — {dados.get('prestador_nome', '')}",
        valor=_decimal(dados.get('valor')),
        cpf_cnpj_beneficiario=dados.get('prestador_cnpj_cpf', ''),
    )
    return {'rendimentos': [], 'deducoes': [obj]}


def _aplicar_educacao(declaracao, dados: dict) -> dict:
    obj = Deducao.objects.create(
        declaracao=declaracao,
        tipo='educacao',
        descricao=dados.get('descricao') or f"Educação — {dados.get('instituicao_nome', '')}",
        valor=_decimal(dados.get('valor_total')),
        cpf_cnpj_beneficiario=dados.get('instituicao_cnpj', ''),
    )
    return {'rendimentos': [], 'deducoes': [obj]}


def _aplicar_outros(declaracao, dados: dict) -> dict:
    """Cria BemDireito(s) a partir dos subtipos de documento."""
    subtipo = dados.get('subtipo', 'generico')
    bens_criados = []

    if subtipo == 'veiculo':
        obj = BemDireito.objects.create(
            declaracao=declaracao,
            origem='documento',
            codigo=dados.get('codigo_rf') or '21',
            discriminacao=dados.get('discriminacao') or dados.get('marca_modelo', 'Veículo'),
            valor_atual=_decimal(dados.get('valor_aquisicao')),
            valor_anterior=Decimal('0'),
        )
        bens_criados.append(obj)

    elif subtipo == 'imovel':
        obj = BemDireito.objects.create(
            declaracao=declaracao,
            origem='documento',
            codigo=dados.get('codigo_rf') or '11',
            discriminacao=dados.get('discriminacao') or dados.get('endereco', 'Imóvel'),
            valor_atual=_decimal(dados.get('valor_aquisicao')),
            valor_anterior=Decimal('0'),
        )
        bens_criados.append(obj)

    elif subtipo == 'acoes_fii':
        for ativo in dados.get('ativos', []):
            ticker = ativo.get('ticker', '')
            nome = ativo.get('nome', '')
            qtd = ativo.get('quantidade', 0)
            valor = _decimal(ativo.get('valor_total'))
            if valor == Decimal('0'):
                continue
            discriminacao = f"{ticker} — {nome} — {qtd} cotas — {dados.get('corretora_nome', '')}"
            obj = BemDireito.objects.create(
                declaracao=declaracao,
                origem='documento',
                codigo=dados.get('codigo_rf') or '31',
                discriminacao=discriminacao.strip(' —'),
                valor_atual=valor,
                valor_anterior=Decimal('0'),
            )
            bens_criados.append(obj)

    elif subtipo == 'cripto':
        for ativo in dados.get('ativos', []):
            nome = ativo.get('nome', '')
            simbolo = ativo.get('simbolo', '')
            qtd = ativo.get('quantidade', 0)
            valor = _decimal(ativo.get('valor_brl'))
            if valor == Decimal('0'):
                continue
            discriminacao = f"{simbolo} ({nome}) — {qtd} unidades — {dados.get('exchange', '')}"
            obj = BemDireito.objects.create(
                declaracao=declaracao,
                origem='documento',
                codigo=dados.get('codigo_rf') or '89',
                discriminacao=discriminacao.strip(' —'),
                valor_atual=valor,
                valor_anterior=Decimal('0'),
            )
            bens_criados.append(obj)

    elif subtipo == 'conta_bancaria':
        obj = BemDireito.objects.create(
            declaracao=declaracao,
            origem='documento',
            codigo=dados.get('codigo_rf') or '41',
            discriminacao=dados.get('discriminacao') or dados.get('banco_nome', 'Conta bancária'),
            valor_atual=_decimal(dados.get('saldo')),
            valor_anterior=Decimal('0'),
        )
        bens_criados.append(obj)

    # subtipo genérico — cria um bem com a descrição disponível
    else:
        descricao = dados.get('discriminacao') or dados.get('descricao', 'Bem ou direito')
        if descricao:
            obj = BemDireito.objects.create(
                declaracao=declaracao,
                origem='documento',
                codigo=dados.get('codigo_rf') or '99',
                discriminacao=descricao,
                valor_atual=Decimal('0'),
                valor_anterior=Decimal('0'),
            )
            bens_criados.append(obj)

    return {'rendimentos': [], 'deducoes': [], 'bens': bens_criados}
