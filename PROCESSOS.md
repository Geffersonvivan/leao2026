# PROCESSOS — Lógica de Cálculo do IRPF

Documento de referência sobre como o motor de cálculo (`declaracao/calculadora.py`) funciona internamente.

---

## Visão geral do fluxo

```
Rendimentos → [filtro: tributáveis]
                    ↓
            Deduções legais
                    ↓
             Base de Cálculo
                    ↓
         Tabela Progressiva IR
                    ↓
              IR Devido
                    ↓
         IR Devido − IR Retido
                    ↓
      Restituição ou Imposto a Pagar
```

---

## 1. Arredondamento

Todo valor monetário é arredondado com `ROUND_HALF_UP` para 2 casas decimais usando `Decimal` do Python. **Nunca se usa `float`** para evitar erros de ponto flutuante em cálculos fiscais.

```python
# Ex: 4432.825 → 4432.83
valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
```

---

## 2. Tabela progressiva do IRPF 2024

Fonte: IN RFB nº 2.255/2025

| Base de Cálculo Anual (R$) | Alíquota | Parcela a Deduzir (R$) |
|---|---|---|
| Até 26.963,20 | 0% | — |
| De 26.963,21 até 33.919,80 | 7,5% | 2.022,24 |
| De 33.919,81 até 45.012,60 | 15% | 4.566,23 |
| De 45.012,61 até 55.976,16 | 22,5% | 7.942,17 |
| Acima de 55.976,16 | 27,5% | 10.740,98 |

**Fórmula aplicada:**

```
IR = Base de Cálculo × Alíquota − Parcela a Deduzir
```

**Exemplo:** Base = R$ 60.000
→ 60.000 × 27,5% − 10.740,98 = 16.500 − 10.740,98 = **R$ 5.759,02**

**Exemplo:** Base = R$ 40.000
→ 40.000 × 15% − 4.566,23 = 6.000 − 4.566,23 = **R$ 1.433,77**

---

## 3. Rendimentos tributáveis

São somados todos os rendimentos da declaração **exceto** os do tipo:
- `isento` — rendimentos isentos e não tributáveis
- `exclusivo_fonte` — tributados exclusivamente na fonte (ex: JCP, prêmios de loteria)

```
Renda Tributável = Σ valor_bruto (exceto isento e exclusivo_fonte)
```

Os tipos que entram na base:

| Tipo | Descrição |
|---|---|
| `salario` | Salário / Pró-labore |
| `aluguel` | Aluguéis recebidos |
| `autonomo` | Trabalho autônomo / RPA |
| `pensao_recebida` | Pensão alimentícia recebida |
| `aposentadoria` | Aposentadoria / Pensão INSS |
| `rural` | Atividade rural |
| `exterior` | Rendimentos do exterior |
| `outros_tributaveis` | Outros rendimentos tributáveis |

---

## 4. Modelo Completo

Usa todas as deduções legais permitidas pela legislação.

### 4.1 Deduções por dependente

```
Dedução = R$ 2.275,08 × número de dependentes
```

Cada dependente elegível gera R$ 2.275,08 de dedução anual, independente de gastos.

### 4.2 Deduções de saúde

```
Dedução = Σ valores de saúde declarados
```

**Sem limite de valor.** Abrange consultas médicas, dentistas, planos de saúde, exames, internações e procedimentos cirúrgicos. O prestador deve ter CPF/CNPJ informado para evitar malha fina.

### 4.3 Deduções de educação

```
Dedução por pessoa = min(Σ gastos da pessoa, R$ 3.561,50)
Dedução total = Σ deduções por beneficiário
```

**Limite de R$ 3.561,50 por beneficiário (CPF).** O sistema agrupa todos os lançamentos pelo CPF do beneficiário antes de aplicar o limite, evitando que múltiplos lançamentos da mesma pessoa ultrapassem o teto individualmente.

**Exemplo:**
- Pessoa A (CPF 111): R$ 3.000 + R$ 2.000 = R$ 5.000 → limitado a R$ 3.561,50
- Pessoa B (CPF 222): R$ 2.000 → R$ 2.000 (abaixo do limite)
- **Total deduzido: R$ 5.561,50**

### 4.4 INSS

```
Dedução = valor total do INSS retido (sem limite)
```

Previdência Social (contribuição do empregado). Valor integral dedutível.

### 4.5 PGBL

```
Dedução = min(valor PGBL, 12% da renda tributável)
```

Previdência privada modalidade PGBL. Limitado a 12% da renda bruta tributável anual.

### 4.6 Pensão alimentícia paga

```
Dedução = valor total pago (sem limite)
```

Apenas pensão determinada por decisão judicial ou acordo homologado em juízo é dedutível.

### 4.7 Livro-caixa

```
Dedução = despesas comprovadas do exercício da atividade
```

Exclusivo para profissionais autônomos com rendimentos de trabalho sem vínculo empregatício.

### 4.8 Fórmula final — Modelo Completo

```
Base de Cálculo = max(Renda Tributável − Total de Deduções, 0)
IR Devido = Tabela Progressiva(Base de Cálculo)
```

---

## 5. Modelo Simplificado

Substitui todas as deduções por um desconto fixo de 20% sobre a renda tributável, com teto.

```
Desconto = min(Renda Tributável × 20%, R$ 16.754,34)
Base de Cálculo = max(Renda Tributável − Desconto, 0)
IR Devido = Tabela Progressiva(Base de Cálculo)
```

**Quando usar:** Quando o total de deduções legais for inferior a 20% da renda (ou ao teto de R$ 16.754,34). O sistema calcula os dois modelos e recomenda automaticamente o mais vantajoso.

---

## 6. Recomendação de modelo

```
se IR_Completo ≤ IR_Simplificado:
    recomendado = "completo"
    economia = IR_Simplificado − IR_Completo
senão:
    recomendado = "simplificado"
    economia = IR_Completo − IR_Simplificado
```

Ambos os modelos são sempre calculados e comparados. O sistema retorna o recomendado e o valor de economia potencial.

---

## 7. Resultado final

```
IR Retido = Σ ir_retido de todos os rendimentos

Resultado = IR Retido − IR Devido

se Resultado ≥ 0 → situação = "restituicao"  (Receita devolve)
se Resultado < 0 → situação = "imposto_a_pagar"  (contribuinte paga)
```

**Exemplo:**
- IR devido: R$ 4.000
- IR retido na fonte: R$ 5.500
- Resultado: +R$ 1.500 → **restituição de R$ 1.500**

---

## 8. Ganho de Capital — Imóveis e outros bens

Usado para alienação de imóveis, participações societárias e outros bens não enquadrados como ações.

Fonte: Lei nº 13.259/2016 (alíquotas progressivas)

```
Ganho = Valor de Venda − Custo de Aquisição

se Ganho ≤ 0: IR = 0 (prejuízo não gera imposto)
```

**Tabela progressiva de ganho de capital:**

| Faixa do Ganho (R$) | Alíquota |
|---|---|
| Até 5.000.000 | 15% |
| De 5.000.001 até 10.000.000 | 17,5% |
| De 10.000.001 até 30.000.000 | 20% |
| Acima de 30.000.000 | 22,5% |

**Cálculo por faixas (progressivo):**

```
IR = (primeiros R$ 5M × 15%)
   + (próximos R$ 5M × 17,5%)
   + (próximos R$ 20M × 20%)
   + (excedente × 22,5%)
```

**Exemplo:** Ganho de R$ 6.000.000
→ R$ 5.000.000 × 15% = R$ 750.000
→ R$ 1.000.000 × 17,5% = R$ 175.000
→ **IR total = R$ 925.000**

---

## 9. Ganho de Capital — Ações (Bolsa de Valores)

Regras específicas para operações com ações, ETFs e FIIs em bolsa.

Fonte: IN RFB nº 1.585/2015 + Lei nº 11.033/2004

### 9.1 Operação normal (swing trade)

```
se Total de Vendas no Mês ≤ R$ 20.000:
    IR = 0  (isento)

se Total de Vendas no Mês > R$ 20.000:
    Ganho Líquido = Total de Vendas − Custo Total
    se Ganho Líquido ≤ 0:
        IR = 0  (prejuízo)
    senão:
        IR = Ganho Líquido × 15%
```

**Ponto crítico:** A isenção é baseada no **total de vendas do mês** (não no lucro). Se em um mês o total de alienações ultrapassar R$ 20.000, toda a operação fica sujeita ao imposto — mesmo que o lucro seja pequeno.

**Exemplos:**

| Vendas/mês | Custo | Lucro | IR |
|---|---|---|---|
| R$ 15.000 | R$ 10.000 | R$ 5.000 | R$ 0 (isento) |
| R$ 20.000 | R$ 15.000 | R$ 5.000 | R$ 0 (isento, no limite exato) |
| R$ 25.000 | R$ 10.000 | R$ 15.000 | R$ 2.250 (15%) |
| R$ 25.000 | R$ 26.000 | −R$ 1.000 | R$ 0 (prejuízo) |

### 9.2 Day trade

```
Ganho Líquido = Vendas − Custos
se Ganho Líquido ≤ 0: IR = 0
senão: IR = Ganho Líquido × 20%
```

- **Sem isenção mensal** — mesmo vendas abaixo de R$ 20.000 são tributadas
- Alíquota sempre 20%, independente do valor
- DARF código **6015** para ambas as modalidades

### 9.3 Compensação de prejuízos

Prejuízos em ações podem ser compensados com lucros em meses seguintes **dentro da mesma categoria** (operações normais compensam operações normais; day trade compensa day trade). O sistema alerta quando há prejuízos registrados para que o usuário acompanhe a compensação.

---

## 10. Constantes utilizadas (IRPF 2025 / ano-base 2024)

| Constante | Valor | Descrição |
|---|---|---|
| `DEDUCAO_DEPENDENTE_ANUAL` | R$ 2.275,08 | Dedução por dependente |
| `LIMITE_DEDUCAO_EDUCACAO` | R$ 3.561,50 | Teto por beneficiário (educação) |
| `DESCONTO_SIMPLIFICADO_PERC` | 20% | Percentual do desconto simplificado |
| `LIMITE_DESCONTO_SIMPLIFICADO` | R$ 16.754,34 | Teto do desconto simplificado |
| `ISENCAO_MENSAL_ACOES` | R$ 20.000,00 | Limite mensal de vendas de ações para isenção |
| `ALIQUOTA_ACOES` | 15% | Alíquota de ações (operação normal) |
| `ALIQUOTA_DAY_TRADE` | 20% | Alíquota de day trade |

---

## 11. Funções públicas do módulo

| Função | Entrada | Saída | Uso |
|---|---|---|---|
| `calcular_ir_tabela(base)` | `Decimal` | `Decimal` | Aplica a tabela progressiva a uma base |
| `calcular_modelo_completo(declaracao)` | objeto `Declaracao` | `dict` | IR com deduções legais |
| `calcular_modelo_simplificado(declaracao)` | objeto `Declaracao` | `dict` | IR com desconto fixo 20% |
| `recomendar_modelo(declaracao)` | objeto `Declaracao` | `dict` | Compara os dois modelos e recomenda |
| `calcular_ir_retido_total(declaracao)` | objeto `Declaracao` | `Decimal` | Soma do IR retido na fonte |
| `calcular_resultado_final(declaracao, modelo)` | objeto `Declaracao`, `str` opcional | `dict` | Restituição ou imposto a pagar |
| `calcular_ganho_capital(custo, venda)` | `Decimal`, `Decimal` | `dict` | Ganho de capital progressivo (imóveis etc.) |
| `calcular_ganho_capital_acoes(vendas, custo, day_trade)` | `Decimal`, `Decimal`, `bool` | `dict` | Ganho de capital em ações com isenção mensal |

---

## 12. Onde os cálculos são acionados

| Onde | Quando |
|---|---|
| `declaracao/auditoria.py` → `auditar()` | Passo 6 (revisão) e tela de auditoria |
| `declaracao/wizard_views.py` → passo 6 | Ao exibir a comparação de modelos |
| `declaracao/exportador.py` | Ao gerar o PDF/JSON da declaração |
| `declaracao/tests.py` | Testes automatizados (40 casos) |
