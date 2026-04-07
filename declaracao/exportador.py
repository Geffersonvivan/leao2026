"""
Exportação da declaração IRPF.

Formatos disponíveis:
  - PDF  → relatório completo estruturado pelas fichas do programa IRPF
  - JSON → dados brutos para portabilidade
"""
import io
import json
from decimal import Decimal
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .calculadora import recomendar_modelo, calcular_resultado_final

# ─── Cores ────────────────────────────────────────────────────────────────────
AZUL      = colors.HexColor('#1d4ed8')
AZUL_CLARO = colors.HexColor('#eff6ff')
CINZA     = colors.HexColor('#6b7280')
CINZA_BG  = colors.HexColor('#f9fafb')
PRETO     = colors.HexColor('#111827')
VERDE     = colors.HexColor('#16a34a')
VERMELHO  = colors.HexColor('#dc2626')
BRANCO    = colors.white


def _fmt(valor) -> str:
    if valor is None:
        return '—'
    try:
        return f'R$ {Decimal(str(valor)):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return str(valor)


def _styles():
    base = getSampleStyleSheet()
    estilos = {
        'titulo':     ParagraphStyle('titulo', parent=base['Title'],
                                     fontSize=18, textColor=AZUL, spaceAfter=4),
        'subtitulo':  ParagraphStyle('subtitulo', parent=base['Normal'],
                                     fontSize=10, textColor=CINZA, spaceAfter=12),
        'secao':      ParagraphStyle('secao', parent=base['Heading2'],
                                     fontSize=11, textColor=AZUL, spaceBefore=14, spaceAfter=6,
                                     borderPad=4),
        'label':      ParagraphStyle('label', parent=base['Normal'],
                                     fontSize=8, textColor=CINZA),
        'valor':      ParagraphStyle('valor', parent=base['Normal'],
                                     fontSize=10, textColor=PRETO),
        'rodape':     ParagraphStyle('rodape', parent=base['Normal'],
                                     fontSize=7, textColor=CINZA, alignment=TA_CENTER),
        'normal':     ParagraphStyle('normal', parent=base['Normal'],
                                     fontSize=9, textColor=PRETO),
        'destaque':   ParagraphStyle('destaque', parent=base['Normal'],
                                     fontSize=12, textColor=PRETO, fontName='Helvetica-Bold'),
    }
    return estilos


def _tabela_padrao(dados, col_widths=None):
    t = Table(dados, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('TEXTCOLOR',  (0, 0), (-1, 0), BRANCO),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BRANCO, CINZA_BG]),
        ('FONTSIZE',   (0, 1), (-1, -1), 8),
        ('TEXTCOLOR',  (0, 1), (-1, -1), PRETO),
        ('GRID',       (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


# ─── PDF ──────────────────────────────────────────────────────────────────────

def gerar_pdf(declaracao) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm,
        title=f'Declaração IRPF {declaracao.ano_base}',
        author='Calculadora IR',
    )

    s = _styles()
    elementos = []
    largura = doc.width

    # ── Capa ──
    elementos += [
        Paragraph('DECLARAÇÃO DE IMPOSTO DE RENDA', s['titulo']),
        Paragraph(f'Pessoa Física — Ano-Calendário {declaracao.ano_base} (IRPF {declaracao.ano_base + 1})', s['subtitulo']),
        HRFlowable(width='100%', thickness=1, color=AZUL),
        Spacer(1, 0.4*cm),
    ]

    # ── Identificação ──
    usuario = declaracao.usuario
    dados_id = [
        ['Contribuinte', usuario.get_full_name() or usuario.username],
        ['CPF',          usuario.cpf or '—'],
        ['E-mail',       usuario.email],
        ['Modelo',       declaracao.get_modelo_display() or 'Não definido'],
        ['Status',       declaracao.get_status_display()],
        ['Gerado em',    date.today().strftime('%d/%m/%Y')],
    ]
    t_id = Table(dados_id, colWidths=[4*cm, largura - 4*cm])
    t_id.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), CINZA),
        ('TEXTCOLOR', (1, 0), (1, -1), PRETO),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [BRANCO, CINZA_BG]),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
    ]))
    elementos += [t_id, Spacer(1, 0.5*cm)]

    # ── Resultado ──
    if declaracao.rendimentos.exists():
        simulacao = recomendar_modelo(declaracao)
        resultado = calcular_resultado_final(declaracao)

        elementos.append(Paragraph('RESULTADO DA DECLARAÇÃO', s['secao']))

        rec = simulacao[simulacao['recomendado']]
        cor_resultado = VERDE if resultado['resultado'] >= 0 else VERMELHO
        situacao_txt = 'RESTITUIÇÃO A RECEBER' if resultado['resultado'] >= 0 else 'IMPOSTO A PAGAR'

        dados_res = [
            ['', 'Simplificado', 'Completo'],
            ['Rendimentos tributáveis',
             _fmt(simulacao['simplificado']['rendimentos_tributaveis']),
             _fmt(simulacao['completo']['rendimentos_tributaveis'])],
            ['Deduções / Desconto',
             _fmt(simulacao['simplificado']['desconto_aplicado']),
             _fmt(simulacao['completo']['total_deducoes'])],
            ['Base de cálculo',
             _fmt(simulacao['simplificado']['base_calculo']),
             _fmt(simulacao['completo']['base_calculo'])],
            ['IR Devido',
             _fmt(simulacao['simplificado']['ir_devido']),
             _fmt(simulacao['completo']['ir_devido'])],
        ]
        t_res = _tabela_padrao(dados_res, col_widths=[largura*0.5, largura*0.25, largura*0.25])
        # Destaca coluna recomendada
        col_rec = 1 if simulacao['recomendado'] == 'simplificado' else 2
        t_res.setStyle(TableStyle([
            ('BACKGROUND', (col_rec, 1), (col_rec, -1), AZUL_CLARO),
            ('FONTNAME',   (col_rec, 0), (col_rec, -1), 'Helvetica-Bold'),
        ]))

        elementos += [
            t_res, Spacer(1, 0.3*cm),
            Table([[
                Paragraph(f'IR Retido na Fonte: {_fmt(resultado["ir_retido"])}', s['normal']),
                Paragraph(f'{situacao_txt}: {_fmt(abs(resultado["resultado"]))}', ParagraphStyle(
                    'sit', parent=s['destaque'], textColor=cor_resultado, alignment=TA_CENTER,
                )),
            ]], colWidths=[largura*0.5, largura*0.5]),
            Spacer(1, 0.5*cm),
        ]

    # ── Rendimentos ──
    rendimentos = list(declaracao.rendimentos.all())
    if rendimentos:
        elementos.append(Paragraph('FICHA: RENDIMENTOS RECEBIDOS DE PESSOA JURÍDICA / FÍSICA', s['secao']))
        dados = [['Tipo', 'Fonte Pagadora', 'CNPJ/CPF', 'Valor Bruto', 'IR Retido', 'INSS']]
        for r in rendimentos:
            dados.append([
                r.get_tipo_display(),
                r.fonte_pagadora_nome,
                r.fonte_pagadora_cnpj_cpf or '—',
                _fmt(r.valor_bruto),
                _fmt(r.ir_retido),
                _fmt(r.inss_retido),
            ])
        total_bruto = sum(r.valor_bruto for r in rendimentos)
        total_ir    = sum(r.ir_retido   for r in rendimentos)
        dados.append(['TOTAL', '', '', _fmt(total_bruto), _fmt(total_ir), ''])
        t = _tabela_padrao(dados, col_widths=[
            largura*0.18, largura*0.28, largura*0.15,
            largura*0.14, largura*0.13, largura*0.12,
        ])
        t.setStyle(TableStyle([
            ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), AZUL_CLARO),
        ]))
        elementos += [t, Spacer(1, 0.5*cm)]

    # ── Dependentes ──
    dependentes = list(declaracao.dependentes.all())
    if dependentes:
        elementos.append(Paragraph('FICHA: DEPENDENTES', s['secao']))
        dados = [['Nome', 'CPF', 'Nascimento', 'Parentesco']]
        for d in dependentes:
            dados.append([
                d.nome,
                d.cpf,
                d.data_nascimento.strftime('%d/%m/%Y') if d.data_nascimento else '—',
                d.get_parentesco_display(),
            ])
        elementos += [
            _tabela_padrao(dados, col_widths=[largura*0.38, largura*0.2, largura*0.18, largura*0.24]),
            Paragraph(f'Dedução total: {_fmt(len(dependentes) * 2275.08)} '
                      f'({len(dependentes)} × R$ 2.275,08)', s['label']),
            Spacer(1, 0.5*cm),
        ]

    # ── Deduções ──
    deducoes = list(declaracao.deducoes.all())
    if deducoes:
        elementos.append(Paragraph('FICHA: PAGAMENTOS EFETUADOS / DEDUÇÕES', s['secao']))
        dados = [['Tipo', 'Descrição', 'CPF/CNPJ Benef.', 'Valor']]
        for d in deducoes:
            dados.append([
                d.get_tipo_display(),
                d.descricao,
                d.cpf_cnpj_beneficiario or '—',
                _fmt(d.valor),
            ])
        total_ded = sum(d.valor for d in deducoes)
        dados.append(['TOTAL', '', '', _fmt(total_ded)])
        t = _tabela_padrao(dados, col_widths=[largura*0.2, largura*0.42, largura*0.2, largura*0.18])
        t.setStyle(TableStyle([
            ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), AZUL_CLARO),
        ]))
        elementos += [t, Spacer(1, 0.5*cm)]

    # ── Bens e Direitos ──
    bens = list(declaracao.bens.all())
    if bens:
        elementos.append(Paragraph('FICHA: BENS E DIREITOS', s['secao']))
        dados = [['Código', 'Discriminação', f'31/12/{declaracao.ano_base - 1}', f'31/12/{declaracao.ano_base}']]
        for b in bens:
            dados.append([
                b.codigo,
                b.discriminacao[:60] + ('...' if len(b.discriminacao) > 60 else ''),
                _fmt(b.valor_anterior),
                _fmt(b.valor_atual),
            ])
        elementos += [
            _tabela_padrao(dados, col_widths=[largura*0.1, largura*0.5, largura*0.2, largura*0.2]),
            Spacer(1, 0.5*cm),
        ]

    # ── Rodapé legal ──
    elementos += [
        HRFlowable(width='100%', thickness=0.5, color=CINZA),
        Spacer(1, 0.2*cm),
        Paragraph(
            'Documento gerado pela Calculadora IR. Verifique todos os dados antes de enviar à Receita Federal. '
            'Prazo de entrega: 30 de abril de ' + str(declaracao.ano_base + 1) + '. '
            'Este relatório não substitui o programa IRPF oficial.',
            s['rodape'],
        ),
    ]

    doc.build(elementos)
    return buffer.getvalue()


# ─── JSON ─────────────────────────────────────────────────────────────────────

def gerar_json(declaracao) -> str:
    def _d(v):
        return float(v) if isinstance(v, Decimal) else v

    resultado = {}
    if declaracao.rendimentos.exists():
        res = calcular_resultado_final(declaracao)
        resultado = {
            'modelo_usado':    res['modelo_usado'],
            'ir_devido':       _d(res['ir_devido']),
            'ir_retido':       _d(res['ir_retido']),
            'resultado':       _d(res['resultado']),
            'situacao':        res['situacao'],
        }

    dados = {
        'declaracao': {
            'ano_base': declaracao.ano_base,
            'modelo':   declaracao.modelo,
            'status':   declaracao.status,
        },
        'contribuinte': {
            'nome':  declaracao.usuario.get_full_name(),
            'cpf':   declaracao.usuario.cpf,
            'email': declaracao.usuario.email,
        },
        'resultado': resultado,
        'rendimentos': [
            {
                'tipo':                    r.tipo,
                'fonte_pagadora_nome':     r.fonte_pagadora_nome,
                'fonte_pagadora_cnpj_cpf': r.fonte_pagadora_cnpj_cpf,
                'valor_bruto':             _d(r.valor_bruto),
                'ir_retido':               _d(r.ir_retido),
                'inss_retido':             _d(r.inss_retido),
            }
            for r in declaracao.rendimentos.all()
        ],
        'dependentes': [
            {
                'nome':            d.nome,
                'cpf':             d.cpf,
                'data_nascimento': d.data_nascimento.isoformat() if d.data_nascimento else None,
                'parentesco':      d.parentesco,
            }
            for d in declaracao.dependentes.all()
        ],
        'deducoes': [
            {
                'tipo':                  d.tipo,
                'descricao':             d.descricao,
                'valor':                 _d(d.valor),
                'cpf_cnpj_beneficiario': d.cpf_cnpj_beneficiario,
            }
            for d in declaracao.deducoes.all()
        ],
        'bens_direitos': [
            {
                'codigo':         b.codigo,
                'discriminacao':  b.discriminacao,
                'valor_anterior': _d(b.valor_anterior),
                'valor_atual':    _d(b.valor_atual),
            }
            for b in declaracao.bens.all()
        ],
    }
    return json.dumps(dados, ensure_ascii=False, indent=2)
