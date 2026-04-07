"""
Prompts para extração de dados fiscais de documentos.
"""

PROMPT_EXTRACAO = """
Você é um especialista em leitura de documentos fiscais brasileiros.
Analise o documento e extraia os dados no formato JSON especificado.

IMPORTANTE:
- Retorne APENAS o JSON, sem explicações ou texto adicional
- Use null para campos não encontrados
- Valores monetários devem ser números decimais (ex: 12345.67), sem R$ ou pontos de milhar
- Datas no formato YYYY-MM-DD
- Se o documento contiver múltiplos rendimentos ou deduções, liste todos em arrays

FORMATO ESPERADO — escolha o tipo correto:

Para INFORME DE RENDIMENTOS (banco, corretora, empregador):
{
  "tipo_documento": "informe_rendimentos",
  "fonte_pagadora_nome": "string",
  "fonte_pagadora_cnpj": "string",
  "ano_base": 2024,
  "rendimentos": [
    {
      "tipo": "salario|aluguel|autonomo|aposentadoria|outros_tributaveis|exclusivo_fonte|isento",
      "descricao": "string",
      "valor_bruto": 0.00,
      "ir_retido": 0.00,
      "inss_retido": 0.00
    }
  ]
}

Para RECIBO MÉDICO / PLANO DE SAÚDE:
{
  "tipo_documento": "recibo_medico",
  "prestador_nome": "string",
  "prestador_cnpj_cpf": "string",
  "paciente_nome": "string",
  "data": "YYYY-MM-DD",
  "descricao": "string",
  "valor": 0.00
}

Para COMPROVANTE DE EDUCAÇÃO (escola, faculdade, curso técnico):
{
  "tipo_documento": "boleto_escola",
  "instituicao_nome": "string",
  "instituicao_cnpj": "string",
  "aluno_nome": "string",
  "ano_base": 2024,
  "valor_total": 0.00,
  "descricao": "string"
}

Para VEÍCULO (CRLV, nota fiscal, DUT, documento do carro/moto):
{
  "tipo_documento": "outros",
  "subtipo": "veiculo",
  "codigo_rf": "21",
  "marca_modelo": "string (ex: Toyota Corolla)",
  "ano_fabricacao": 2020,
  "placa": "string",
  "renavam": "string",
  "valor_aquisicao": 0.00,
  "data_aquisicao": "YYYY-MM-DD",
  "discriminacao": "string resumida para a declaração (ex: Toyota Corolla 2020, placa ABC-1234)"
}

Para IMÓVEL (escritura, ITBI, matrícula, contrato de compra e venda):
{
  "tipo_documento": "outros",
  "subtipo": "imovel",
  "codigo_rf": "11",
  "endereco": "string completo",
  "area_m2": 0.0,
  "matricula": "string",
  "cartorio": "string",
  "valor_aquisicao": 0.00,
  "data_aquisicao": "YYYY-MM-DD",
  "discriminacao": "string resumida para a declaração (ex: Apto 101, Rua das Flores, 100 - São Paulo/SP)"
}

Para AÇÕES / FII / BDR (nota de corretagem, extrato de posição, informe de custódia):
{
  "tipo_documento": "outros",
  "subtipo": "acoes_fii",
  "codigo_rf": "31",
  "corretora_nome": "string",
  "corretora_cnpj": "string",
  "ativos": [
    {
      "ticker": "string (ex: PETR4, HGLG11)",
      "nome": "string",
      "quantidade": 0,
      "valor_total": 0.00
    }
  ],
  "discriminacao": "string (ex: Ações PETR4 — 100 cotas @ R$ 35,00)"
}

Para CRIPTOMOEDA (extrato de exchange, comprovante de compra):
{
  "tipo_documento": "outros",
  "subtipo": "cripto",
  "codigo_rf": "89",
  "exchange": "string (ex: Binance, Mercado Bitcoin)",
  "ativos": [
    {
      "nome": "string (ex: Bitcoin)",
      "simbolo": "string (ex: BTC)",
      "quantidade": 0.0,
      "valor_brl": 0.00
    }
  ],
  "discriminacao": "string (ex: 0.05 BTC na Binance)"
}

Para CONTA BANCÁRIA / POUPANÇA / APLICAÇÃO (extrato bancário, CDB, LCI, fundo):
{
  "tipo_documento": "outros",
  "subtipo": "conta_bancaria",
  "codigo_rf": "41",
  "banco_nome": "string",
  "banco_cnpj": "string",
  "agencia": "string",
  "conta": "string",
  "tipo_conta": "poupanca|renda_fixa|fundo|corrente",
  "saldo": 0.00,
  "discriminacao": "string (ex: Poupança Bradesco ag. 1234-5 cc. 67890-1)"
}

Para qualquer OUTRO documento não identificado acima:
{
  "tipo_documento": "outros",
  "subtipo": "generico",
  "codigo_rf": null,
  "descricao": "string descrevendo o documento",
  "dados_relevantes": {}
}
"""
