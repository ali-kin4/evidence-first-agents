/* Evidence First Agents — real scanner-backed authority workbench. */
const $=s=>document.querySelector(s);
const $$=s=>Array.from(document.querySelectorAll(s));
const ESC={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"};
const safe=v=>String(v??"").replace(/[&<>"']/g,k=>ESC[k]);
let catalog=null, sample=null, current="unsafe", chosenView="overview", simulation=null, notificationTimer;
const labels={overview:"Overview",scenarios:"Scenario library",authority:"Authority map",findings:"Finding explorer",lab:"Remediation lab",training:"Training walkthrough",methodology:"Methodology"};
const meaning={ready:"No findings in the declared static checks. Runtime safety remains unverified.",
warn:"Configuration contains ambiguity requiring review. This is not proof of exploitation.",
fail:"Declared policy has one or more violations. Prioritize these before runtime deployment.",
blocked:"Some evidence could not be resolved. A complete static assessment was not possible."};
const icon={safe:"✓",ambiguous:"?",unsafe:"!",business:"▥"};
const severityPriority={blocked:0,failure:1,warning:2};

async function api(path,init) {
  const response=await fetch(path,{cache:"no-store",...init});
  let body;try{body=await response.json();}catch{throw new Error("Local server returned unreadable data.");}
  if(!response.ok)throw new Error(body.error||("Request failed: "+response.status));
  return body;
}
function toast(msg) {
  const t=$("#toast");t.textContent=msg;t.classList.add("show");
  clearTimeout(notificationTimer);notificationTimer=setTimeout(()=>t.classList.remove("show"),4000);
}
function showError(message){$("#error").hidden=false;$("#error").textContent=message;}
function closeNav(){
  $("#sidebar").classList.remove("open");$("#scrim").hidden=true;
  $("#menuButton").setAttribute("aria-expanded","false");
}
function navigate(view) {
  if(!labels[view])return;
  chosenView=view;
  $$(".screen").forEach(el=>el.classList.toggle("active",el.id==="screen-"+view));
  $$(".nav-link[data-view]").forEach(el=>{
    const active=el.dataset.view===view;el.classList.toggle("active",active);
    if(active)el.setAttribute("aria-current","page");
    else el.removeAttribute("aria-current");
  });
  $("#breadcrumb").textContent=labels[view];closeNav();
  if(location.hash!=="#"+view)history.replaceState(null,"","#"+view);
  window.scrollTo(0,0);
}
async function selectScenario(key){
  if(!catalog.scenarios.some(s=>s.id===key))return;
  current=key;
  try {
    sample=await api("/api/scenario?case="+encodeURIComponent(key));
    simulation=null;
    $("#scenarioSelect").value=key;
    renderEverything();
    toast("Loaded fictional scenario: "+sample.story.title);
  } catch(err){showError(err.message);}
}
function pill(decision){return '<span class="state-pill '+safe(decision)+'">'+safe(decision.toUpperCase())+'</span>';}
function itemRow(symbol,value,label){return '<article class="metric-card"><span class="metric-icon">'+symbol+
  '</span><div class="metric-value">'+safe(value)+'</div><div class="metric-label">'+safe(label)+'</div></article>';}
function renderOverview(){
  const g=sample.governance,sm=g.summary;
  $("#metrics").innerHTML=[
    ["◇",sm.instructions,"Root instruction files"],["⌘",sm.mcp_servers,"Discovered MCP servers"],
    ["◈",sm.capabilities,"Declared capabilities"],
    ["◎",sm.warnings+sm.failures+sm.blocked,"Static findings"]
  ].map(row=>itemRow(...row)).join("");
  $("#navFindings").textContent=g.findings.length;
  $("#decisionRing").className="decision-ring "+g.decision;
  $("#decisionText").textContent=g.decision.toUpperCase();
  $("#decisionMeaning").textContent=meaning[g.decision];
  const domains=g.domains;
  const max=Math.max(1,...domains.map(d=>d.findings));
  $("#domainRows").innerHTML=domains.map(d=>
    '<div class="domain-row '+(d.findings?"alert-row":"")+'" title="No finding is not certification">' +
    '<strong>'+safe(d.name)+'</strong><div class="domain-bar"><span style="width:'+
    (d.findings?Math.max(12,100*d.findings/max):0)+'%"></span></div><span class="domain-state '+
    (d.findings?"attention":"")+'">'+(d.findings?d.findings+" finding"+(d.findings===1?"":"s"):"No signal")+
    '</span></div>'
  ).join("");
  const focus=[...g.findings].sort((a,b)=>(severityPriority[a.severity]??9)-(severityPriority[b.severity]??9)).slice(0,4);
  $("#priorityFindings").innerHTML=focus.length?focus.map(f=>
    '<div class="priority-row '+safe(f.severity)+'"><span class="priority-symbol">'+(f.severity==="warning"?"!":"✕")+
    '</span><div class="priority-details"><strong>'+safe(f.title)+'</strong><small>'+safe(f.code)+
    ' · '+safe(f.domain)+'</small></div><span class="tiny-badge '+safe(f.severity)+'">'+
    safe(f.severity.toUpperCase())+'</span></div>'
  ).join(""):'<div class="empty-summary">No findings in the declared checks. This does not establish runtime safety or resistance to prompt injection.</div>';
  $("#workflowPreview").innerHTML='<span aria-hidden="true">↗</span><span>'+safe(sample.story.workflow)+'</span>';
  $("#lessonPreview").textContent=sample.story.lesson;
}
function renderScenarios(){
  $("#scenarioCards").innerHTML=catalog.scenarios.map(c=>{
    const status={safe:"ready",ambiguous:"warn",unsafe:"fail",business:"fail"}[c.id];
    return '<article class="panel scenario-card '+(current===c.id?"selected":"")+'"><div class="scenario-card-top">'+
      '<span class="scenario-glyph">'+icon[c.id]+'</span>'+pill(status)+'</div>'+
      '<h3>'+safe(c.title)+'</h3><p>'+safe(c.subtitle)+'</p>'+
      '<div class="scenario-bottom"><span class="eyebrow">FICTIONAL WORKFLOW</span><button type="button" data-case="'+
      safe(c.id)+'">Inspect example ↗</button></div></article>';
  }).join("");
}
function renderAuthority(){
  const inventory=sample.governance.inventory;
  const instructions=inventory.instructions.map(x=>({
    name:x.path,detail:"Root instruction · "+x.bytes+" bytes",cls:"instruction"
  }));
  const servers=inventory.mcp_servers.map(x=>({
    name:x.name,detail:x.transport+" · "+x.config_path,cls:"server"
  }));
  const capabilities=inventory.capabilities.map(x=>({
    name:x.id,detail:x.kind+" · approval "+x.approval,cls:"capability"
  }));
  const blocks=arr=>arr.length?arr.map(x=>
    '<div class="authority-block '+x.cls+'"><strong>'+safe(x.name)+'</strong><small>'+
    safe(x.detail)+'</small></div>').join("") :
    '<div class="authority-block"><strong>Not declared</strong><small>No evidence in this inventory layer</small></div>';
  $("#authorityDiagram").innerHTML='<div class="authority-map">'+
    '<div class="eyebrow">DISCOVERED INSTRUCTION SOURCES</div><div class="authority-layer">'+blocks(instructions)+'</div>'+
    '<div class="authority-arrow" aria-hidden="true">↓</div>'+
    '<div class="eyebrow">CONFIGURED MCP ENDPOINTS</div><div class="authority-layer">'+blocks(servers)+'</div>'+
    '<div class="authority-arrow" aria-hidden="true">↓</div>'+
    '<div class="eyebrow">DECLARED CAPABILITIES</div><div class="authority-layer">'+blocks(capabilities)+'</div></div>';
  $("#authorityList").innerHTML=capabilities.length?
    inventory.capabilities.map(c=>
      '<div class="authority-entry"><strong>'+safe(c.id)+'</strong><small>'+
      safe(c.kind)+' · '+safe(c.source||"No source declared")+'</small><small>Named operations: '+
      safe(c.tools.join(", ")||"None declared")+'</small><span class="state-pill '+
      (c.approval==="required"?"ready":c.kind.endsWith("_write")?"fail":"warn")+
      '">Approval: '+safe(c.approval)+'</span></div>'
    ).join(""):'<div class="empty-authority">No capabilities were declared. This does not prove there are no runtime permissions.</div>';
}
function renderFindings(){
  const query=$("#findingSearch").value.trim().toLowerCase();
  const level=$("#severityFilter").value;
  const findings=sample.governance.findings.filter(f=>
    (level==="all"||f.severity===level)&&[f.code,f.title,f.domain,f.path,f.message].some(v=>
      String(v||"").toLowerCase().includes(query)));
  $("#findingCount").textContent=findings.length+" of "+sample.governance.findings.length+" findings";
  $("#findingList").innerHTML=findings.length?findings.map(f=>
    '<article class="panel finding-card">'+
      '<div class="finding-head"><div><div class="finding-id">'+safe(f.code)+
      ' · '+safe(f.domain)+'</div><h3>'+safe(f.title)+'</h3><p>'+safe(f.message)+
      (f.path?" · "+safe(f.path):"")+'</p></div>'+
      '<span class="tiny-badge '+safe(f.severity)+'">'+safe(f.severity.toUpperCase())+'</span></div>'+
      '<div class="finding-section"><strong>Why investigate</strong><p>'+safe(f.why)+'</p></div>'+
      '<div class="finding-section"><strong>Recommended configuration change</strong><p>'+safe(f.fix)+'</p></div>'+
      '<div class="finding-section"><strong>Verification still needed</strong><p>'+safe(f.verify)+'</p></div>'+
      '<div class="finding-actions"><a href="'+safe(f.reference.url)+
      '" target="_blank" rel="noopener noreferrer">Reference: '+safe(f.reference.label)+
      ' ↗</a><button type="button" data-go="lab">Test controls ↗</button></div></article>'
  ).join(""):'<div class="no-findings">No matching findings. A clean static report does not certify runtime security.</div>';
}
const suggested={
  "EMBEDDED_SECRET":"environment_secret","APPROVAL_BOUNDARY_MISSING":"require_approval",
  "WILDCARD_TOOL_SCOPE":"limit_tools","CONTRACT_MISSING":"policy_contract",
  "INSTRUCTION_PRECEDENCE_UNDECLARED":"instruction_precedence",
  "MCP_TRANSPORT_UNSPECIFIED":"mcp_transport"
};
function renderLab(){
  const preferred=new Set(sample.governance.findings.map(x=>suggested[x.code]).filter(Boolean));
  $("#controlChoices").innerHTML=Object.entries(catalog.controls).map(([code,label])=>{
    const selected=preferred.has(code);
    return '<label class="choice-option"><input type="checkbox" name="controls" value="'+
      safe(code)+'" '+(selected?"checked":"")+'><span><strong>'+safe(label)+
      '</strong><small>'+(selected?"Suggested by the current finding set.":"Explore whether this control applies.")+
      '</small></span></label>';
  }).join("");
  $("#labComparison").innerHTML='<div class="empty-graphic"><span>⌘</span><strong>Real checks, disposable changes.</strong>'+
    '<p>Select your controls and rescan a fictional copy. No production agent runs.</p></div>';
  $("#labNotes").hidden=true;
}
function renderMethod(){
  const items=[
    ["◎","Measured configuration evidence","The scanner inspects files, local skill references, declared authority, transport settings and selected credential-like fields. Results are reproducible static observations."],
    ["◇","What READY actually means",sample.governance.scope+" READY is not a certification; warning-free declared checks can coexist with unobserved runtime vulnerabilities."],
    ["✧","Human approval is a runtime control","An approval = required declaration indicates policy intent. It cannot prove a model/tool runtime will pause before consequential action. Validate approval enforcement separately."],
    ["◷","The remediation experiment","Chosen fixes are applied only to a fresh temporary copy of a fictional project. The actual scanner is run before and after. A changed verdict is evidence of changed configuration—not operational safety."],
    ["⇢","Model-specific prompt injection","Untrusted retrieved documents, tool responses and user-provided text can influence agents. Static inspection of these fixtures does not test attack success or defenses; use a separate authorized evaluation."],
    ["▥","MCP trust and identity","A configured transport or environment secret does not establish token audience validation, least-privilege scopes, server trust, or a secure OAuth flow. Review these using protocol-specific tests."],
    ["♙","Learning scenarios are synthetic","Scenario files, credentials, hostnames, and workflows are fictional. No business-client findings or actual security incidents are asserted."],
    ["✓","Evidence-linked guidance","Finding explanations cite public guidance such as OWASP, MCP Security Best Practices, NIST AI RMF and the Agents SDK. These mappings are interpretive training guidance—not an official compliance assessment."],
  ];
  $("#methodCards").innerHTML=items.map(([symbol,title,description])=>
    '<article class="panel method-card"><span class="method-icon">'+symbol+
    '</span><h3>'+safe(title)+'</h3><p>'+safe(description)+'</p></article>'
  ).join("");
}
function renderTraining(){
  const steps=[
    ["01","00–08 min","Map an agent's authority","Start with the customer-support case; identify tools that only read versus those that write customer data.","authority"],
    ["02","08–18 min","Inspect actual configuration evidence","Compare ready, warning and failure cases. Ask which claims are grounded and which are still untested.","scenarios"],
    ["03","18–32 min","Run a real remediation experiment","Open the unsafe publisher, choose least-privilege, approval and credential controls, then compare rescanned findings.","lab"],
    ["04","32–40 min","Challenge the result","A clean scan is not proof of secure runtime execution. Discuss prompt injection, OAuth audience, delegation and approval bypass tests.","methodology"],
    ["05","40–45 min","Export and discuss","Export the static evidence JSON and define one additional runtime verification task for the team's actual agent.","findings"],
  ];
  $("#trainingSteps").innerHTML=steps.map(([num,time,title,detail,route])=>
    '<article class="panel training-step"><div class="training-top"><span class="step-num">'+
    num+'</span><span class="training-time">'+time+'</span></div><h3>'+safe(title)+
    '</h3><p>'+safe(detail)+'</p><button type="button" data-go="'+safe(route)+
    '">Open relevant workspace ↗</button></article>').join("");
}
function renderEverything(){
  renderOverview();renderScenarios();renderAuthority();renderFindings();renderLab();renderMethod();renderTraining();
}
async function simulate(){
  const controls=$$('input[name="controls"]:checked').map(el=>el.value);
  const button=$("#simulateButton");
  button.disabled=true;button.textContent="Rescanning disposable configuration…";
  try {
    simulation=await api("/api/simulate",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({case:current,controls})
    });
    const before=simulation.before,after=simulation.after;
    $("#labComparison").innerHTML=
      '<div class="comparison-grid"><div class="comparison-state"><div class="eyebrow">BEFORE</div>'+
      '<h4>'+safe(before.decision.toUpperCase())+'</h4><p>'+
      before.findings.length+' static findings</p></div>'+
      '<div class="comparison-state after"><div class="eyebrow">AFTER DISPOSABLE RESCAN</div>'+
      '<h4>'+safe(after.decision.toUpperCase())+'</h4><p>'+
      after.findings.length+' static findings</p></div></div>'+
      '<div class="result-detail success"><b>Resolved finding codes:</b> '+safe(simulation.resolved.join(", ")||"None")+'</div>'+
      '<div class="result-detail"><b>Remaining finding codes:</b> '+safe(simulation.remaining.join(", ")||"None detected in these checks")+'</div>'+
      '<div class="result-detail note"><b>Applicable controls:</b> '+
      safe(simulation.applied.join(", ")||"None")+'<br><b>Not applicable:</b> '+
      safe(simulation.notApplicable.join(", ")||"None")+'</div>';
    $("#labNotes").hidden=false;
    $("#labNotes").innerHTML='<h3>What has actually been tested?</h3><p>'+
      safe(simulation.limitation)+'</p>';
    toast("Completed a real static rescan of the disposable teaching fixture.");
  }catch(err){toast("Simulation failed: "+err.message);}
  finally{button.disabled=false;button.innerHTML='Run disposable-copy rescan <span>↗</span>';}
}
function exportEvidence(){
  if(!sample)return;
  const text=JSON.stringify({
    artifact:"Evidence First Agents teaching evidence",fictional:true,
    scenario:current,governance:sample.governance,simulatedRescan:simulation
  },null,2);
  const url=URL.createObjectURL(new Blob([text],{type:"application/json"}));
  const a=document.createElement("a");a.href=url;a.download="evidence-first-"+current+"-training.json";
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1200);
  toast("Exported local scenario evidence (fictional).");
}
function events(){
  $$("[data-view]").forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.view)));
  document.addEventListener("click",ev=>{
    const button=ev.target.closest("[data-go],[data-case]");
    if(!button)return;
    if(button.dataset.case){selectScenario(button.dataset.case).then(()=>navigate("overview"));}
    else if(button.dataset.go)navigate(button.dataset.go);
  });
  $("#scenarioSelect").addEventListener("change",ev=>selectScenario(ev.target.value));
  $("#findingSearch").addEventListener("input",renderFindings);
  $("#severityFilter").addEventListener("change",renderFindings);
  $("#simulateButton").addEventListener("click",simulate);
  $("#exportReport").addEventListener("click",exportEvidence);
  $("#menuButton").addEventListener("click",()=>{
    const expanded=$("#sidebar").classList.toggle("open");
    $("#scrim").hidden=!expanded;$("#menuButton").setAttribute("aria-expanded",String(expanded));
  });
  $("#scrim").addEventListener("click",closeNav);
  window.addEventListener("keydown",ev=>{if(ev.key==="Escape")closeNav();});
}
async function init(){
  $("#year").textContent=String(new Date().getFullYear());
  events();
  try{
    catalog=await api("/api/catalog");
    $("#scenarioSelect").innerHTML=catalog.scenarios.map(c=>
      '<option value="'+safe(c.id)+'">'+safe(c.title)+'</option>').join("");
    await selectScenario("unsafe");
    const hash=location.hash.slice(1);navigate(labels[hash]?hash:"overview");
  }catch(err){showError("Cannot load the local workbench: "+err.message);}
}
init();
