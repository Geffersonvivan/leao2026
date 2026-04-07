O que falta para "blindagem" real

  1. Testes automatizados do motor de cálculo — o mais crítico

  Não existe nenhum teste. O calculadora.py pode silenciosamente dar resultado errado se alguém mexer numa constante ou mudar uma regra. Um arquivo
   de testes com casos conhecidos (ex: "renda 60k, 1 dependente, saúde 5k → IR = X") é a única forma de garantir que os cálculos nunca regridam.

  1. Isenção mensal de R$ 20.000 em ações — gap fiscal crítico
  
  A função calcular_ganho_capital não considera a isenção mensal para ações. Se o usuário vendeu menos de R$ 20k num mês, o imposto é zero — isso  
  não está implementado. É um erro direto na apuração.

  1. Dedução de educação por beneficiário — gap de cálculo
  
  O limite de R$ 3.561,50 está sendo aplicado por entrada no banco, não por pessoa. Se o usuário lançou 3 recibos da mesma faculdade, cada um
  recebe o limite inteiro. O certo é agrupar por beneficiário.

  1. Detecção de rendimento duplicado — risco de import

  Nada impede importar o mesmo informe de rendimentos duas vezes. A auditoria deveria alertar quando há dois rendimentos com mesma fonte pagadora e
   valor muito próximo.

  1. Auditoria de ganho de capital — ausente
  
  O motor de auditoria não toca nos GanhoCapital. Deveria verificar: DARF pago? Day trade separado? Prejuízo compensado?

  ---
  Sobre RAG e segunda LLM

  RAG: não precisa. O domínio é fechado e conhecido — logica_IR.md como contexto estático é mais confiável e previsível que RAG para este caso.  

  Segunda LLM: não acrescenta. O gargalo não é inteligência, é regras determinísticas faltando.

  Motor math Python: já está bem feito com Decimal. O problema não é o motor em si, é os casos que ele não cobre ainda (isenção de ações, limite de
   educação por pessoa).

  ---
  Prioridade sugerida

  ┌─────┬──────────────────────────────────┬───────────────────────────────────────┐
  │  #  │              O que               │                Impacto                │
  ├─────┼──────────────────────────────────┼───────────────────────────────────────┤
  │ 1   │ Testes do calculadora.py         │ Blindagem permanente contra regressão │
  ├─────┼──────────────────────────────────┼───────────────────────────────────────┤
  │ 2   │ Isenção R$ 20k/mês em ações      │ Erro fiscal real                      │
  ├─────┼──────────────────────────────────┼───────────────────────────────────────┤
  │ 3   │ Limite educação por beneficiário │ Cálculo incorreto                     │
  ├─────┼──────────────────────────────────┼───────────────────────────────────────┤
  │ 4   │ Detecção de rendimento duplicado │ Erro comum de usuário                 │
  ├─────┼──────────────────────────────────┼───────────────────────────────────────┤
  │ 5   │ Auditoria de ganho de capital    │ Alertas úteis                         │
  └─────┴──────────────────────────────────┴───────────────────────────────────────┘

  Quer que eu implemente por essa ordem?
s