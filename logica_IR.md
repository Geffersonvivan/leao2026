# Lógica do Imposto de Renda — Regras Oficiais IRPF

> **Base legal:** Lei nº 7.713/1988, Decreto nº 9.580/2018 (RIR), Instrução Normativa RFB nº 2.255/2025
> **Vigência:** Declaração IRPF 2025 (Ano-calendário 2024)
> **Fonte oficial:** [Receita Federal do Brasil](https://www.gov.br/receitafederal)

---

## 1. OBRIGATORIEDADE DE DECLARAR

Está obrigado a declarar o IRPF 2025 o contribuinte residente no Brasil que, em 2024:

| Critério | Limite |
|----------|--------|
| Rendimentos tributáveis (salário, aluguel, etc.) | Acima de **R$ 33.888,00** |
| Rendimentos isentos, não tributáveis ou tributados exclusivamente na fonte | Acima de **R$ 200.000,00** |
| Ganho de capital na alienação de bens ou direitos | Qualquer valor |
| Operações em bolsa de valores (ações, FIIs, etc.) | Qualquer valor |
| Receita bruta de atividade rural | Acima de **R$ 169.440,00** |
| Posse ou propriedade de bens e direitos (em 31/12/2024) | Acima de **R$ 800.000,00** |
| Passou à condição de residente no Brasil em qualquer mês | Obrigatório |
| Optou pela isenção do IR sobre ganho de capital na venda de imóvel + compra de outro imóvel em 180 dias | Obrigatório |

> **Regra:** Qualquer um dos critérios acima já obriga a declaração.

---

## 2. TABELA PROGRESSIVA ANUAL — IRPF 2024

Aplicada sobre a **base de cálculo anual** (rendimentos tributáveis − deduções permitidas):

| Base de Cálculo (R$) | Alíquota | Parcela a Deduzir (R$) |
|----------------------|----------|------------------------|
| Até 26.963,20 | **Isento** | — |
| De 26.963,21 até 33.919,80 | **7,5%** | 2.022,24 |
| De 33.919,81 até 45.012,60 | **15,0%** | 4.566,23 |
| De 45.012,61 até 55.976,16 | **22,5%** | 7.942,17 |
| Acima de 55.976,16 | **27,5%** | 10.740,98 |

### Tabela Progressiva Mensal — IRPF 2024 (retenção na fonte)

| Base de Cálculo Mensal (R$) | Alíquota | Parcela a Deduzir (R$) |
|-----------------------------|----------|------------------------|
| Até 2.259,20 | Isento | — |
| De 2.259,21 até 2.826,65 | 7,5% | 169,44 |
| De 2.826,66 até 3.751,05 | 15,0% | 381,44 |
| De 3.751,06 até 4.664,68 | 22,5% | 662,77 |
| Acima de 4.664,68 | 27,5% | 896,00 |

**Fórmula:**
```
IR Devido = (Base de Cálculo × Alíquota) − Parcela a Deduzir
```

---

## 3. MODELOS DE DECLARAÇÃO

### 3.1 Declaração Simplificada
- Substitui todas as deduções legais por um **desconto padrão de 20%** sobre os rendimentos tributáveis.
- Limite máximo do desconto: **R$ 16.754,34**
- Recomendado para quem tem poucas deduções.

### 3.2 Declaração Completa (Deduções Legais)
- Permite deduzir todas as despesas previstas em lei.
- Recomendado para quem tem dependentes, gastos médicos elevados, previdência privada, etc.

> **Regra de ouro:** O sistema deve **calcular os dois modelos automaticamente** e indicar qual resulta em menor imposto ou maior restituição.

---

## 4. DEDUÇÕES PERMITIDAS (Modelo Completo)

### 4.1 Dependentes
- Dedução: **R$ 2.275,08 por dependente/ano** (R$ 189,59/mês)
- Quem pode ser dependente:
  - Cônjuge ou companheiro(a) com quem viva há mais de 5 anos, ou com filho(a) em comum
  - Filho(a) ou enteado(a) até 21 anos, ou até 24 anos se estudante universitário/técnico
  - Filho(a) ou enteado(a) de qualquer idade se incapacitado física ou mentalmente
  - Irmão(ã), neto(a) ou bisneto(a) sem arrimo dos pais, até 21 anos (ou 24, se universitário) — desde que o declarante detenha a guarda judicial
  - Pais, avós e bisavós que, em 2024, tenham recebido rendimentos até R$ 26.963,20
  - Menor pobre até 21 anos que o declarante crie e eduque e do qual detenha a guarda judicial
  - Pessoa absolutamente incapaz da qual o declarante seja tutor ou curador

### 4.2 Educação
- Limite: **R$ 3.561,50 por pessoa** (declarante + dependentes)
- Despesas dedutíveis:
  - Educação infantil (creche e pré-escola)
  - Ensino fundamental, médio e superior
  - Educação profissional (técnico e tecnólogo)
  - Pós-graduação (mestrado, doutorado, especialização)
- **Não dedutíveis:** cursos de idiomas, informática, esportes, artes, transporte escolar, material escolar, uniforme.

### 4.3 Despesas Médicas
- **Sem limite de valor**
- Despesas dedutíveis:
  - Médicos (qualquer especialidade), dentistas, psicólogos, fisioterapeutas, fonoaudiólogos, terapeutas ocupacionais
  - Hospitais, clínicas, laboratórios, serviços radiológicos
  - Plano de saúde (titular e dependentes)
  - Aparelhos e próteses ortopédicas e dentárias (com receita)
  - Despesas com internação em estabelecimento geriátrico
- **Não dedutíveis:** medicamentos (exceto se na conta hospitalar), óculos, academias, enfermeiro particular (exceto com nota fiscal do hospital).
- **Exigência:** comprovante com CPF/CNPJ do prestador, nome do paciente e valor.

### 4.4 Previdência Social (INSS)
- Contribuições pagas à Previdência Social (INSS) são integralmente dedutíveis, sem limite.

### 4.5 Previdência Complementar (PGBL)
- Dedutível até **12% da renda bruta tributável anual**
- Aplica-se a: PGBL, Funpresp, entidades de previdência fechada
- **VGBL não é dedutível** na declaração completa (tributação apenas no resgate)

### 4.6 Pensão Alimentícia
- Valores pagos por determinação judicial ou acordo homologado judicialmente são **integralmente dedutíveis** (sem limite)
- Acordos extrajudiciais **não são dedutíveis**

### 4.7 Livro-Caixa (Autônomos)
- Profissionais autônomos podem deduzir despesas da atividade registradas em livro-caixa:
  - Remuneração de terceiros com vínculo empregatício
  - Emolumentos pagos a terceiros
  - Despesas de custeio necessárias à percepção da receita (aluguel do consultório, materiais, etc.)

---

## 5. RENDIMENTOS TRIBUTÁVEIS

Devem ser informados e integram a base de cálculo:

- Salários, vencimentos, proventos, honorários
- Aluguéis recebidos de pessoa física
- Pensão alimentícia recebida
- Atividade rural (receitas − despesas)
- Rendimentos de pessoa jurídica do exterior
- Prêmios em dinheiro (loteria, concursos)
- Rendimentos de trabalho sem vínculo empregatício (autônomos/MEI com serviços)
- Participação nos lucros e resultados (PLR) — **tributação exclusiva na fonte**, mas deve ser informado
- 13º salário — **tributação exclusiva na fonte**, deve ser informado separadamente

---

## 6. RENDIMENTOS ISENTOS E NÃO TRIBUTÁVEIS

Devem ser informados na declaração, mas **não integram a base de cálculo**:

| Rendimento | Observação |
|------------|------------|
| Parcela isenta de aposentadoria/pensão — 65 anos ou mais | Até R$ 26.963,20/ano (R$ 2.246,93/mês) |
| FGTS recebido | Sempre isento |
| Indenização por rescisão de contrato de trabalho | Incluindo aviso prévio indenizado |
| Seguro-desemprego | Sempre isento |
| Bolsas de estudo (para pesquisa/estudo) | Sem contraprestação de serviço |
| Lucros e dividendos recebidos | Distribuição de empresas brasileiras |
| Rendimentos de caderneta de poupança | Sempre isento |
| Rendimento de LCI, LCA, CRI, CRA | Sempre isento para PF |
| Herança e doação (recebidas) | Isentas de IR (sujeitas ao ITCMD estadual) |
| Indenização por acidente ou doença grave | Isenta |
| Ganho de capital na venda de imóvel residencial | Se o valor for reinvestido em outro imóvel residencial em até 180 dias |
| Ganho de capital na venda de único imóvel | Até R$ 440.000,00 (se não alienou outro imóvel nos últimos 5 anos) |
| Venda de bens de pequeno valor | Até R$ 35.000,00 por mês (cada alienação) |

---

## 7. RENDIMENTOS TRIBUTADOS EXCLUSIVAMENTE NA FONTE

Informados na declaração, mas o imposto já foi retido definitivamente:

- 13º salário
- Participação nos lucros e resultados (PLR)
- Juros sobre capital próprio
- Rendimentos de aplicações financeiras (fundos, CDB, Tesouro Direto)
- Prêmios de loterias e concursos
- Rendimentos de não residentes

---

## 8. GANHO DE CAPITAL

### 8.1 Alíquotas (Lei nº 13.259/2016)

| Ganho de Capital (R$) | Alíquota |
|-----------------------|----------|
| Até 5.000.000,00 | **15%** |
| De 5.000.000,01 até 10.000.000,00 | **17,5%** |
| De 10.000.000,01 até 30.000.000,00 | **20%** |
| Acima de 30.000.000,00 | **22,5%** |

### 8.2 Cálculo
```
Ganho de Capital = Valor de Venda − Custo de Aquisição
IR = Ganho de Capital × Alíquota aplicável
```

### 8.3 Prazo de Recolhimento
- O DARF deve ser pago até o **último dia útil do mês seguinte** à venda.
- Código DARF: **4600** (pessoa física)

### 8.4 Isenções de Ganho de Capital
- Venda de bens de pequeno valor: até **R$ 35.000,00/mês** por tipo de bem
- Venda do único imóvel residencial: até **R$ 440.000,00** (sem alienação nos últimos 5 anos)
- Reinvestimento em imóvel residencial: venda + compra em **180 dias**

---

## 9. OPERAÇÕES EM BOLSA DE VALORES

### 9.1 Ações (Mercado à Vista)
- **Isenção:** vendas mensais até **R$ 20.000,00** (soma de todas as ações no mês)
- **Acima de R$ 20.000,00/mês:** alíquota de **15%** sobre o lucro líquido
- **Day trade:** alíquota de **20%** (sem isenção de R$ 20.000,00)
- Prejuízos podem ser compensados com lucros futuros (mesmo tipo de operação)
- Recolhimento: DARF até o **último dia útil do mês seguinte** — código **6015** (normal) ou **6015** (day trade)

### 9.2 Fundos Imobiliários (FII)
- Rendimentos distribuídos: **isentos** para PF (desde que o FII tenha mais de 50 cotistas e seja negociado em bolsa)
- Ganho de capital na venda de cotas: **20%** (sem isenção mensal)

### 9.3 BDRs, ETFs e Fundos de Investimento
- ETFs de renda variável: **15%** (operações normais), **20%** (day trade)
- Fundos de renda fixa: tabela regressiva (22,5% a 15%)
- Fundos de curto prazo: 22,5% (até 180 dias), 20% (acima de 180 dias)

---

## 10. ATIVIDADE RURAL

- Receita bruta tributável = Receitas − Despesas comprovadas
- Alíquota: tabela progressiva normal
- Prejuízo rural pode ser compensado com receita rural dos anos seguintes
- Limite de compensação de prejuízo rural com outras rendas: **não permitido**
- Receita bruta acima de **R$ 169.440,00** obriga a declaração

---

## 11. BENS E DIREITOS

Devem ser declarados os bens e direitos possuídos em **31/12/2024** (e comparados com 31/12/2023):

- Imóveis (residencial, comercial, rural, terreno)
- Veículos, embarcações, aeronaves
- Contas bancárias, poupança, aplicações financeiras
- Participações societárias (cotas/ações de empresas)
- Criptoativos (obrigatório declarar)
- Joias, obras de arte, antiguidades (acima de R$ 5.000,00)
- Direitos autorais, patentes

> **Critério de avaliação:** custo de aquisição (não valor de mercado)

### Criptoativos
- Declarar pelo **custo de aquisição** em "Bens e Direitos" — código **89**
- Ganhos na venda: sujeitos ao ganho de capital (mesmas alíquotas)
- Isenção para vendas abaixo de **R$ 35.000,00/mês**
- Obrigação de reporte na IN RFB nº 1.888/2019 (mensalmente, para exchanges)

---

## 12. DÍVIDAS E ÔNUS REAIS

Informar saldos devidos em **31/12/2024** (e 31/12/2023):

- Financiamentos imobiliários (SFH, SFI)
- Financiamentos de veículos
- Empréstimos bancários (CDC, crédito pessoal)
- Empréstimos com pessoa física (acima de R$ 5.000,00)

> **Não informar:** dívidas já quitadas antes de 31/12/2024

---

## 13. CARNÊ-LEÃO

Obrigatório para rendimentos recebidos de **pessoa física** ou do **exterior** sem retenção na fonte:

- Aluguéis recebidos de PF
- Trabalho prestado a pessoa física (autônomos)
- Pensão alimentícia recebida de PF
- Rendimentos do exterior

**Tabela:** mesma tabela progressiva mensal
**Prazo de recolhimento:** último dia útil do mês seguinte ao recebimento
**Código DARF:** 0190

---

## 14. PRAZO, MULTAS E PENALIDADES

### 14.1 Prazo de Entrega
- **Data limite:** 30 de abril de 2025
- Entrega via: Programa IRPF, app Meu Imposto de Renda, portal e-CAC

### 14.2 Multa por Atraso
```
Multa = 1% ao mês (ou fração) sobre o IR devido
Mínimo: R$ 165,74
Máximo: 20% do IR devido
```

### 14.3 Omissão / Declaração Incorreta
- Multa de **75%** do imposto devido (dolo, fraude ou simulação: **150%**)
- Juros SELIC a partir do vencimento

### 14.4 Malha Fina — Inconsistências Comuns
- Despesas médicas sem comprovação ou com CPF inválido
- Rendimentos informados pela fonte pagadora diferentes dos declarados
- Deduções com dependente em duas declarações distintas
- Rendimentos de aluguéis não declarados
- Ganho de capital não recolhido
- Doações acima do limite (10% do IR devido)

---

## 15. DOAÇÕES INCENTIVADAS (Deduções do IR Devido)

Doações a fundos e entidades aprovadas permitem dedução diretamente do **imposto devido** (não da base de cálculo):

| Fundo / Programa | Limite de Dedução |
|-----------------|-------------------|
| Fundos da Criança e do Adolescente (ECA) | 3% do IR devido |
| Fundos do Idoso | 3% do IR devido |
| PRONON / PRONAS | 1% cada |
| Fundos Municipais/Estaduais/Nacional da Criança | somados com ECA: max 3% |
| **Total geral de doações incentivadas** | **Máximo 6% do IR devido** |

---

## 16. RESTITUIÇÃO

- A restituição ocorre quando o IR retido na fonte + DARF pagos > IR devido na declaração
- Prioridade de restituição: idosos (60+), portadores de doença grave, professores, contribuintes com maior imposto retido
- Lotes mensais: de junho a dezembro do ano de entrega
- Correção: taxa SELIC acumulada da data prevista de entrega até o pagamento

---

## 17. REGRAS ESPECIAIS

### 17.1 Declaração Final de Espólio
- Apresentada pelo inventariante após o falecimento do titular
- Inclui rendimentos do período, bens e direitos do falecido

### 17.2 Saída Definitiva do País
- Declaração de saída definitiva do Brasil
- Imposto pago sobre rendimentos até a data de saída

### 17.3 Menor de Idade
- Se o menor tem renda própria que obriga a declaração, deve declarar em separado (responsável legal assina)
- Pode constar como dependente e ter renda declarada na ficha de dependentes

---

## 18. REFERÊNCIAS LEGAIS

| Norma | Assunto |
|-------|---------|
| Lei nº 7.713/1988 | Imposto de Renda Pessoa Física — base |
| Decreto nº 9.580/2018 | Regulamento do Imposto de Renda (RIR/2018) |
| Lei nº 9.250/1995 | Deduções, dependentes, educação, saúde |
| Lei nº 9.532/1997 | Ganho de capital, isenções |
| Lei nº 13.259/2016 | Alíquotas progressivas de ganho de capital |
| IN RFB nº 2.255/2025 | Instruções para IRPF 2025 (ano-base 2024) |
| IN RFB nº 1.888/2019 | Obrigações com criptoativos |
| Lei nº 11.482/2007 | Tabela progressiva IRPF — valores atualizados |

---

> **Aviso:** Este documento reflete as regras do IRPF 2025 (ano-calendário 2024). As regras devem ser revisadas anualmente conforme as instruções normativas publicadas pela Receita Federal do Brasil. Em caso de dúvida, consulte sempre a legislação oficial em [gov.br/receitafederal](https://www.gov.br/receitafederal).
