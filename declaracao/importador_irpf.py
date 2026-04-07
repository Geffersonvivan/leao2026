"""
Extrator de dados de declarações IRPF anteriores (PDF completo do programa da Receita).
"""
import json
import re
import time
import logging
from decimal import Decimal, InvalidOperation

import anthropic
from django.conf import settings
from pypdf import PdfReader

log = logging.getLogger(__name__)


PROMPT_EXTRACAO_IRPF = """
Você receberá o texto extraído de uma declaração do Imposto de Renda Pessoa Física (IRPF)
gerada pelo programa oficial da Receita Federal do Brasil.

Sua tarefa: extrair os dados estruturados e retornar SOMENTE um JSON válido, sem nenhum texto
antes ou depois.

REGRAS CRÍTICAS:
1. Extraia SOMENTE o que está explicitamente no texto. NÃO invente nem complete dados ausentes.
2. Se um campo não estiver claro, use null.
3. Valores monetários: converta vírgula decimal para ponto (ex: 1.234,56 → 1234.56).
4. CNPJ/CPF: remova pontuação, retorne apenas os dígitos.
5. Datas: formato YYYY-MM-DD.
6. Se o PDF for apenas o recibo de entrega (sem os dados completos), retorne erro no campo "erro".

SCHEMA ESPERADO:
{
  "erro": null,
  "ano_base": 2023,
  "modelo": "completo",
  "rendimentos": [
    {
      "tipo": "salario",
      "fonte_pagadora_nome": "EMPRESA LTDA",
      "cnpj": "12345678000100",
      "valor_bruto": 72000.00,
      "ir_retido": 8400.00,
      "inss_retido": 3500.00
    }
  ],
  "dependentes": [
    {
      "nome": "FILHO DA SILVA",
      "cpf": "12345678901",
      "data_nascimento": "2010-03-15",
      "parentesco": "filho"
    }
  ],
  "deducoes": [
    {
      "tipo": "saude",
      "descricao": "PLANO DE SAÚDE EMPRESA",
      "valor": 4800.00,
      "cnpj_cpf": "12345678000199"
    }
  ],
  "bens": [
    {
      "codigo": "11",
      "discriminacao": "APARTAMENTO - RUA X, 123 - SÃO PAULO/SP",
      "valor_anterior": 300000.00,
      "valor_atual": 300000.00
    }
  ]
}

TIPOS DE RENDIMENTO ACEITOS:
- "salario" → Rendimentos Tributáveis de Pessoa Jurídica (salário, pró-labore)
- "aluguel" → Aluguéis
- "autonomo" → Trabalho Autônomo / RPA
- "aposentadoria" → Aposentadoria / Pensão INSS
- "pensao_recebida" → Pensão Alimentícia Recebida
- "rural" → Atividade Rural
- "exterior" → Rendimentos do Exterior
- "isento" → Rendimentos Isentos e Não Tributáveis
- "exclusivo_fonte" → Tributação Exclusiva na Fonte
- "outros_tributaveis" → Outros Tributáveis

TIPOS DE DEDUÇÃO ACEITOS:
- "saude" → Despesas Médicas / Plano de Saúde
- "educacao" → Educação
- "inss" → Previdência Social (INSS)
- "pgbl" → Previdência Privada (PGBL)
- "pensao_paga" → Pensão Alimentícia Paga
- "livro_caixa" → Livro-Caixa

PARENTESCO ACEITOS: conjuge, filho, pai_mae, avo, irmao, menor_guarda, incapaz

Retorne APENAS o JSON. Sem explicações, sem markdown, sem texto adicional.
"""


class ExtractionError(Exception):
    pass


def _extrair_texto_pdf(path: str) -> str:
    try:
        reader = PdfReader(path)
        paginas = []
        for page in reader.pages:
            texto = page.extract_text()
            if texto:
                paginas.append(texto)
        return "\n".join(paginas)
    except Exception as e:
        raise ExtractionError(f"Não foi possível ler o PDF: {e}")


def _limpar_valor(valor) -> Decimal:
    """Converte string ou number para Decimal seguro."""
    if valor is None:
        return Decimal("0")
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _validar_e_normalizar(dados: dict) -> dict:
    """Valida estrutura mínima e normaliza valores."""
    if dados.get("erro"):
        raise ExtractionError(dados["erro"])

    if not dados.get("ano_base"):
        raise ExtractionError("Ano-base não encontrado no PDF.")

    # Normaliza rendimentos
    rendimentos = []
    for r in dados.get("rendimentos") or []:
        if not r.get("fonte_pagadora_nome") or not r.get("valor_bruto"):
            continue
        rendimentos.append({
            "tipo": r.get("tipo") or "outros_tributaveis",
            "fonte_pagadora_nome": str(r["fonte_pagadora_nome"])[:200],
            "cnpj": re.sub(r"\D", "", str(r.get("cnpj") or ""))[:20],
            "valor_bruto": _limpar_valor(r["valor_bruto"]),
            "ir_retido": _limpar_valor(r.get("ir_retido")),
            "inss_retido": _limpar_valor(r.get("inss_retido")),
        })

    # Normaliza dependentes
    dependentes = []
    for d in dados.get("dependentes") or []:
        if not d.get("nome"):
            continue
        dependentes.append({
            "nome": str(d["nome"])[:200],
            "cpf": re.sub(r"\D", "", str(d.get("cpf") or ""))[:14],
            "data_nascimento": d.get("data_nascimento") or "2000-01-01",
            "parentesco": d.get("parentesco") or "filho",
        })

    # Normaliza deduções
    deducoes = []
    for ded in dados.get("deducoes") or []:
        if not ded.get("valor"):
            continue
        deducoes.append({
            "tipo": ded.get("tipo") or "saude",
            "descricao": str(ded.get("descricao") or "")[:300],
            "valor": _limpar_valor(ded["valor"]),
            "cnpj_cpf": re.sub(r"\D", "", str(ded.get("cnpj_cpf") or ""))[:20],
        })

    # Normaliza bens
    bens = []
    for b in dados.get("bens") or []:
        if not b.get("discriminacao"):
            continue
        bens.append({
            "codigo": str(b.get("codigo") or "99")[:10],
            "discriminacao": str(b["discriminacao"])[:500],
            "valor_anterior": _limpar_valor(b.get("valor_anterior")),
            "valor_atual": _limpar_valor(b.get("valor_atual")),
        })

    return {
        "ano_base": int(dados["ano_base"]),
        "modelo": dados.get("modelo") or "simplificado",
        "rendimentos": rendimentos,
        "dependentes": dependentes,
        "deducoes": deducoes,
        "bens": bens,
    }


def extrair_dados_irpf(arquivo_path: str) -> dict:
    """
    Recebe o caminho do PDF da declaração anterior e retorna
    um dicionário normalizado com todos os dados extraídos.
    Lança ExtractionError em caso de falha.
    """
    t0 = time.time()
    log.warning(f"[IRPF] ▶ Iniciando extração: {arquivo_path}")

    if not settings.ANTHROPIC_API_KEY:
        raise ExtractionError("Chave da API Anthropic não configurada.")

    t1 = time.time()
    texto = _extrair_texto_pdf(arquivo_path)
    log.warning(f"[IRPF] 📄 PDF lido em {time.time()-t1:.2f}s — {len(texto)} chars")

    if len(texto.strip()) < 100:
        raise ExtractionError(
            "O PDF não contém texto legível. Verifique se é a impressão completa "
            "da declaração (não apenas o recibo de entrega)."
        )

    texto_truncado = texto[:12000]
    log.warning(f"[IRPF] ✂ Texto truncado: {len(texto_truncado)} chars enviados à IA")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    t2 = time.time()
    log.warning(f"[IRPF] 🤖 Chamando Claude Haiku…")
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    PROMPT_EXTRACAO_IRPF
                    + "\n\n---\nTEXTO EXTRAÍDO DO PDF:\n---\n"
                    + texto_truncado
                ),
            }],
        )
        raw = response.content[0].text.strip()
        log.warning(f"[IRPF] ✅ Claude respondeu em {time.time()-t2:.2f}s — {len(raw)} chars")
    except Exception as e:
        raise ExtractionError(f"Erro ao contatar o assistente de IA: {e}")

    # Remove fences markdown se presentes
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        dados = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"Resposta da IA não é um JSON válido: {e}")

    resultado = _validar_e_normalizar(dados)
    log.warning(
        f"[IRPF] 🏁 Concluído em {time.time()-t0:.2f}s total | "
        f"{len(resultado.get('rendimentos', []))} rendimentos, "
        f"{len(resultado.get('dependentes', []))} dependentes, "
        f"{len(resultado.get('bens', []))} bens"
    )
    return resultado
