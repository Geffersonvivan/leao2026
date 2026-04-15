"""
Motor de cálculo do IRPF.
Todas as regras seguem logica_IR.md — IRPF 2025 (ano-base 2024).
"""
from decimal import Decimal, ROUND_HALF_UP

# ---------------------------------------------------------------------------
# Constantes IRPF 2024 (ano-base)
# ---------------------------------------------------------------------------

# (limite_superior, aliquota, parcela_deduzir)
TABELA_ANUAL_2024 = [
    (Decimal('26963.20'),   Decimal('0.000'), Decimal('0.00')),
    (Decimal('33919.80'),   Decimal('0.075'), Decimal('2022.24')),
    (Decimal('45012.60'),   Decimal('0.150'), Decimal('4566.23')),
    (Decimal('55976.16'),   Decimal('0.225'), Decimal('7942.17')),
    (Decimal('Infinity'),   Decimal('0.275'), Decimal('10740.98')),
]

DEDUCAO_DEPENDENTE_ANUAL   = Decimal('2275.08')
LIMITE_DEDUCAO_EDUCACAO    = Decimal('3561.50')
DESCONTO_SIMPLIFICADO_PERC = Decimal('0.20')
LIMITE_DESCONTO_SIMPLIFICADO = Decimal('16754.34')

# Alíquotas de ganho de capital (Lei 13.259/2016)
TABELA_GANHO_CAPITAL = [
    (Decimal('5000000.00'),  Decimal('0.150')),
    (Decimal('10000000.00'), Decimal('0.175')),
    (Decimal('30000000.00'), Decimal('0.200')),
    (Decimal('Infinity'),    Decimal('0.225')),
]

# Ações — regras específicas (IN RFB 1.585/2015 + Lei 11.033/2004)
ISENCAO_MENSAL_ACOES   = Decimal('20000.00')
ALIQUOTA_ACOES         = Decimal('0.15')
ALIQUOTA_DAY_TRADE     = Decimal('0.20')


# ---------------------------------------------------------------------------
# Funções de cálculo
# ---------------------------------------------------------------------------

def _arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calcular_ir_tabela(base: Decimal) -> Decimal:
    """Aplica a tabela progressiva anual e retorna o IR sobre a base informada."""
    if base <= Decimal('0'):
        return Decimal('0.00')
    for limite, aliquota, parcela in TABELA_ANUAL_2024:
        if base <= limite:
            return _arredondar(base * aliquota - parcela)
    return Decimal('0.00')


def calcular_modelo_completo(declaracao) -> dict:
    """
    Calcula o IR no modelo completo (deduções legais).
    Retorna dict com base_calculo, ir_devido, total_deducoes.
    """
    rendimentos_tributaveis = sum(
        (r.valor_bruto
         for r in declaracao.rendimentos.all()
         if r.tipo not in TIPOS_TRIBUTACAO_EXCLUSIVA),
        Decimal('0'),
    )

    # Deduções legais
    total_deducoes = Decimal('0')

    # Dependentes (valor fixo por dependente)
    qtd_dependentes = declaracao.dependentes.count()
    total_deducoes += DEDUCAO_DEPENDENTE_ANUAL * qtd_dependentes

    # Educação: agrupa por beneficiário e aplica o limite por pessoa
    educacao_por_beneficiario: dict[str, Decimal] = {}
    for deducao in declaracao.deducoes.filter(tipo='educacao'):
        chave = deducao.cpf_cnpj_beneficiario or f'_sem_cpf_{deducao.pk}'
        educacao_por_beneficiario[chave] = (
            educacao_por_beneficiario.get(chave, Decimal('0')) + deducao.valor
        )
    for valor_pessoa in educacao_por_beneficiario.values():
        total_deducoes += min(valor_pessoa, LIMITE_DEDUCAO_EDUCACAO)

    # Demais deduções
    for deducao in declaracao.deducoes.exclude(tipo='educacao'):
        if deducao.tipo == 'saude':
            total_deducoes += deducao.valor  # sem limite
        elif deducao.tipo in ('inss', 'pgbl', 'pensao_paga', 'livro_caixa'):
            total_deducoes += deducao.valor

    base_calculo = max(rendimentos_tributaveis - total_deducoes, Decimal('0'))
    ir_devido = calcular_ir_tabela(base_calculo)

    return {
        'modelo': 'completo',
        'rendimentos_tributaveis': _arredondar(rendimentos_tributaveis),
        'total_deducoes': _arredondar(total_deducoes),
        'base_calculo': _arredondar(base_calculo),
        'ir_devido': ir_devido,
    }


def calcular_modelo_simplificado(declaracao) -> dict:
    """
    Calcula o IR no modelo simplificado (desconto padrão de 20%, limite R$16.754,34).
    """
    rendimentos_tributaveis = sum(
        (r.valor_bruto
         for r in declaracao.rendimentos.all()
         if r.tipo not in TIPOS_TRIBUTACAO_EXCLUSIVA),
        Decimal('0'),
    )

    desconto = min(
        rendimentos_tributaveis * DESCONTO_SIMPLIFICADO_PERC,
        LIMITE_DESCONTO_SIMPLIFICADO,
    )
    base_calculo = max(rendimentos_tributaveis - desconto, Decimal('0'))
    ir_devido = calcular_ir_tabela(base_calculo)

    return {
        'modelo': 'simplificado',
        'rendimentos_tributaveis': _arredondar(rendimentos_tributaveis),
        'desconto_aplicado': _arredondar(desconto),
        'base_calculo': _arredondar(base_calculo),
        'ir_devido': ir_devido,
    }


def recomendar_modelo(declaracao) -> dict:
    """
    Calcula os dois modelos e retorna o mais vantajoso com comparativo.
    """
    completo = calcular_modelo_completo(declaracao)
    simplificado = calcular_modelo_simplificado(declaracao)

    if completo['ir_devido'] <= simplificado['ir_devido']:
        recomendado = 'completo'
        economia = simplificado['ir_devido'] - completo['ir_devido']
    else:
        recomendado = 'simplificado'
        economia = completo['ir_devido'] - simplificado['ir_devido']

    return {
        'recomendado': recomendado,
        'economia': _arredondar(economia),
        'completo': completo,
        'simplificado': simplificado,
    }


TIPOS_TRIBUTACAO_EXCLUSIVA = frozenset({
    'isento', 'exclusivo_fonte', 'jcp', 'dividendo', 'rendimento_fii',
})

def calcular_ir_retido_total(declaracao) -> Decimal:
    """
    Soma o IR retido apenas dos rendimentos que são adiantamento do ajuste anual.
    Tipos de tributação exclusiva/definitiva (JCP, dividendos, etc.) têm imposto
    já encerrado na fonte e não entram no confronto IR devido × IR retido.
    """
    return _arredondar(sum(
        r.ir_retido for r in declaracao.rendimentos.all()
        if r.tipo not in TIPOS_TRIBUTACAO_EXCLUSIVA
    ))


def calcular_resultado_final(declaracao, modelo: str = None) -> dict:
    """
    Calcula o resultado final: imposto a pagar ou a restituir.
    modelo: 'completo' | 'simplificado' | None (usa o recomendado)
    """
    recomendacao = recomendar_modelo(declaracao)
    if modelo is None:
        modelo = recomendacao['recomendado']

    calculo = recomendacao[modelo]
    ir_devido = calculo['ir_devido']
    ir_retido = calcular_ir_retido_total(declaracao)
    resultado = ir_retido - ir_devido  # positivo = restituição / negativo = a pagar

    return {
        'modelo_usado': modelo,
        'ir_devido': ir_devido,
        'ir_retido': ir_retido,
        'resultado': _arredondar(resultado),
        'situacao': 'restituicao' if resultado >= 0 else 'imposto_a_pagar',
        'recomendacao': recomendacao,
    }


def calcular_ganho_capital_acoes(
    total_vendas_mes: Decimal,
    custo_total_mes: Decimal,
    day_trade: bool = False,
) -> dict:
    """
    Calcula IR sobre operações com ações no mês (DARF 6015).

    Regras:
    - Day trade: 20% sobre o lucro líquido, sem isenção mensal.
    - Operação normal: isento se total de vendas no mês <= R$ 20.000;
      caso contrário 15% sobre o lucro líquido.
    - Prejuízo: IR = 0 (compensar em meses futuros).
    """
    ganho = total_vendas_mes - custo_total_mes

    if day_trade:
        if ganho <= Decimal('0'):
            return {
                'ganho': _arredondar(ganho),
                'ir_devido': Decimal('0.00'),
                'isento': False,
                'day_trade': True,
            }
        ir = _arredondar(ganho * ALIQUOTA_DAY_TRADE)
        return {
            'ganho': _arredondar(ganho),
            'ir_devido': ir,
            'isento': False,
            'day_trade': True,
            'aliquota': ALIQUOTA_DAY_TRADE,
        }

    # Operação normal
    if total_vendas_mes <= ISENCAO_MENSAL_ACOES:
        return {
            'ganho': _arredondar(ganho),
            'ir_devido': Decimal('0.00'),
            'isento': True,
            'day_trade': False,
        }

    if ganho <= Decimal('0'):
        return {
            'ganho': _arredondar(ganho),
            'ir_devido': Decimal('0.00'),
            'isento': False,
            'day_trade': False,
        }

    ir = _arredondar(ganho * ALIQUOTA_ACOES)
    return {
        'ganho': _arredondar(ganho),
        'ir_devido': ir,
        'isento': False,
        'day_trade': False,
        'aliquota': ALIQUOTA_ACOES,
    }


def calcular_ganho_capital(custo: Decimal, venda: Decimal) -> dict:
    """
    Calcula o IR sobre ganho de capital com alíquotas progressivas (Lei 13.259/2016).
    """
    ganho = venda - custo
    if ganho <= 0:
        return {'ganho': _arredondar(ganho), 'ir_devido': Decimal('0.00'), 'aliquota': Decimal('0')}

    anterior = Decimal('0')
    ir_total = Decimal('0')
    for limite, aliquota in TABELA_GANHO_CAPITAL:
        faixa = min(ganho, limite) - anterior
        if faixa <= 0:
            break
        ir_total += faixa * aliquota
        anterior = limite

    return {
        'ganho': _arredondar(ganho),
        'ir_devido': _arredondar(ir_total),
        'aliquota_efetiva': _arredondar(ir_total / ganho * 100),
    }
