"""
Auditoria profunda via Claude API.
Envia o relatório completo da declaração e solicita uma análise detalhada.
"""
import anthropic
from django.conf import settings

from assistente.prompts import serializar_declaracao
from .auditoria import RelatorioAuditoria


_PROMPT_AUDITORIA = """
Você é um auditor fiscal especialista em IRPF brasileiro.
Analise a declaração abaixo e forneça uma revisão completa e didática.

Sua análise deve cobrir:
1. **Pontos de risco** — o que pode gerar malha fina ou questionamento da Receita Federal
2. **Oportunidades perdidas** — deduções ou isenções que o contribuinte pode estar esquecendo
3. **Consistência** — se os valores fazem sentido entre si (renda x bens x IR retido)
4. **Recomendação de modelo** — confirme se simplificado ou completo é mais vantajoso e explique
5. **Próximos passos** — ações concretas que o contribuinte deve tomar antes de enviar

Seja objetivo, use linguagem simples (sem jargão contábil excessivo) e organize sua resposta
com os títulos acima. Se não houver riscos em alguma área, diga explicitamente "Nenhum risco identificado."

---
DECLARAÇÃO DO CONTRIBUINTE:
{dados_declaracao}

RESULTADO DA SIMULAÇÃO:
Modelo recomendado: {modelo_recomendado}
IR devido ({modelo_recomendado}): R$ {ir_devido}
IR retido na fonte: R$ {ir_retido}
{situacao}: R$ {valor_resultado}
"""


def auditar_com_ia(declaracao, relatorio: RelatorioAuditoria) -> str:
    """
    Envia a declaração para o Claude e retorna a análise em texto.
    Retorna string de erro se a API não estiver configurada.
    """
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == 'sk-ant-':
        return None  # Sem chave configurada — análise IA desabilitada silenciosamente

    dados = serializar_declaracao(declaracao)

    if relatorio.resultado:
        res = relatorio.resultado
        situacao = 'Restituição' if res['resultado'] >= 0 else 'Imposto a pagar'
        valor = abs(res['resultado'])
    else:
        situacao = 'Resultado'
        valor = 0
        res = {'modelo_usado': '—', 'ir_devido': 0, 'ir_retido': 0, 'resultado': 0}

    prompt = _PROMPT_AUDITORIA.format(
        dados_declaracao=dados,
        modelo_recomendado=res.get('modelo_usado', '—'),
        ir_devido=f"{res.get('ir_devido', 0):.2f}",
        ir_retido=f"{res.get('ir_retido', 0):.2f}",
        situacao=situacao,
        valor_resultado=f"{valor:.2f}",
    )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=2048,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return response.content[0].text
    except Exception as e:
        return f'Não foi possível gerar a análise IA: {str(e)}'
