import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST

import anthropic

from declaracao.models import Declaracao
from .models import Conversa, Mensagem
from .prompts import montar_system_prompt, serializar_declaracao


@login_required
def chat(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)
    conversa, _ = Conversa.objects.get_or_create(declaracao=declaracao)
    mensagens = conversa.mensagens.order_by('criada_em')
    return render(request, 'assistente/chat.html', {
        'declaracao': declaracao,
        'conversa': conversa,
        'mensagens': mensagens,
    })


@login_required
@require_POST
def mensagem(request, pk):
    declaracao = get_object_or_404(Declaracao, pk=pk, usuario=request.user)

    try:
        body = json.loads(request.body)
        texto_usuario = body.get('mensagem', '').strip()
        passo_atual = body.get('passo', '').strip()
        analise_resumo = body.get('analise_resumo', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'erro': 'Requisição inválida.'}, status=400)

    if not texto_usuario:
        return JsonResponse({'erro': 'Mensagem vazia.'}, status=400)

    conversa, _ = Conversa.objects.get_or_create(declaracao=declaracao)

    # Salva mensagem do usuário
    Mensagem.objects.create(conversa=conversa, papel='user', conteudo=texto_usuario)

    # Monta histórico para a API
    historico = [
        {'role': m.papel, 'content': m.conteudo}
        for m in conversa.mensagens.order_by('criada_em')
    ]

    # Monta system prompt com dados da declaração
    dados_decl = serializar_declaracao(declaracao)
    system_prompt = montar_system_prompt(dados_decl, passo_atual, analise_resumo)

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            system=system_prompt,
            messages=historico,
        )
        resposta = response.content[0].text
    except anthropic.AuthenticationError:
        resposta = 'Assistente temporariamente indisponível (chave de API não configurada).'
    except Exception as e:
        resposta = f'Ocorreu um erro ao contatar o assistente: {str(e)}'

    # Salva resposta do assistente
    Mensagem.objects.create(conversa=conversa, papel='assistant', conteudo=resposta)

    return JsonResponse({'resposta': resposta})
