const $ = (sel) => document.querySelector(sel);
let lastJobId = null;
let reviewedItems = [];

async function apiGet(path){ const r=await fetch(path); if(!r.ok) throw new Error(await r.text()); return r.json(); }
async function apiPost(path, body){ const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}); if(!r.ok) throw new Error(await r.text()); return r.json(); }

function setStatus(text, ok=true){
  const el=$("#apiStatus");
  el.textContent=text;
  el.style.borderColor= ok ? "rgba(52,211,153,0.35)" : "rgba(251,113,133,0.35)";
  el.style.background= ok ? "rgba(52,211,153,0.10)" : "rgba(251,113,133,0.10)";
}

function esc(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderNotes(notes){
  const box=$("#previewNotes"); box.innerHTML="";
  (notes||[]).forEach(n=>{ const d=document.createElement("div"); d.className="note"; d.textContent=n; box.appendChild(d); });
}

function syncReviewedItemsFromDOM(){
  const cards = document.querySelectorAll(".item");
  reviewedItems = Array.from(cards).map(card => ({
    prioridade: Number(card.dataset.prioridade),
    referencia_raw: card.dataset.referencia,
    categoria: card.dataset.categoria,
    quantidade: Number(card.dataset.quantidade),
    unidade: card.dataset.unidade,
    preco_unit: Number(card.dataset.preco),
    descricao_resumida: card.querySelector(".fieldResumo").value.trim(),
    descricao_detalhada: card.querySelector(".fieldDetalhada").value.trim(),
    assumptions: JSON.parse(card.dataset.assumptions || "[]"),
    sources: JSON.parse(card.dataset.sources || "[]")
  }));
}

function renderItems(items){
  reviewedItems = items.map(i=>({ ...i }));
  const box=$("#previewList"); box.innerHTML="";
  (items||[]).forEach(it=>{
    const div=document.createElement("div"); div.className="item";
    div.dataset.prioridade=String(it.prioridade);
    div.dataset.referencia=it.referencia_raw || "";
    div.dataset.categoria=it.categoria || "";
    div.dataset.quantidade=String(it.quantidade);
    div.dataset.unidade=it.unidade || "";
    div.dataset.preco=String(it.preco_unit);
    div.dataset.assumptions=JSON.stringify(it.assumptions || []);
    div.dataset.sources=JSON.stringify(it.sources || []);

    const isUnknown = it.categoria==="desconhecido";
    const badgeClass = isUnknown ? "warn" : "ok";
    const badgeTxt = isUnknown ? "Item novo (revisar)" : "Item reconhecido";
    div.innerHTML = `
      <div class="itemTop">
        <div class="badge ${badgeClass}">#${it.prioridade} • ${badgeTxt}</div>
        <div class="badge">Qtd ${it.quantidade} • ${esc(it.unidade)} • R$ ${Number(it.preco_unit).toFixed(2)}</div>
      </div>
      <div class="kv">
        <div class="kvRow"><div class="k">Referência</div><div class="v">${esc(it.referencia_raw)}</div></div>
        <div class="kvRow kvEditRow">
          <div class="k">Resumo (editável)</div>
          <div class="v"><textarea class="editField fieldResumo" rows="2">${esc(it.descricao_resumida)}</textarea></div>
        </div>
        <div class="kvRow kvEditRow">
          <div class="k">Detalhada (editável)</div>
          <div class="v"><textarea class="editField fieldDetalhada" rows="4">${esc(it.descricao_detalhada)}</textarea></div>
        </div>
      </div>
      ${(it.assumptions && it.assumptions.length) ? `
        <div class="sources">
          <div class="k">Assunções</div>
          <div class="v">• ${it.assumptions.map(esc).join("\n• ")}</div>
        </div>` : ""}
      ${(it.sources && it.sources.length) ? `
        <div class="sources">
          <div class="k">Fontes</div>
          <div class="v">${it.sources.map(s=>`<div>• <a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.title||s.url)}</a></div>`).join("")}</div>
        </div>` : ""}
    `;
    box.appendChild(div);
  });

  document.querySelectorAll(".editField").forEach(el=>{
    el.addEventListener("input", syncReviewedItemsFromDOM);
  });
}

async function loadTemplates(){
  const list=await apiGet("/api/templates");
  const sel=$("#template"); sel.innerHTML="";
  list.forEach(t=>{ const opt=document.createElement("option"); opt.value=t.id; opt.textContent=`${t.label} (${t.file})`; sel.appendChild(opt); });
}

async function doPreview(){
  const template_id=$("#template").value;
  const prompt=$("#prompt").value.trim();
  if(!prompt) return alert("Cole um prompt antes.");
  $("#btnPreview").disabled=true;
  try{
    const data=await apiPost("/api/preview",{template_id,prompt});
    renderNotes(data.notes); renderItems(data.items);
    syncReviewedItemsFromDOM();
    $("#approved").checked=false; $("#btnGenerate").disabled=true;
  }catch(e){ alert("Erro no preview: "+e.message); }
  finally{ $("#btnPreview").disabled=false; }
}

async function doGenerate(){
  const template_id=$("#template").value;
  const prompt=$("#prompt").value.trim();
  if(!prompt) return alert("Cole um prompt antes.");
  if(!$("#approved").checked) return alert("Marque a aprovação antes de gerar.");
  syncReviewedItemsFromDOM();
  $("#btnGenerate").disabled=true;
  try{
    const data=await apiPost("/api/generate",{template_id,prompt,items:reviewedItems,approved:true});
    lastJobId=data.job_id;
    $("#btnCheckJob").disabled=false;
    $("#jobStatus").textContent="queued";
    $("#fileLink").textContent="—"; $("#fileLink").href="#";
    $("#fileLinkGoogle").textContent="—"; $("#fileLinkGoogle").href="#";
  }catch(e){ alert("Erro ao gerar: "+e.message); }
  finally{ $("#btnGenerate").disabled=false; }
}

async function checkJob(){
  if(!lastJobId) return;
  $("#btnCheckJob").disabled=true;
  try{
    const data=await apiGet(`/api/job/${lastJobId}`);
    $("#jobStatus").textContent=data.status;
    if(data.status==="finished" && data.result){
      const xlsxPath = String(data.result.xlsx || "").replace(/\\/g,"/");
      const xlsxFile = xlsxPath.split("/").pop();
      if (xlsxFile) {
        const link = `/download/${encodeURIComponent(xlsxFile)}`;
        $("#fileLink").textContent=xlsxFile;
        $("#fileLink").href=link;
      }

      const googlePath = String(data.result.google_sheets_csv || "").replace(/\\/g,"/");
      const googleFile = googlePath.split("/").pop();
      if (googleFile) {
        const gLink = `/download/${encodeURIComponent(googleFile)}`;
        $("#fileLinkGoogle").textContent=googleFile;
        $("#fileLinkGoogle").href=gLink;
      }
    }
  }catch(e){ alert("Erro ao consultar: "+e.message); }
  finally{ $("#btnCheckJob").disabled=false; }
}

function hook(){
  $("#btnPreview").addEventListener("click", doPreview);
  $("#btnGenerate").addEventListener("click", doGenerate);
  $("#btnCheckJob").addEventListener("click", checkJob);
  $("#approved").addEventListener("change", (ev)=>{ $("#btnGenerate").disabled=!ev.target.checked; });

  $("#prompt").value = "Gere uma planilha para uma licitação usando como base o arquivo Pregão Modelo.xlsx. Os itens de referência em ordem de prioridade são: 20 unidades do Teclado Mecânico Redragon FIZZ RGB PRETO 60%; 50 caixas de clips de papel com 100 unidades cada de qualquer marca.";
}

async function boot(){
  try{ await loadTemplates(); setStatus("API online", true); }
  catch(e){ setStatus("API offline", false); }
  hook();
}
boot();
