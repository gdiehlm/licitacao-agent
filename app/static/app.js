const $ = (sel) => document.querySelector(sel);
let lastJobId = null;

async function apiGet(path){ const r=await fetch(path); if(!r.ok) throw new Error(await r.text()); return r.json(); }
async function apiPost(path, body){ const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}); if(!r.ok) throw new Error(await r.text()); return r.json(); }

function setStatus(text, ok=true){
  const el=$("#apiStatus");
  el.textContent=text;
  el.style.borderColor= ok ? "rgba(52,211,153,0.35)" : "rgba(251,113,133,0.35)";
  el.style.background= ok ? "rgba(52,211,153,0.10)" : "rgba(251,113,133,0.10)";
}

function renderNotes(notes){
  const box=$("#previewNotes"); box.innerHTML="";
  (notes||[]).forEach(n=>{ const d=document.createElement("div"); d.className="note"; d.textContent=n; box.appendChild(d); });
}

function renderItems(items){
  const box=$("#previewList"); box.innerHTML="";
  (items||[]).forEach(it=>{
    const div=document.createElement("div"); div.className="item";
    const isUnknown = it.categoria==="desconhecido";
    const badgeClass = isUnknown ? "warn" : "ok";
    const badgeTxt = isUnknown ? "Item novo (revisar)" : "Item reconhecido";
    div.innerHTML = `
      <div class="itemTop">
        <div class="badge ${badgeClass}">#${it.prioridade} • ${badgeTxt}</div>
        <div class="badge">Qtd ${it.quantidade} • ${it.unidade} • R$ ${Number(it.preco_unit).toFixed(2)}</div>
      </div>
      <div class="kv">
        <div class="kvRow"><div class="k">Referência</div><div class="v">${it.referencia_raw}</div></div>
        <div class="kvRow"><div class="k">Resumo</div><div class="v">${it.descricao_resumida}</div></div>
        <div class="kvRow"><div class="k">Detalhada</div><div class="v">${it.descricao_detalhada}</div></div>
      </div>
      ${(it.assumptions && it.assumptions.length) ? `
        <div class="sources">
          <div class="k">Assunções</div>
          <div class="v">• ${it.assumptions.join("\n• ")}</div>
        </div>` : ""}
      ${(it.sources && it.sources.length) ? `
        <div class="sources">
          <div class="k">Fontes</div>
          <div class="v">${it.sources.map(s=>`<div>• <a href="${s.url}" target="_blank" rel="noreferrer">${s.title||s.url}</a></div>`).join("")}</div>
        </div>` : ""}
    `;
    box.appendChild(div);
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
    $("#approved").checked=false; $("#btnGenerate").disabled=true;
  }catch(e){ alert("Erro no preview: "+e.message); }
  finally{ $("#btnPreview").disabled=false; }
}

async function doGenerate(){
  const template_id=$("#template").value;
  const prompt=$("#prompt").value.trim();
  if(!prompt) return alert("Cole um prompt antes.");
  if(!$("#approved").checked) return alert("Marque a aprovação antes de gerar.");
  $("#btnGenerate").disabled=true;
  try{
    const data=await apiPost("/api/generate",{template_id,prompt,approved:true});
    lastJobId=data.job_id;
    $("#btnCheckJob").disabled=false;
    $("#jobStatus").textContent="queued";
    $("#fileLink").textContent="—"; $("#fileLink").href="#";
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
      const path = String(data.result).replace(/\\/g,"/");
      const file = path.split("/").pop();
      const link = `/download/${encodeURIComponent(file)}`;
      $("#fileLink").textContent=file;
      $("#fileLink").href=link;
    }
  }catch(e){ alert("Erro ao consultar: "+e.message); }
  finally{ $("#btnCheckJob").disabled=false; }
}

function hook(){
  $("#btnPreview").addEventListener("click", doPreview);
  $("#btnGenerate").addEventListener("click", doGenerate);
  $("#btnCheckJob").addEventListener("click", checkJob);
  $("#approved").addEventListener("change", (ev)=>{ $("#btnGenerate").disabled=!ev.target.checked; });

  $("#prompt").value = "Gere uma planilha para uma licitação usando como base o arquivo Pregão Modelo.xlsx. Os itens de referencia em ordem de prioridade são, 20 unidades do Teclado Mecânico Redragon FIZZ RGB PRETO 60% no preço de R$ 400,00 cada; 50 caixas de clips de papel com 100 unidades cada de qualquer marca no preço de R$ 5,00 cada.";
}

async function boot(){
  try{ await loadTemplates(); setStatus("API online", true); }
  catch(e){ setStatus("API offline", false); }
  hook();
}
boot();
