"""
Extração de dados fiscais de documentos enviados pelo usuário.

Fluxo:
  1. Lê o arquivo:
     - Imagem (PNG/JPG/WEBP) → base64 → vision
     - PDF com texto nativo  → extrai texto → envia como texto
     - PDF escaneado (sem texto) → renderiza páginas como PNG via PyMuPDF → vision
  2. Envia para a Claude API
  3. Claude retorna JSON estruturado com os campos fiscais
  4. O resultado é salvo em Documento.dados_extraidos
"""
import io
import json
import base64
import mimetypes

import anthropic
from django.conf import settings

from .prompts import PROMPT_EXTRACAO

# Máximo de páginas renderizadas para PDFs escaneados (evita tokens excessivos)
MAX_PAGINAS_SCAN = 3


def _extrair_texto_pdf(caminho: str) -> str:
    """Extrai texto de todas as páginas do PDF via pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(caminho)
    paginas = [p.extract_text() or '' for p in reader.pages]
    return '\n'.join(paginas).strip()


def _pdf_para_imagens_b64(caminho: str) -> list[dict]:
    """
    Renderiza as páginas de um PDF como PNG via PyMuPDF.
    Retorna lista de dicts no formato de content block da API Anthropic.
    """
    import fitz  # PyMuPDF
    doc = fitz.open(caminho)
    blocos = []
    for i, pagina in enumerate(doc):
        if i >= MAX_PAGINAS_SCAN:
            break
        # Renderiza a 150 DPI — boa resolução sem explodir o token count
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pix = pagina.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes('png')
        b64 = base64.standard_b64encode(png_bytes).decode('utf-8')
        blocos.append({
            'type': 'image',
            'source': {'type': 'base64', 'media_type': 'image/png', 'data': b64},
        })
    doc.close()
    return blocos


def _arquivo_e_imagem(caminho: str) -> bool:
    mime, _ = mimetypes.guess_type(caminho)
    return mime in ('image/png', 'image/jpeg', 'image/webp', 'image/gif')


def _chamar_api(client, content: list) -> str:
    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        messages=[{'role': 'user', 'content': content}],
    )
    return response.content[0].text.strip()


def extrair_dados(documento) -> dict:
    """
    Processa um Documento e retorna o dict extraído pela LLM.
    Lança exceção em caso de falha — o chamador deve tratar.
    """
    caminho = documento.arquivo.path
    mime, _ = mimetypes.guess_type(caminho)
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    if _arquivo_e_imagem(caminho):
        # Imagem nativa → vision direto
        with open(caminho, 'rb') as f:
            b64 = base64.standard_b64encode(f.read()).decode('utf-8')
        content = [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}},
            {'type': 'text', 'text': PROMPT_EXTRACAO},
        ]
        raw = _chamar_api(client, content)

    else:
        # PDF — tenta extrair texto primeiro
        texto = _extrair_texto_pdf(caminho)

        if texto:
            # PDF com texto nativo
            content = [{'type': 'text', 'text': f"{PROMPT_EXTRACAO}\n\n---\nCONTEÚDO DO DOCUMENTO:\n{texto}"}]
            raw = _chamar_api(client, content)
        else:
            # PDF escaneado — renderiza páginas como imagem e envia via vision
            blocos = _pdf_para_imagens_b64(caminho)
            if not blocos:
                return {'erro': 'Não foi possível processar o PDF. O arquivo pode estar corrompido.'}
            content = blocos + [{'type': 'text', 'text': PROMPT_EXTRACAO}]
            raw = _chamar_api(client, content)

    # Claude pode devolver o JSON dentro de ```json ... ```
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {'erro': 'Resposta da IA não pôde ser interpretada.', 'raw': raw}
