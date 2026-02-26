# SATL - Agente de Pregão (MVP)

Projeto do **SATL – Sistema Automatizado de Elaboração de Termos de Referência para Licitações Públicas Brasileiras**.

## O que esta versão entrega
- Backend em **FastAPI** e frontend web simples para fluxo de preview/geração.
- Geração de especificações técnicas com **Google Generative AI (SDK `google-generativeai`)**.
- Busca de evidências com **Google Search Grounding nativo do Gemini**.
- Geração de arquivos finais: **XLSX** (template) + **CSV** (Google Sheets).
- Fila assíncrona com Redis (web + worker).

## Aderência jurídica (Lei 14.133/2021)
A geração de especificações segue regras de neutralidade técnica:
- sem marcas/fabricantes/modelos;
- requisitos objetivos, mensuráveis e auditáveis;
- aceitação de equivalentes técnicos;
- linguagem formal administrativa.

## Requisitos
- Docker Desktop (Windows convencional, Windows Server, Linux, macOS) **ou** Python 3.11+ para execução local.
- Chave de API Gemini: `GEMINI_API_KEY`.

## Execução com Docker (recomendado)
1. Defina as variáveis de ambiente:
   - `GEMINI_API_KEY`
   - opcional: `GEMINI_MODEL` (default `gemini-1.5-pro`)
   - opcional: `GEMINI_TIMEOUT` (default `120`)

2. Suba os serviços:
```bash
docker compose up -d --build
```

3. Acessos:
- API/UI: http://localhost:8000/ui
- Redis: localhost:6379
- PostgreSQL: localhost:5432

## Execução local no Windows convencional e Windows Server (sem Docker)
> Compatível com Prompt de Comando (CMD) e PowerShell.

1. Instale dependências:
```powershell
cd app
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure variáveis de ambiente (PowerShell):
```powershell
$env:GEMINI_API_KEY="SUA_CHAVE"
$env:REDIS_URL="redis://localhost:6379/0"
$env:TEMPLATES_DIR="..\data\templates"
$env:OUTPUTS_DIR="..\data\outputs"
$env:LOGS_DIR="..\data\logs"
```

3. Suba API e worker em terminais separados:
```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
python -m rq worker default
```

> Em CMD, use `set GEMINI_API_KEY=SUA_CHAVE` etc.

## Fluxo de uso
1. `POST /api/preview` para parse + preço estimado + descrição técnica.
2. Revisão humana na UI.
3. `POST /api/generate` com `approved=true` para produzir XLSX e CSV.
4. `GET /api/job/{job_id}` para acompanhar conclusão.

## Observações
- O cálculo de preços e as fontes agora são extraídos via grounding do Gemini.
- Caso a IA não encontre amostras suficientes, o preview retorna erro para revisão do item.
