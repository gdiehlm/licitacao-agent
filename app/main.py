import os
import json
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue

from services.prompt_parser import parse_prompt
from services.spec_builder import build_spec
from services.pricing import estimate_price_from_licitacon
from services.llm_client import LLMError
from services.excel_writer import OutputItem, write_from_template, write_google_sheets_csv, dated_filename

APP_DIR = Path(__file__).parent
DATA_TEMPLATES = Path(os.environ.get("TEMPLATES_DIR", "/data/templates"))
DATA_OUTPUTS = Path(os.environ.get("OUTPUTS_DIR", "/data/outputs"))
LOGS_DIR = Path(os.environ.get("LOGS_DIR", "/data/logs"))

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
redis_conn = Redis.from_url(REDIS_URL)
q = Queue("default", connection=redis_conn)

app = FastAPI(title="Agente de Pregão - MVP Local")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

@app.get("/ui", response_class=HTMLResponse)
def ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/download/{filename}")
def download(filename: str):
    safe = os.path.basename(filename)
    path = DATA_OUTPUTS / safe
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(path, filename=safe)


class PreviewRequest(BaseModel):
    template_id: str = Field(default="PregaoModelo_v1")
    prompt: str

class PreviewItem(BaseModel):
    prioridade: int
    unidade: str
    quantidade: int
    preco_unit: float
    referencia_raw: str
    categoria: str
    descricao_resumida: str
    descricao_detalhada: str
    assumptions: List[str] = Field(default_factory=list)
    sources: List[dict] = Field(default_factory=list)

class PreviewResponse(BaseModel):
    template_id: str
    items: List[PreviewItem]
    notes: List[str] = Field(default_factory=list)

def load_templates():
    cfg_path = DATA_TEMPLATES / "templates.json"
    if not cfg_path.exists():
        raise RuntimeError(f"templates.json não encontrado em {cfg_path}")
    return json.loads(cfg_path.read_text(encoding="utf-8"))

@app.get("/api/templates")
def list_templates():
    cfg = load_templates()
    return [{"id": k, "label": v.get("label", k), "file": v.get("file")} for k,v in cfg.items()]

@app.post("/api/preview", response_model=PreviewResponse)
def preview(req: PreviewRequest):
    cfg = load_templates()
    if req.template_id not in cfg:
        raise HTTPException(400, "Template inválido")

    try:
        parsed = parse_prompt(req.prompt)
    except Exception as e:
        raise HTTPException(400, str(e))

    items_out: List[PreviewItem] = []
    notes: List[str] = []
    for p in parsed:
        try:
            pricing = estimate_price_from_licitacon(p.referencia_raw)
        except Exception as e:
            raise HTTPException(502, f"Erro ao calcular preço médio no LicitaCon para '{p.referencia_raw}': {e}")
        preco_estimado = pricing["average"]
        try:
            spec = build_spec(p.referencia_raw, preco_estimado)
        except LLMError as e:
            raise HTTPException(502, f"Erro ao gerar especificação via IA (Gemini): {e}")
        notes.append(
            f"Item {p.prioridade}: preço unitário estimado pelo LicitaCon com média de {len(pricing['samples'])} itens similares (R$ {preco_estimado:.2f})."
        )
        if spec["categoria"] == "desconhecido":
            notes.append(f"Item {p.prioridade}: categoria desconhecida, usei pesquisa web e gerei uma descrição preliminar para revisão.")
        items_out.append(PreviewItem(
            prioridade=p.prioridade,
            unidade=p.unidade,
            quantidade=p.quantidade,
            preco_unit=preco_estimado,
            referencia_raw=p.referencia_raw,
            categoria=spec["categoria"],
            descricao_resumida=spec["resumo"],
            descricao_detalhada=spec["detalhada"],
            assumptions=spec.get("assumptions",[]),
            sources=spec.get("sources",[])
        ))
    return PreviewResponse(template_id=req.template_id, items=items_out, notes=notes)

class GenerateRequest(BaseModel):
    template_id: str = Field(default="PregaoModelo_v1")
    prompt: str
    items: List[PreviewItem] = Field(default_factory=list)
    # preço unitário é calculado via média de itens similares no LicitaCon durante o preview
    approved: bool = False

class GenerateResponse(BaseModel):
    job_id: str

def _output_item_from_preview(item: PreviewItem) -> OutputItem:
    return OutputItem(
        prioridade=item.prioridade,
        descricao_resumida=item.descricao_resumida,
        descricao_detalhada=item.descricao_detalhada,
        unidade=item.unidade,
        quantidade=item.quantidade,
        preco_unit=item.preco_unit,
    )

def _generate_files(template_id: str, prompt: str, reviewed_items: List[dict]) -> dict:
    cfg = load_templates()
    t = cfg[template_id]

    output_items: List[OutputItem] = []
    if reviewed_items:
        output_items = [_output_item_from_preview(PreviewItem(**item)) for item in reviewed_items]
    else:
        parsed = parse_prompt(prompt)
        for p in parsed:
            try:
                pricing = estimate_price_from_licitacon(p.referencia_raw)
            except Exception as e:
                raise HTTPException(502, f"Erro ao calcular preço médio no LicitaCon para '{p.referencia_raw}': {e}")
            preco_estimado = pricing["average"]
            try:
                spec = build_spec(p.referencia_raw, preco_estimado)
            except LLMError as e:
                raise HTTPException(502, f"Erro ao gerar especificação via IA (Gemini): {e}")
            output_items.append(OutputItem(
                prioridade=p.prioridade,
                descricao_resumida=spec["resumo"],
                descricao_detalhada=spec["detalhada"],
                unidade=p.unidade,
                quantidade=p.quantidade,
                preco_unit=preco_estimado
            ))

    DATA_OUTPUTS.mkdir(parents=True, exist_ok=True)
    filename_xlsx = dated_filename("Pregão")
    out_path_xlsx = DATA_OUTPUTS / filename_xlsx
    filename_gsheets = dated_filename("Pregão GoogleSheets", "csv")
    out_path_gsheets = DATA_OUTPUTS / filename_gsheets

    template_path = DATA_TEMPLATES / t["file"]
    if not template_path.exists():
        raise RuntimeError(f"Template não encontrado: {template_path}")

    write_from_template(
        template_path=str(template_path),
        out_path=str(out_path_xlsx),
        sheet=t["sheet"],
        start_row=int(t["start_row"]),
        columns=t["columns"],
        items=output_items
    )
    write_google_sheets_csv(str(out_path_gsheets), output_items)
    return {"xlsx": str(out_path_xlsx), "google_sheets_csv": str(out_path_gsheets)}

@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    if not req.approved:
        raise HTTPException(400, "Envie approved=true depois de revisar o preview.")
    cfg = load_templates()
    if req.template_id not in cfg:
        raise HTTPException(400, "Template inválido")

    reviewed_items = [item.model_dump() for item in req.items]
    job = q.enqueue(_generate_files, req.template_id, req.prompt, reviewed_items)
    return GenerateResponse(job_id=job.get_id())

@app.get("/api/job/{job_id}")
def job_status(job_id: str):
    from rq.job import Job
    job = Job.fetch(job_id, connection=redis_conn)
    status = job.get_status()
    result = job.result if job.is_finished else None
    return {"job_id": job_id, "status": status, "result": result}

@app.get("/")
def root():
    return {
        "ok": True,
        "endpoints": ["/ui", "/api/templates", "/api/preview", "/api/generate", "/api/job/{job_id}", "/download/{filename}"],
        "notes": "Use /api/preview para revisar descrições e fontes antes de gerar."
    }
