"""
Testes do motor de cálculo IRPF e regras de auditoria.

Execução:
    python manage.py test declaracao
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .calculadora import (
    ISENCAO_MENSAL_ACOES,
    LIMITE_DEDUCAO_EDUCACAO,
    calcular_ganho_capital,
    calcular_ganho_capital_acoes,
    calcular_ir_tabela,
    calcular_modelo_completo,
    calcular_modelo_simplificado,
    calcular_resultado_final,
    recomendar_modelo,
)
from .auditoria import auditar
from .models import Declaracao, Deducao, GanhoCapital, Rendimento

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _usuario():
    return User.objects.create_user(username='teste', password='123', email='t@t.com')


def _declaracao(usuario=None):
    u = usuario or _usuario()
    return Declaracao.objects.create(usuario=u, ano_base=2024)


def _rendimento(declaracao, tipo='salario', valor=60000, ir=5000, inss=3000, cnpj='11.222.333/0001-44'):
    return Rendimento.objects.create(
        declaracao=declaracao,
        tipo=tipo,
        fonte_pagadora_nome='Empresa Teste',
        fonte_pagadora_cnpj_cpf=cnpj,
        valor_bruto=Decimal(str(valor)),
        ir_retido=Decimal(str(ir)),
        inss_retido=Decimal(str(inss)),
    )


def _deducao(declaracao, tipo='saude', valor=5000, cpf=''):
    return Deducao.objects.create(
        declaracao=declaracao,
        tipo=tipo,
        descricao='Teste',
        valor=Decimal(str(valor)),
        cpf_cnpj_beneficiario=cpf,
    )


# ─── 1. Tabela progressiva de IR ──────────────────────────────────────────────

class TestIRTabela(TestCase):

    def test_isento_zero(self):
        self.assertEqual(calcular_ir_tabela(Decimal('0')), Decimal('0.00'))

    def test_isento_limite_exato(self):
        # Até R$ 26.963,20 → alíquota 0%
        self.assertEqual(calcular_ir_tabela(Decimal('26963.20')), Decimal('0.00'))

    def test_faixa_75(self):
        # R$ 27.000 → 27000 * 0,075 − 2022,24 = 2025,00 − 2022,24 = 2,76
        resultado = calcular_ir_tabela(Decimal('27000.00'))
        self.assertEqual(resultado, Decimal('2.76'))

    def test_faixa_15(self):
        # R$ 40.000 → 40000 * 0,15 − 4566,23 = 6000 − 4566,23 = 1433,77
        resultado = calcular_ir_tabela(Decimal('40000.00'))
        self.assertEqual(resultado, Decimal('1433.77'))

    def test_faixa_275(self):
        # R$ 60.000 → 60000 * 0,275 − 10740,98 = 16500 − 10740,98 = 5759,02
        resultado = calcular_ir_tabela(Decimal('60000.00'))
        self.assertEqual(resultado, Decimal('5759.02'))

    def test_base_negativa_retorna_zero(self):
        self.assertEqual(calcular_ir_tabela(Decimal('-100')), Decimal('0.00'))


# ─── 2. Ganho de capital progressivo (imóvel, etc.) ──────────────────────────

class TestGanhoCapitalGeral(TestCase):

    def test_prejuizo_ir_zero(self):
        # custo=100000, venda=80000 → ganho negativo → IR = 0
        r = calcular_ganho_capital(Decimal('100000'), Decimal('80000'))
        self.assertEqual(r['ir_devido'], Decimal('0.00'))

    def test_ganho_primeira_faixa(self):
        # Ganho de R$ 10.000 → 15% = R$ 1.500
        r = calcular_ganho_capital(Decimal('90000'), Decimal('100000'))
        self.assertEqual(r['ir_devido'], Decimal('1500.00'))

    def test_ganho_faixa_progressiva(self):
        # Ganho de R$ 5.000.001 → primeiros 5M a 15% + 1 real a 17,5%
        custo = Decimal('0')
        venda = Decimal('5000001')
        r = calcular_ganho_capital(custo, venda)
        esperado = Decimal('5000000') * Decimal('0.15') + Decimal('1') * Decimal('0.175')
        self.assertEqual(r['ir_devido'], Decimal(str(esperado)).quantize(Decimal('0.01')))


# ─── 2. Ganho de capital — ações com isenção mensal ──────────────────────────

class TestGanhoCapitalAcoes(TestCase):

    def test_vendas_abaixo_isencao_sao_isentas(self):
        # Venda de R$ 15.000 → isento
        r = calcular_ganho_capital_acoes(
            total_vendas_mes=Decimal('15000'),
            custo_total_mes=Decimal('10000'),
        )
        self.assertTrue(r['isento'])
        self.assertEqual(r['ir_devido'], Decimal('0.00'))

    def test_vendas_no_limite_exato_isentas(self):
        r = calcular_ganho_capital_acoes(
            total_vendas_mes=ISENCAO_MENSAL_ACOES,
            custo_total_mes=Decimal('5000'),
        )
        self.assertTrue(r['isento'])
        self.assertEqual(r['ir_devido'], Decimal('0.00'))

    def test_vendas_acima_isencao_tributadas_15(self):
        # Venda de R$ 25.000, custo R$ 10.000 → lucro R$ 15.000 → IR = 15% * 15000 = 2250
        r = calcular_ganho_capital_acoes(
            total_vendas_mes=Decimal('25000'),
            custo_total_mes=Decimal('10000'),
        )
        self.assertFalse(r['isento'])
        self.assertEqual(r['ir_devido'], Decimal('2250.00'))
        self.assertEqual(r['aliquota'], Decimal('0.15'))

    def test_vendas_acima_isencao_com_prejuizo_ir_zero(self):
        # Venda de R$ 25.000, custo R$ 26.000 → prejuízo → IR = 0
        r = calcular_ganho_capital_acoes(
            total_vendas_mes=Decimal('25000'),
            custo_total_mes=Decimal('26000'),
        )
        self.assertFalse(r['isento'])
        self.assertEqual(r['ir_devido'], Decimal('0.00'))

    def test_day_trade_sem_isencao_20_porcento(self):
        # Day trade lucro R$ 5.000 → IR = 20% = R$ 1.000
        r = calcular_ganho_capital_acoes(
            total_vendas_mes=Decimal('5000'),
            custo_total_mes=Decimal('0'),
            day_trade=True,
        )
        self.assertFalse(r['isento'])
        self.assertTrue(r['day_trade'])
        self.assertEqual(r['ir_devido'], Decimal('1000.00'))

    def test_day_trade_abaixo_20k_nao_isento(self):
        # Day trade não tem isenção mensal — mesmo abaixo de R$20k
        r = calcular_ganho_capital_acoes(
            total_vendas_mes=Decimal('10000'),
            custo_total_mes=Decimal('9000'),
            day_trade=True,
        )
        self.assertFalse(r['isento'])
        self.assertEqual(r['ir_devido'], Decimal('200.00'))

    def test_day_trade_prejuizo_ir_zero(self):
        r = calcular_ganho_capital_acoes(
            total_vendas_mes=Decimal('1000'),
            custo_total_mes=Decimal('2000'),
            day_trade=True,
        )
        self.assertEqual(r['ir_devido'], Decimal('0.00'))


# ─── 3. Educação por beneficiário ─────────────────────────────────────────────

class TestEducacaoPorBeneficiario(TestCase):

    def setUp(self):
        self.usuario = _usuario()
        self.dec = _declaracao(self.usuario)
        _rendimento(self.dec, valor=100000)

    def test_mesmo_beneficiario_limite_unico(self):
        # Dois lançamentos do mesmo CPF: R$ 3000 + R$ 2000 = R$ 5000
        # Limite é R$ 3.561,50 → deve deduzir apenas R$ 3.561,50
        _deducao(self.dec, tipo='educacao', valor=3000, cpf='111.222.333-44')
        _deducao(self.dec, tipo='educacao', valor=2000, cpf='111.222.333-44')

        resultado = calcular_modelo_completo(self.dec)
        deducao_educacao = LIMITE_DEDUCAO_EDUCACAO  # R$ 3.561,50

        self.assertIn('total_deducoes', resultado)
        # A dedução de educação não deve ultrapassar o limite por pessoa
        self.assertLessEqual(
            resultado['total_deducoes'],
            deducao_educacao,
            msg='Deduções de educação do mesmo beneficiário ultrapassaram o limite'
        )

    def test_beneficiarios_diferentes_limites_separados(self):
        # Dois CPFs diferentes: R$ 2.000 cada → total R$ 4.000 (abaixo do limite por pessoa)
        _deducao(self.dec, tipo='educacao', valor=2000, cpf='111.222.333-44')
        _deducao(self.dec, tipo='educacao', valor=2000, cpf='555.666.777-88')

        resultado = calcular_modelo_completo(self.dec)
        # Deve deduzir R$ 4.000 (2000 + 2000, ambos abaixo do limite individual)
        self.assertEqual(resultado['total_deducoes'], Decimal('4000.00'))

    def test_limite_por_pessoa_aplicado_individualmente(self):
        # Pessoa A: R$ 5.000 → limitado a R$ 3.561,50
        # Pessoa B: R$ 5.000 → limitado a R$ 3.561,50
        # Total esperado: R$ 7.123,00
        _deducao(self.dec, tipo='educacao', valor=5000, cpf='111.222.333-44')
        _deducao(self.dec, tipo='educacao', valor=5000, cpf='555.666.777-88')

        resultado = calcular_modelo_completo(self.dec)
        esperado = LIMITE_DEDUCAO_EDUCACAO * 2
        self.assertEqual(resultado['total_deducoes'], esperado)


# ─── Modelo completo e simplificado ──────────────────────────────────────────

class TestCalculoCompleto(TestCase):

    def setUp(self):
        self.usuario = _usuario()
        self.dec = _declaracao(self.usuario)

    def test_sem_deducoes(self):
        _rendimento(self.dec, valor=60000, ir=5000, inss=0)
        r = calcular_modelo_completo(self.dec)
        self.assertEqual(r['rendimentos_tributaveis'], Decimal('60000.00'))
        self.assertEqual(r['total_deducoes'], Decimal('0.00'))
        # IR = 60000 * 0,275 − 10740,98 = 5759,02
        self.assertEqual(r['ir_devido'], Decimal('5759.02'))

    def test_com_deducao_saude(self):
        _rendimento(self.dec, valor=60000, ir=5000, inss=0)
        _deducao(self.dec, tipo='saude', valor=5000)
        r = calcular_modelo_completo(self.dec)
        # base = 60000 - 5000 = 55000 → faixa 22,5% (até 55976,16)
        # IR = 55000 * 0,225 − 7942,17 = 12375 − 7942,17 = 4432,83
        self.assertEqual(r['base_calculo'], Decimal('55000.00'))
        self.assertEqual(r['ir_devido'], Decimal('4432.83'))

    def test_rendimento_isento_excluido_da_base(self):
        _rendimento(self.dec, tipo='isento', valor=50000, ir=0, inss=0)
        r = calcular_modelo_completo(self.dec)
        self.assertEqual(r['rendimentos_tributaveis'], Decimal('0.00'))
        self.assertEqual(r['ir_devido'], Decimal('0.00'))

    def test_rendimento_exclusivo_fonte_excluido_da_base(self):
        _rendimento(self.dec, tipo='exclusivo_fonte', valor=30000, ir=3000, inss=0)
        r = calcular_modelo_completo(self.dec)
        self.assertEqual(r['rendimentos_tributaveis'], Decimal('0.00'))


class TestCalculoSimplificado(TestCase):

    def setUp(self):
        self.usuario = _usuario()
        self.dec = _declaracao(self.usuario)

    def test_desconto_20_porcento(self):
        _rendimento(self.dec, valor=50000, ir=3000, inss=0)
        r = calcular_modelo_simplificado(self.dec)
        # desconto = 50000 * 0,20 = 10000
        # base = 40000 → 40000 * 0,15 − 4566,23 = 6000 − 4566,23 = 1433,77
        self.assertEqual(r['desconto_aplicado'], Decimal('10000.00'))
        self.assertEqual(r['base_calculo'], Decimal('40000.00'))
        self.assertEqual(r['ir_devido'], Decimal('1433.77'))

    def test_desconto_limitado_a_teto(self):
        # Renda R$ 200.000 → 20% = R$ 40.000, mas teto é R$ 16.754,34
        _rendimento(self.dec, valor=200000, ir=30000, inss=0)
        r = calcular_modelo_simplificado(self.dec)
        self.assertEqual(r['desconto_aplicado'], Decimal('16754.34'))


class TestRecomendacaoModelo(TestCase):

    def setUp(self):
        self.usuario = _usuario()
        self.dec = _declaracao(self.usuario)

    def test_completo_vantajoso_com_muitas_deducoes(self):
        _rendimento(self.dec, valor=100000, ir=10000, inss=0)
        _deducao(self.dec, tipo='saude', valor=30000)  # dedução alta
        r = recomendar_modelo(self.dec)
        self.assertEqual(r['recomendado'], 'completo')
        self.assertGreater(r['economia'], Decimal('0'))

    def test_simplificado_vantajoso_sem_deducoes(self):
        _rendimento(self.dec, valor=60000, ir=5000, inss=0)
        r = recomendar_modelo(self.dec)
        self.assertEqual(r['recomendado'], 'simplificado')

    def test_resultado_final_restituicao(self):
        _rendimento(self.dec, valor=30000, ir=5000, inss=0)
        r = calcular_resultado_final(self.dec)
        # IR retido (5000) > IR devido → restituição
        self.assertEqual(r['situacao'], 'restituicao')
        self.assertGreater(r['resultado'], Decimal('0'))

    def test_resultado_final_imposto_a_pagar(self):
        _rendimento(self.dec, valor=80000, ir=100, inss=0)
        r = calcular_resultado_final(self.dec)
        self.assertEqual(r['situacao'], 'imposto_a_pagar')


# ─── 4. Auditoria — duplicatas de rendimentos ────────────────────────────────

class TestAuditoriaDuplicatas(TestCase):

    def setUp(self):
        self.usuario = _usuario()
        self.dec = _declaracao(self.usuario)

    def test_detecta_duplicata_mesmo_cnpj_e_valor(self):
        _rendimento(self.dec, valor=60000, cnpj='11.222.333/0001-44')
        _rendimento(self.dec, valor=60000, cnpj='11.222.333/0001-44')
        rel = auditar(self.dec)
        titulos = [a.titulo for a in rel.alertas]
        self.assertTrue(
            any('duplicado' in t.lower() for t in titulos),
            msg='Deveria alertar sobre rendimento duplicado'
        )

    def test_nao_alerta_cnpjs_diferentes(self):
        _rendimento(self.dec, valor=60000, cnpj='11.222.333/0001-44')
        _rendimento(self.dec, valor=60000, cnpj='99.888.777/0001-11')
        rel = auditar(self.dec)
        titulos = [a.titulo for a in rel.alertas]
        self.assertFalse(any('duplicado' in t.lower() for t in titulos))

    def test_nao_alerta_tipos_diferentes(self):
        _rendimento(self.dec, tipo='salario', valor=60000, cnpj='11.222.333/0001-44')
        _rendimento(self.dec, tipo='aluguel', valor=60000, cnpj='11.222.333/0001-44')
        rel = auditar(self.dec)
        titulos = [a.titulo for a in rel.alertas]
        self.assertFalse(any('duplicado' in t.lower() for t in titulos))

    def test_tolerancia_1_porcento(self):
        # Valores dentro de 1% → duplicata
        _rendimento(self.dec, valor=60000, cnpj='11.222.333/0001-44')
        _rendimento(self.dec, valor=60500, cnpj='11.222.333/0001-44')  # 0,83% de diferença
        rel = auditar(self.dec)
        titulos = [a.titulo for a in rel.alertas]
        self.assertTrue(any('duplicado' in t.lower() for t in titulos))

    def test_sem_duplicata_valores_distintos(self):
        _rendimento(self.dec, valor=60000, cnpj='11.222.333/0001-44')
        _rendimento(self.dec, valor=40000, cnpj='11.222.333/0001-44')
        rel = auditar(self.dec)
        titulos = [a.titulo for a in rel.alertas]
        self.assertFalse(any('duplicado' in t.lower() for t in titulos))


# ─── 5. Auditoria — ganhos de capital ────────────────────────────────────────

class TestAuditoriaGanhosCapital(TestCase):

    def setUp(self):
        self.usuario = _usuario()
        self.dec = _declaracao(self.usuario)
        _rendimento(self.dec, valor=80000)

    def _ganho(self, custo, venda, isento=False, darf=False, tipo='Ações PETR4',
               data_alienacao=None):
        return GanhoCapital.objects.create(
            declaracao=self.dec,
            tipo_bem=tipo,
            data_aquisicao=datetime.date(2024, 1, 10),
            data_alienacao=data_alienacao or datetime.date(2024, 3, 15),
            custo_aquisicao=Decimal(str(custo)),
            valor_venda=Decimal(str(venda)),
            isento=isento,
            darf_recolhido=darf,
        )

    def test_darf_nao_recolhido_gera_erro(self):
        self._ganho(custo=10000, venda=30000, darf=False)
        rel = auditar(self.dec)
        erros = [a for a in rel.alertas if a.nivel == 'erro' and 'darf' in a.titulo.lower()]
        self.assertTrue(len(erros) > 0, 'Deveria gerar erro para DARF não recolhido')

    def test_darf_recolhido_sem_erro(self):
        self._ganho(custo=10000, venda=30000, darf=True)
        rel = auditar(self.dec)
        erros = [a for a in rel.alertas if a.nivel == 'erro' and 'darf' in a.titulo.lower()]
        self.assertEqual(len(erros), 0)

    def test_ganho_isento_sem_erro_darf(self):
        self._ganho(custo=10000, venda=15000, isento=True, darf=False)
        rel = auditar(self.dec)
        erros = [a for a in rel.alertas if a.nivel == 'erro' and 'darf' in a.titulo.lower()]
        self.assertEqual(len(erros), 0)

    def test_vendas_acima_20k_mes_gera_aviso(self):
        # Duas vendas de ações no mesmo mês totalizando > R$20k
        self._ganho(custo=5000, venda=15000, darf=True, data_alienacao=datetime.date(2024, 6, 10))
        self._ganho(custo=3000, venda=10000, darf=True, data_alienacao=datetime.date(2024, 6, 20))
        rel = auditar(self.dec)
        avisos = [a for a in rel.alertas if 'acima de r$ 20.000' in a.titulo.lower() or '20.000' in a.titulo]
        self.assertTrue(len(avisos) > 0, 'Deveria alertar sobre vendas acima do limite mensal')

    def test_prejuizo_gera_dica_compensacao(self):
        self._ganho(custo=50000, venda=30000, darf=False)
        rel = auditar(self.dec)
        dicas = [a for a in rel.alertas if a.nivel == 'dica' and 'prejuízo' in a.titulo.lower()]
        self.assertTrue(len(dicas) > 0, 'Deveria sugerir compensação de prejuízo')

    def test_isento_com_vendas_acima_limite_gera_erro(self):
        # Mês com vendas > 20k mas marcado como isento
        self._ganho(
            custo=5000, venda=25000, isento=True, darf=False,
            data_alienacao=datetime.date(2024, 7, 15),
        )
        rel = auditar(self.dec)
        erros = [a for a in rel.alertas if a.nivel == 'erro' and 'isenção' in a.titulo.lower()]
        self.assertTrue(len(erros) > 0, 'Deveria erro ao aplicar isenção indevida')
