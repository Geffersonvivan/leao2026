"""
Motor de auditoria preventiva da declaração IRPF.

Duas camadas:
  1. Regras determinísticas — verificações rápidas, sempre executadas
  2. Análise IA (Claude) — revisão semântica profunda, sob demanda

Cada alerta tem:
  - nivel: 'erro' | 'aviso' | 'dica'
  - titulo: str
  - detalhe: str
  - campo: str (área relacionada: rendimentos, deducoes, dependentes, bens, geral)
"""
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Literal

from .calculadora import (
    DEDUCAO_DEPENDENTE_ANUAL,
    LIMITE_DEDUCAO_EDUCACAO,
    ISENCAO_MENSAL_ACOES,
    TIPOS_TRIBUTACAO_EXCLUSIVA,
    recomendar_modelo,
    calcular_resultado_final,
)

Nivel = Literal['erro', 'aviso', 'dica']
Campo = Literal['rendimentos', 'deducoes', 'dependentes', 'bens', 'geral']


@dataclass
class Alerta:
    nivel: Nivel
    titulo: str
    detalhe: str
    campo: Campo = 'geral'


@dataclass
class RelatorioAuditoria:
    alertas: list = field(default_factory=list)
    simulacao: dict = field(default_factory=dict)
    resultado: dict = field(default_factory=dict)

    @property
    def erros(self):
        return [a for a in self.alertas if a.nivel == 'erro']

    @property
    def avisos(self):
        return [a for a in self.alertas if a.nivel == 'aviso']

    @property
    def dicas(self):
        return [a for a in self.alertas if a.nivel == 'dica']

    @property
    def total(self):
        return len(self.alertas)

    @property
    def tem_problemas_criticos(self):
        return len(self.erros) > 0


# ─── Regras determinísticas ──────────────────────────────────────────────────

def auditar(declaracao) -> RelatorioAuditoria:
    """Executa todas as regras e retorna o relatório."""
    rel = RelatorioAuditoria()

    _verificar_rendimentos(declaracao, rel)
    _verificar_duplicatas_rendimentos(declaracao, rel)
    _verificar_deducoes(declaracao, rel)
    _verificar_dependentes(declaracao, rel)
    _verificar_bens(declaracao, rel)
    _verificar_consistencia_geral(declaracao, rel)
    _sugerir_deducoes_esquecidas(declaracao, rel)
    _verificar_ganhos_capital(declaracao, rel)

    if declaracao.rendimentos.exists():
        rel.simulacao = recomendar_modelo(declaracao)
        rel.resultado = calcular_resultado_final(declaracao)

    return rel


# ── Rendimentos ───────────────────────────────────────────────────────────────

def _verificar_rendimentos(declaracao, rel: RelatorioAuditoria):
    rendimentos = list(declaracao.rendimentos.all())

    if not rendimentos:
        rel.alertas.append(Alerta(
            nivel='erro',
            titulo='Nenhum rendimento declarado',
            detalhe='É obrigatório informar ao menos um rendimento. Adicione seus rendimentos antes de continuar.',
            campo='rendimentos',
        ))
        return

    renda_tributavel = sum(
        r.valor_bruto for r in rendimentos
        if r.tipo not in TIPOS_TRIBUTACAO_EXCLUSIVA
    )
    ir_retido_total = sum(r.ir_retido for r in rendimentos)

    # Renda acima do limite de isenção mas sem IR retido
    if renda_tributavel > Decimal('33888.00') and ir_retido_total == 0:
        rel.alertas.append(Alerta(
            nivel='aviso',
            titulo='Renda tributável acima do limite sem IR retido',
            detalhe=f'Sua renda tributável (R$ {renda_tributavel:.2f}) supera R$ 33.888,00 '
                    f'mas o IR retido informado é zero. Verifique os informes de rendimento.',
            campo='rendimentos',
        ))

    # IR retido desproporcional à renda
    if renda_tributavel > Decimal('50000') and ir_retido_total < renda_tributavel * Decimal('0.03'):
        rel.alertas.append(Alerta(
            nivel='aviso',
            titulo='IR retido muito baixo para a renda declarada',
            detalhe=f'Renda tributável de R$ {renda_tributavel:.2f} com apenas '
                    f'R$ {ir_retido_total:.2f} de IR retido. Isso pode indicar dados incompletos.',
            campo='rendimentos',
        ))

    # Rendimentos sem CNPJ/CPF da fonte pagadora
    sem_doc = [r for r in rendimentos if not r.fonte_pagadora_cnpj_cpf and r.tipo != 'autonomo']
    if sem_doc:
        rel.alertas.append(Alerta(
            nivel='aviso',
            titulo=f'{len(sem_doc)} rendimento(s) sem CNPJ/CPF da fonte pagadora',
            detalhe='Informar o CNPJ ou CPF da fonte pagadora reduz o risco de malha fina, '
                    'pois a Receita Federal cruza esses dados automaticamente.',
            campo='rendimentos',
        ))

    # Renda de autônomo sem carnê-leão
    autonomo = [r for r in rendimentos if r.tipo == 'autonomo']
    if autonomo:
        total_autonomo = sum(r.valor_bruto for r in autonomo)
        if total_autonomo > Decimal('26963.20'):
            rel.alertas.append(Alerta(
                nivel='aviso',
                titulo='Rendimento autônomo acima da isenção — verifique o carnê-leão',
                detalhe=f'Você declarou R$ {total_autonomo:.2f} de trabalho autônomo. '
                        'Rendimentos de PF para PF exigem recolhimento mensal via carnê-leão (código DARF 0190). '
                        'Confirme se os DARFs foram recolhidos no prazo.',
                campo='rendimentos',
            ))

    # Aluguel de PF sem carnê-leão
    alugueis = [r for r in rendimentos if r.tipo == 'aluguel' and not r.fonte_pagadora_cnpj_cpf]
    if alugueis:
        rel.alertas.append(Alerta(
            nivel='dica',
            titulo='Aluguel recebido de pessoa física — confirme o carnê-leão',
            detalhe='Aluguéis pagos por pessoa física devem ser recolhidos mensalmente '
                    'via carnê-leão. Verifique se os DARFs foram pagos em dia.',
            campo='rendimentos',
        ))


# ── Deduções ─────────────────────────────────────────────────────────────────

def _verificar_deducoes(declaracao, rel: RelatorioAuditoria):
    deducoes = list(declaracao.deducoes.all())

    # Deduções de saúde sem CPF/CNPJ do prestador
    saude_sem_doc = [d for d in deducoes if d.tipo == 'saude' and not d.cpf_cnpj_beneficiario]
    if saude_sem_doc:
        total = sum(d.valor for d in saude_sem_doc)
        rel.alertas.append(Alerta(
            nivel='aviso',
            titulo=f'Despesas médicas sem CPF/CNPJ do prestador (R$ {total:.2f})',
            detalhe='A Receita Federal cruza os dados de despesas médicas com os informes dos prestadores. '
                    'Deduções sem identificação do prestador têm alto risco de malha fina.',
            campo='deducoes',
        ))

    # Educação acima do limite por beneficiário
    educacao_total = sum(d.valor for d in deducoes if d.tipo == 'educacao')
    qtd_dependentes = declaracao.dependentes.count()
    limite_total_educacao = LIMITE_DEDUCAO_EDUCACAO * (1 + qtd_dependentes)
    if educacao_total > limite_total_educacao:
        rel.alertas.append(Alerta(
            nivel='aviso',
            titulo='Deduções de educação podem ultrapassar o limite',
            detalhe=f'O limite de educação é R$ {LIMITE_DEDUCAO_EDUCACAO:.2f}/pessoa. '
                    f'Com {1 + qtd_dependentes} pessoa(s), o teto é R$ {limite_total_educacao:.2f}. '
                    f'O sistema aplicará o limite automaticamente, mas verifique os valores.',
            campo='deducoes',
        ))

    # PGBL acima de 12% da renda
    renda_tributavel = sum(
        r.valor_bruto for r in declaracao.rendimentos.all()
        if r.tipo not in TIPOS_TRIBUTACAO_EXCLUSIVA
    )
    pgbl = sum(d.valor for d in deducoes if d.tipo == 'pgbl')
    if pgbl > 0 and renda_tributavel > 0:
        limite_pgbl = renda_tributavel * Decimal('0.12')
        if pgbl > limite_pgbl:
            rel.alertas.append(Alerta(
                nivel='aviso',
                titulo=f'PGBL declarado (R$ {pgbl:.2f}) ultrapassa o limite dedutível',
                detalhe=f'O limite do PGBL é 12% da renda bruta tributável. '
                        f'Com renda de R$ {renda_tributavel:.2f}, o teto é R$ {limite_pgbl:.2f}. '
                        f'O excedente de R$ {pgbl - limite_pgbl:.2f} não será deduzido.',
                campo='deducoes',
            ))

    # Pensão paga sem comprovante judicial
    pensao = [d for d in deducoes if d.tipo == 'pensao_paga']
    if pensao:
        rel.alertas.append(Alerta(
            nivel='dica',
            titulo='Pensão alimentícia deduzida — guarde o documento judicial',
            detalhe='Só é dedutível a pensão paga por determinação judicial ou acordo homologado em juízo. '
                    'Guarde o documento para comprovação em caso de fiscalização.',
            campo='deducoes',
        ))


# ── Dependentes ───────────────────────────────────────────────────────────────

def _verificar_dependentes(declaracao, rel: RelatorioAuditoria):
    dependentes = list(declaracao.dependentes.all())
    if not dependentes:
        return

    # CPFs duplicados
    cpfs = [d.cpf for d in dependentes if d.cpf]
    if len(cpfs) != len(set(cpfs)):
        rel.alertas.append(Alerta(
            nivel='erro',
            titulo='Dependentes com CPF duplicado',
            detalhe='Há dois ou mais dependentes com o mesmo CPF. '
                    'Cada dependente deve ser informado apenas uma vez.',
            campo='dependentes',
        ))

    # Dependentes sem CPF
    sem_cpf = [d for d in dependentes if not d.cpf]
    if sem_cpf:
        rel.alertas.append(Alerta(
            nivel='aviso',
            titulo=f'{len(sem_cpf)} dependente(s) sem CPF informado',
            detalhe='A Receita Federal exige o CPF de todos os dependentes maiores de 8 anos. '
                    'Menores de 8 anos são dispensados, mas é recomendado informar.',
            campo='dependentes',
        ))

    # Filhos universitários — verifica se está dentro do limite de idade
    from datetime import date
    hoje = date.today()
    for dep in dependentes:
        if dep.parentesco == 'filho' and dep.data_nascimento:
            idade = (hoje - dep.data_nascimento).days // 365
            if idade > 24:
                rel.alertas.append(Alerta(
                    nivel='aviso',
                    titulo=f'Dependente {dep.nome} pode não ser elegível',
                    detalhe=f'Filhos/enteados acima de 24 anos só são elegíveis como dependentes '
                            f'se forem incapacitados física ou mentalmente. '
                            f'Verifique a elegibilidade deste dependente.',
                    campo='dependentes',
                ))


# ── Bens e Direitos ──────────────────────────────────────────────────────────

def _verificar_bens(declaracao, rel: RelatorioAuditoria):
    bens = list(declaracao.bens.all())
    if not bens:
        return

    total_bens = sum(b.valor_atual for b in bens)

    if total_bens > Decimal('800000'):
        rel.alertas.append(Alerta(
            nivel='dica',
            titulo=f'Total de bens e direitos: R$ {total_bens:,.2f}',
            detalhe='Patrimônio acima de R$ 800.000,00 é um dos critérios de obrigatoriedade da declaração. '
                    'Certifique-se de que todos os bens relevantes estão declarados.',
            campo='bens',
        ))

    # Bens com variação patrimonial incompatível com a renda
    renda_total = sum(
        r.valor_bruto for r in declaracao.rendimentos.all()
        if r.tipo not in TIPOS_TRIBUTACAO_EXCLUSIVA
    )
    aquisicoes = sum(
        max(b.valor_atual - b.valor_anterior, Decimal('0')) for b in bens
    )
    if renda_total > 0 and aquisicoes > renda_total * Decimal('1.5'):
        rel.alertas.append(Alerta(
            nivel='aviso',
            titulo='Variação patrimonial elevada em relação à renda',
            detalhe=f'A variação de bens (R$ {aquisicoes:.2f}) é muito superior à renda declarada '
                    f'(R$ {renda_total:.2f}). A Receita Federal pode questionar a origem dos recursos. '
                    'Certifique-se de declarar todas as fontes de renda.',
            campo='bens',
        ))


# ── Consistência geral ────────────────────────────────────────────────────────

def _verificar_consistencia_geral(declaracao, rel: RelatorioAuditoria):
    renda_tributavel = sum(
        r.valor_bruto for r in declaracao.rendimentos.all()
        if r.tipo not in TIPOS_TRIBUTACAO_EXCLUSIVA
    )

    # Obrigatoriedade de declarar
    renda_isentas = sum(
        r.valor_bruto for r in declaracao.rendimentos.filter(tipo='isento')
    )
    if renda_isentas > Decimal('200000') or renda_tributavel > Decimal('33888'):
        rel.alertas.append(Alerta(
            nivel='dica',
            titulo='Declaração obrigatória confirmada',
            detalhe='Com base nos rendimentos informados, você está obrigado a declarar o IRPF '
                    f'{declaracao.ano_base + 1}. Prazo: 30 de abril de {declaracao.ano_base + 1}.',
            campo='geral',
        ))

    # Declaração sem deduções com renda alta — pode valer preencher o completo
    total_deducoes = sum(d.valor for d in declaracao.deducoes.all())
    qtd_dependentes = declaracao.dependentes.count()
    deducoes_efetivas = total_deducoes + (DEDUCAO_DEPENDENTE_ANUAL * qtd_dependentes)
    if renda_tributavel > Decimal('50000') and deducoes_efetivas < Decimal('3000'):
        rel.alertas.append(Alerta(
            nivel='dica',
            titulo='Poucas deduções para uma renda elevada',
            detalhe='Com renda acima de R$ 50.000, vale a pena verificar se há deduções não informadas: '
                    'plano de saúde, consultas médicas, faculdade ou dependentes.',
            campo='deducoes',
        ))


# ── Deduções esquecidas ───────────────────────────────────────────────────────

def _sugerir_deducoes_esquecidas(declaracao, rel: RelatorioAuditoria):
    tipos_deducoes = {d.tipo for d in declaracao.deducoes.all()}
    tem_dependentes = declaracao.dependentes.exists()

    # Tem salário mas não informou INSS
    tem_salario = declaracao.rendimentos.filter(tipo='salario').exists()
    if tem_salario and 'inss' not in tipos_deducoes:
        inss_retido = sum(
            r.inss_retido for r in declaracao.rendimentos.filter(tipo='salario')
        )
        if inss_retido == 0:
            rel.alertas.append(Alerta(
                nivel='dica',
                titulo='INSS não informado nos rendimentos de salário',
                detalhe='Se você é empregado CLT, o INSS retido é dedutível e aparece no informe de rendimentos. '
                        'Verifique se o valor de INSS retido está preenchido nos seus rendimentos.',
                campo='rendimentos',
            ))

    # Tem dependentes mas nenhuma despesa médica/educação
    if tem_dependentes and 'saude' not in tipos_deducoes and 'educacao' not in tipos_deducoes:
        rel.alertas.append(Alerta(
            nivel='dica',
            titulo='Dependentes sem despesas médicas ou educação declaradas',
            detalhe='Você tem dependentes, mas não informou despesas de saúde ou educação. '
                    'Se houver gastos com médicos, dentistas, plano de saúde ou escola, adicione-os para reduzir o IR.',
            campo='deducoes',
        ))

    # Tem plano de saúde? (heurística por valor alto de saúde)
    if 'saude' not in tipos_deducoes:
        rel.alertas.append(Alerta(
            nivel='dica',
            titulo='Despesas médicas e de saúde não informadas',
            detalhe='Consultas médicas, dentistas, planos de saúde, exames e internações são dedutíveis '
                    'sem limite de valor. Não esqueça de declarar se tiver esses gastos.',
            campo='deducoes',
        ))


# ── Duplicatas de rendimentos ─────────────────────────────────────────────────

def _verificar_duplicatas_rendimentos(declaracao, rel: RelatorioAuditoria):
    """Detecta rendimentos com mesma fonte, mesmo tipo e valor muito próximo."""
    rendimentos = list(declaracao.rendimentos.all())
    duplicatas_encontradas = set()

    for i, r1 in enumerate(rendimentos):
        if not r1.fonte_pagadora_cnpj_cpf:
            continue
        for r2 in rendimentos[i + 1:]:
            if r1.pk in duplicatas_encontradas or r2.pk in duplicatas_encontradas:
                continue
            if (
                r1.tipo == r2.tipo
                and r1.fonte_pagadora_cnpj_cpf == r2.fonte_pagadora_cnpj_cpf
                and r2.valor_bruto > Decimal('0')
            ):
                # Considera duplicata se a diferença for menor que 1%
                diferenca = abs(r1.valor_bruto - r2.valor_bruto)
                tolerancia = r1.valor_bruto * Decimal('0.01')
                if diferenca <= tolerancia:
                    duplicatas_encontradas.add(r1.pk)
                    duplicatas_encontradas.add(r2.pk)
                    rel.alertas.append(Alerta(
                        nivel='aviso',
                        titulo='Possível rendimento duplicado',
                        detalhe=f'Dois registros do tipo "{r1.get_tipo_display()}" com a mesma fonte '
                                f'({r1.fonte_pagadora_cnpj_cpf}) e valores muito próximos '
                                f'(R$ {r1.valor_bruto:.2f} e R$ {r2.valor_bruto:.2f}). '
                                'Verifique se o mesmo informe foi importado duas vezes.',
                        campo='rendimentos',
                    ))


# ── Ganhos de capital ─────────────────────────────────────────────────────────

def _verificar_ganhos_capital(declaracao, rel: RelatorioAuditoria):
    ganhos = list(declaracao.ganhos_capital.all())
    if not ganhos:
        return

    # DARF não recolhido para ganhos tributáveis
    sem_darf = [
        g for g in ganhos
        if not g.isento
        and not g.darf_recolhido
        and (g.valor_venda - g.custo_aquisicao) > Decimal('0')
    ]
    if sem_darf:
        total_ir_pendente = sum(
            (g.valor_venda - g.custo_aquisicao) * Decimal('0.15')
            for g in sem_darf
        )
        rel.alertas.append(Alerta(
            nivel='erro',
            titulo=f'{len(sem_darf)} ganho(s) de capital sem DARF recolhido',
            detalhe=f'Há {len(sem_darf)} alienação(ões) com lucro tributável sem DARF marcado como pago. '
                    f'IR estimado pendente: R$ {total_ir_pendente:.2f}. '
                    'O DARF deve ser recolhido até o último dia útil do mês seguinte à venda (código 6015 para ações).',
            campo='bens',
        ))

    # Verificar isenção mensal para ações — agrupa vendas por mês/ano
    from collections import defaultdict
    vendas_por_mes: dict = defaultdict(Decimal)
    ganhos_acoes = [
        g for g in ganhos
        if any(k in g.tipo_bem.lower() for k in ('ação', 'acao', 'acoes', 'ações', 'bolsa', 'fii', 'etf'))
    ]
    for g in ganhos_acoes:
        chave = (g.data_alienacao.year, g.data_alienacao.month)
        vendas_por_mes[chave] += g.valor_venda

    meses_acima_isencao = [
        f'{m:02d}/{a}' for (a, m), total in vendas_por_mes.items()
        if total > ISENCAO_MENSAL_ACOES
    ]
    meses_marcados_isentos = [
        f'{g.data_alienacao.month:02d}/{g.data_alienacao.year}'
        for g in ganhos_acoes
        if g.isento
    ]

    if meses_acima_isencao:
        rel.alertas.append(Alerta(
            nivel='aviso',
            titulo=f'Vendas de ações acima de R$ 20.000 em: {", ".join(sorted(meses_acima_isencao))}',
            detalhe='O limite de isenção para ações é R$ 20.000 em vendas por mês. '
                    'Nos meses acima desse valor, o lucro líquido é tributado a 15% (DARF 6015). '
                    'Verifique se o IR foi recolhido nesses meses.',
            campo='bens',
        ))

    if meses_marcados_isentos and meses_acima_isencao:
        cruzamento = set(meses_marcados_isentos) & set(meses_acima_isencao)
        if cruzamento:
            rel.alertas.append(Alerta(
                nivel='erro',
                titulo='Isenção aplicada em mês com vendas acima do limite',
                detalhe=f'Nos meses {", ".join(sorted(cruzamento))} há ganhos marcados como isentos, '
                        f'mas o total de vendas superou R$ {ISENCAO_MENSAL_ACOES:,.2f}. '
                        'A isenção não se aplica quando o total de alienações do mês ultrapassa esse valor.',
                campo='bens',
            ))

    # Prejuízos sem compensação futura
    prejuizos = [g for g in ganhos if (g.valor_venda - g.custo_aquisicao) < Decimal('0')]
    if prejuizos:
        total_prejuizo = sum(g.custo_aquisicao - g.valor_venda for g in prejuizos)
        rel.alertas.append(Alerta(
            nivel='dica',
            titulo=f'Prejuízo de capital de R$ {total_prejuizo:.2f} — pode compensar lucros futuros',
            detalhe='Perdas em alienações de bens podem ser compensadas em meses ou anos posteriores '
                    'para reduzir o IR sobre ganhos futuros. Guarde os registros de cada operação.',
            campo='bens',
        ))
