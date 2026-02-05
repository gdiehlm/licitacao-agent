# Agente de Pregão (local) - Demonstração

Este projeto roda **localmente** via Docker (Windows/Mac/Linux) e demonstra:
- multiusuário (estrutura pronta para evoluir; nesta demo é API)
- busca web **sem assinatura** via **SearxNG** (self-host)
- geração de planilha `.xlsx` a partir de um template (Pregão Modelo.xlsx)
- fluxo com **preview → aprovação → gerar planilha**

## Pré-requisitos
- Docker Desktop instalado e funcionando.

## Subir tudo
Na pasta do projeto:
```bash
docker compose up -d --build
```

## Acessos
- API do agente: http://localhost:8000
- SearxNG: http://localhost:8080

## Templates
Coloque seus templates em:
`data/templates/`

Este projeto já inclui:
- `data/templates/Pregão Modelo.xlsx`
- `data/templates/templates.json` (mapeamento do template)

## Como usar (fluxo)
1) Preview (gera descrições e mostra fontes/assunções):
```bash
curl -X POST http://localhost:8000/api/preview ^
  -H "Content-Type: application/json" ^
  -d "{\"template_id\":\"PregaoModelo_v1\",\"prompt\":\"Gere ... 20 unidades do Teclado ... no preço de R$ 400,00 cada; 50 caixas de clipes ... no preço de R$ 5,00 cada.\"}"
```

2) Gerar (após revisar, envie approved=true):
```bash
curl -X POST http://localhost:8000/api/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"template_id\":\"PregaoModelo_v1\",\"prompt\":\"...\",\"approved\":true}"
```

3) Consultar status do job:
```bash
curl http://localhost:8000/api/job/<JOB_ID>
```

Quando finalizar, o `result` traz o caminho do arquivo gerado em `data/outputs/`.

## Observações importantes
- Para itens desconhecidos, a descrição é **preliminar** e vem acompanhada de **assunções** para revisão humana.
- O texto final aplica regra "sem marca/modelo" com sanitização básica (lista bloqueada). Você pode expandir a blocklist.
- Próximo passo: adicionar uma interface web (HTML) e autenticação (AD/LDAP/local).


## Tela no navegador
Abra: http://localhost:8000/ui


## Correção (SearxNG content=None)
Patch aplicado para lidar com resultados do SearxNG que retornam `content=null`.

## Se aparecer erro 403 do SearxNG no preview
O agente usa `format=json` para obter resultados do SearxNG. Algumas configurações do SearxNG bloqueiam JSON e retornam **403 Forbidden**.
Este projeto já inclui `searxng/settings.yml` habilitando JSON.

Se você já tinha subido os containers antes, rode:
```bash
docker compose down
docker compose up -d --build
```

Teste direto no navegador:
- http://localhost:8080/search?q=teste&format=json
Deve retornar JSON (não 403).


## Se o SearxNG não abrir em http://localhost:8080
Rode:
```bash
docker compose ps
docker compose logs --tail=200 searxng
```
Se aparecer erro de configuração, este projeto usa `./searxng/settings.yml` montado diretamente em `/etc/searxng/settings.yml`.

## SearxNG não inicia e reclama de secret_key
Se aparecer no log: `server.secret_key is not changed`, o SearxNG encerra o worker.
Este projeto já inclui um `server.secret_key` aleatório em `searxng/settings.yml`.
Após atualizar o projeto, rode:
```bash
docker compose down -v
docker compose up -d --build
```


## IA local (Ollama + Qwen)
Este projeto sobe um serviço Ollama em http://localhost:11434 e faz chamadas para gerar especificações técnicas detalhadas (especialmente para teclados).
Na primeira execução o modelo pode precisar ser baixado.

Testes:
- UI: http://localhost:8000/ui
- Ollama tags: http://localhost:11434/api/tags
