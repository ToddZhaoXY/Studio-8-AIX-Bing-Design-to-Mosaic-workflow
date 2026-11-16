'use strict';
const $ = id => document.getElementById(id);
const state = {csrf:'',catalog:[],selected:new Set(),library:'all',search:'',category:'all',skills:null,environment:null,job:null,poll:null,preview:null,defaults:{},filtered:[]};
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL = value => { try { const u=new URL(String(value),location.origin); return ['http:','https:'].includes(u.protocol)?u.href:'#'; } catch {return '#';} };
const countLabel = (count,singular,plural=singular+'s') => `${count} ${count===1?singular:plural}`;
const formatDate = value => new Date(value).toLocaleString('en-US',{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
const textValue = value => typeof value==='string'?value:JSON.stringify(value ?? 'Not recorded');
const summaryText = value => typeof value==='string'?value:value?.message||value?.error||'Results are saved. Review the evidence and differences below.';
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,4200);}
function errorText(...values){
  const parts=[],seen=new Set();
  const append=(value,depth=0)=>{
    if(value===null||value===undefined||value===false||depth>8)return;
    if(typeof value==='string'){
      const message=value.trim();if(!message)return;
      try{const parsed=JSON.parse(message);if(parsed&&typeof parsed==='object'||typeof parsed==='string'&&parsed!==message){append(parsed,depth+1);return;}}catch{}
      const key=message.replace(/\s+/g,' ').toLowerCase();
      if(!seen.has(key)){seen.add(key);parts.push(message);}return;
    }
    if(Array.isArray(value)){value.forEach(item=>append(item,depth+1));return;}
    if(typeof value==='object'){
      const fields=[value.message,value.error,value.reason,value.hint];
      if(fields.some(field=>field!==null&&field!==undefined&&field!==''))fields.forEach(field=>append(field,depth+1));
      else Object.values(value).forEach(field=>append(field,depth+1));
      return;
    }
    append(String(value),depth+1);
  };
  values.forEach(value=>append(value));
  return parts.join(' · ');
}
function error(message){const readable=errorText(message);$('global-error').textContent=readable;$('global-error').hidden=!readable;}
async function api(path,options={}){
  const headers={...(options.body&&typeof options.body==='string'?{'Content-Type':'application/json'}:{}),...options.headers};
  if(options.method&&options.method!=='GET')headers['X-Workbench-Token']=state.csrf;
  const response=await fetch(path,{...options,headers});
  const data=await response.json();
  if(!response.ok)throw new Error(errorText(data?.message,data?.error,data?.reason,data?.hint)||`Request failed (${response.status})`);
  return data;
}
function libraryName(item){return item.libraryName||({'mm-image':'MM Image',aigc:'AIGC',video:'Video'}[item.library]||item.library);}
function visibleItems(){return state.catalog.filter(i=>(state.library==='all'||i.library===state.library)&&(state.category==='all'||(i.componentId||i.category)===state.category)&&(!state.search||[i.name,i.variant,i.size,i.description,i.componentId,libraryName(i)].join(' ').toLowerCase().includes(state.search)));}
function renderCategories(){
  const choices=new Map();
  for(const item of state.catalog.filter(i=>state.library==='all'||i.library===state.library))choices.set(item.componentId||item.category,item.name);
  $('category').innerHTML='<option value="all">All types</option>'+[...choices].map(([value,name])=>`<option value="${escapeHTML(value)}">${escapeHTML(name)}</option>`).join('');
  $('category').value=choices.has(state.category)?state.category:'all';state.category=$('category').value;
}
function thumb(item){
  if(item.thumbnail){const url=item.thumbnail.startsWith('/')?item.thumbnail:'/library/'+item.thumbnail;return `<img src="${escapeHTML(safeURL(url))}" alt="" loading="lazy">`;}
  return `<span class="wireframe ${escapeHTML(item.library)}" aria-hidden="true"><i></i><i></i><i></i></span>`;
}
function renderCatalog(){
  const items=visibleItems();state.filtered=items;
  $('filter-count').textContent=countLabel(items.length,'result');
  if(!items.length){$('catalog').innerHTML='<div class="empty-state">No matching components. Try another name or size.</div>';updateSelection();return;}
  $('catalog').innerHTML=items.map(i=>`<div class="catalog-row ${state.selected.has(i.id)?'selected':''}" data-id="${escapeHTML(i.id)}"><input class="item-check" type="checkbox" aria-label="Select ${escapeHTML(i.name+' '+(i.variant||'')+' '+(i.size||''))}" ${state.selected.has(i.id)?'checked':''}><div class="component-thumb">${thumb(i)}</div><div class="row-main"><strong>${escapeHTML(i.variant||i.name)}</strong><small>${escapeHTML(libraryName(i))} / ${escapeHTML(i.name)}${i.variant&&i.variant!==i.name?'':' / '+escapeHTML(i.category||'Component')}</small></div><div class="row-dim"><b>${escapeHTML(i.size||'Default')}</b>${i.width&&i.height?`<br>${escapeHTML(i.width)} × ${escapeHTML(i.height)}`:''}</div><button class="peek-button" aria-label="Preview ${escapeHTML(i.name+' '+(i.variant||''))}">Preview</button></div>`).join('');
  $('catalog').querySelectorAll('.catalog-row').forEach(row=>{
    row.querySelector('.item-check').addEventListener('change',()=>toggle(row.dataset.id));
    row.querySelector('.peek-button').addEventListener('click',e=>{e.stopPropagation();openPreview(row.dataset.id);});
    row.addEventListener('click',e=>{if(e.target.closest('button,input'))return;toggle(row.dataset.id);});
  });updateSelection();
}
function toggle(id){if(state.selected.has(id))state.selected.delete(id);else if(state.selected.size<50)state.selected.add(id);else toast('Select up to 50 items per batch. Run additional items in another batch.');renderCatalog();}
function mosaicReady(env=state.environment){return env?.cli?.available!==false&&env?.cli?.authenticated===true&&env?.cli?.apiReachable===true;}
function codexReady(env=state.environment){return env?.codex?.ready===true;}
function updateSelection(){
  const n=state.selected.size;
  $('selection-total').textContent=n?`${n} selected`:'No components selected';
  $('run-selection').textContent=n?`${countLabel(n,'component')} in this batch`:'Select components to begin';
  $('run-version').textContent=$('version').value||'';
  $('clear-selection').hidden=!n;
  const total=state.filtered.length,checked=state.filtered.filter(i=>state.selected.has(i.id)).length;
  $('select-visible').checked=total>0&&checked===total;$('select-visible').indeterminate=checked>0&&checked<total;
  const ready=mosaicReady()&&codexReady();
  const version=state.environment?.versions?.find(v=>v.id===$('version').value);
  const running=state.job&&['queued','running','cancelling'].includes(state.job.status);
  const workspaceId=$('workspace-id').value.trim();
  $('run').disabled=!(n&&ready&&version?.authoringAvailable&&workspaceId&&$('folder-id').value.trim())||running;
  $('run-readiness').textContent=running?'Batch running. Track progress or stop it in the queue below.':!ready?'Sign in to your Codex and Mosaic accounts, then refresh the connection.':!workspaceId?'Choose a workspace or enter its ID under destination settings.':'Codex processes each item in order and saves outputs and a differences report.';
}
function renderCodexModels(){
  const previous=$('codex-model').value;
  const models=state.environment?.codex?.models||[];
  $('codex-model').innerHTML='<option value="">Environment default</option>'+models.map(m=>`<option value="${escapeHTML(m.model||m.id)}">${escapeHTML(m.displayName||m.model||m.id)}</option>`).join('');
  if(models.some(m=>(m.model||m.id)===previous))$('codex-model').value=previous;
  updateReasoningOptions();
}
function updateReasoningOptions(){
  const model=(state.environment?.codex?.models||[]).find(m=>(m.model||m.id)===$('codex-model').value);
  const supported=model?.supportedReasoningEfforts?.map(v=>typeof v==='string'?v:v.reasoningEffort||v.effort).filter(Boolean)||[];
  for(const o of $('reasoning-effort').options)o.disabled=supported.length>0&&!supported.includes(o.value);
  const selected=$('reasoning-effort').selectedOptions[0];
  if(selected?.disabled)$('reasoning-effort').value=[...$('reasoning-effort').options].find(o=>!o.disabled)?.value||'';
  $('codex-model-note').textContent=model?`${model.displayName||model.model||model.id} · Applies to this batch only.`:'Uses the current Codex default. Tasks receive the source, skill, and your instructions.';
}
async function loadEnvironment(refresh=false){
  $('connection-dot').className='dot loading';$('connection-text').textContent='Checking connections';$('refresh-env').disabled=true;
  try{
    const previousVersion=$('version').value;
    const env=await api('/api/environment'+(refresh?'?refresh=1':''));state.environment=env;
    const cli=env.cli||{},codex=env.codex||{};const ready=mosaicReady(env)&&codexReady(env);
    const versions=env.versions||[];
    const errors=Array.isArray(env.errors)?env.errors:env.errors&&typeof env.errors==='object'?Object.values(env.errors):env.errors?[env.errors]:[];
    const needsAttention=Boolean(env.error)||errors.length>0||!versions.some(v=>v.authoringAvailable);
    $('connection-dot').className='dot '+(ready&&!needsAttention?'good':'bad');$('connection-text').textContent=needsAttention?'Connection needs attention':ready?'Codex + Mosaic ready':!codexReady(env)?'Codex not connected':'Mosaic not connected';
    $('refresh-env').title=[`Codex ${codex.version||''}: ${codexReady(env)?'ready':'not ready'}`,`Mosaic CLI ${cli.version||''}: ${mosaicReady(env)?'ready':'not ready'}`,'Click to refresh'].join(' · ');
    $('executor-status').textContent=`Codex ${codexReady(env)?'ready':'not ready'} · Mosaic CLI ${mosaicReady(env)?'connected':'not connected'}`;
    renderCodexModels();
    $('version').innerHTML=(versions.some(v=>v.authoringAvailable)?'':'<option value="" selected>No available version</option>')+versions.map(v=>`<option value="${escapeHTML(v.id)}" ${v.authoringAvailable?'':'disabled'}>${escapeHTML(v.label||v.id)}${v.authoringAvailable?'':' · '+escapeHTML(v.reason||'Unavailable for new templates')}</option>`).join('');
    const preferred=previousVersion||state.defaults.targetVersion;
    if(versions.some(v=>v.id===preferred&&v.authoringAvailable))$('version').value=preferred;
    else $('version').value=versions.find(v=>v.authoringAvailable)?.id||'';
    versionNote();
    renderWorkspaces(env.workspaces||[]);
    if(env.error||errors.length)error(errorText(env.error,errors));
    else if(!codexReady(env))error(codex.error||codex.reason||'Codex is not ready. Check your local Codex sign-in, then refresh the connection.');
    else if(!mosaicReady(env))error('Mosaic is not ready. Run mosaic login in a terminal, then refresh the connection.');
    else if(!versions.some(v=>v.authoringAvailable))error('No Mosaic version is currently available for authoring. Review the version details and refresh the connection.');
    else error('');
    if(mosaicReady(env)||!$('workspace-id').value.trim())await loadFolders();
  }catch(e){state.environment=null;$('connection-dot').className='dot bad';$('connection-text').textContent='Connection failed';$('executor-status').textContent='Connection check failed';error(e.message);$('version').innerHTML='<option value="">Connect to choose a version</option>';}
  finally{$('refresh-env').disabled=false;updateSelection();}
}
function versionNote(){const v=state.environment?.versions?.find(v=>v.id===$('version').value);$('version-note').textContent=v?.reason||(v?'Uses versions supported by the current Mosaic environment without changing global preferences.':'Refresh the connection to load an available version.');updateSelection();}
function renderWorkspaces(workspaces=state.environment?.workspaces||[]){
  const selectedId=$('workspace-id').value.trim();
  const known=workspaces.some(w=>(w.id||w.workspaceId)===selectedId);
  $('workspace').innerHTML='<option value="">Choose a workspace</option>'+workspaces.map(w=>`<option value="${escapeHTML(w.id||w.workspaceId)}">${escapeHTML(w.name||w.displayName||w.workspaceName||w.id||w.workspaceId)}</option>`).join('')+(selectedId&&!known?`<option value="${escapeHTML(selectedId)}">Entered ID · ${escapeHTML(selectedId)}</option>`:'');
  $('workspace').value=selectedId;
}
let folderSequence=0;
async function loadFolders(){
  const id=$('workspace-id').value.trim();
  const seq=++folderSequence;
  if(!id){$('folder').innerHTML='<option value="">Choose a workspace first</option>';$('folder').disabled=true;$('reload-folders').disabled=true;return;}
  $('folder').disabled=false;$('reload-folders').disabled=true;
  try{const data=await api('/api/folders?workspaceId='+encodeURIComponent(id));if(seq!==folderSequence||id!==$('workspace-id').value.trim())return;
    const folders=data.folders||[];
    $('folder').innerHTML='<option value="">Enter a folder ID</option>'+folders.map(f=>`<option value="${escapeHTML(f.id||f.folderId)}">${escapeHTML(f.path||f.name||f.displayName||f.id)}</option>`).join('');
    $('folder').value=folders.some(f=>(f.id||f.folderId)===$('folder-id').value)?$('folder-id').value:'';
  }catch(e){if(seq===folderSequence)toast('Could not load folders: '+e.message);}
  finally{if(seq===folderSequence)$('reload-folders').disabled=false;}
}
function renderSkills(){
  const data=state.skills,active=data.versions.find(v=>v.id===data.activeId);
  $('header-skill').textContent='v'+(active?.version||'?');$('skill-version').textContent=`v${active?.version||'?'} · Loaded before the run`;
  $('official-skill').href=safeURL(data.officialUrl);
  $('skill-list').innerHTML=data.versions.map(v=>`<div class="skill-item"><span class="mini-icon">S</span><div><strong>Mosaic Gen Workflow v${escapeHTML(v.version)}</strong><small>${escapeHTML(countLabel(v.fileCount,'file'))} · ${escapeHTML(v.source==='project-installed'?'Project installation':v.source)}</small></div>${v.id===data.activeId?'<span class="status-pill">Active</span>':`<button class="secondary activate-skill" data-id="${escapeHTML(v.id)}">Activate</button>`}</div>`).join('');
  $('skill-list').querySelectorAll('.activate-skill').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await api('/api/skills/activate',{method:'POST',body:JSON.stringify({id:b.dataset.id})});state.skills=await api('/api/skills');renderSkills();toast('Version activated. New tasks will use this version.');}catch(e){toast(e.message);}finally{b.disabled=false;}});
}
function showDialog(id){if(!$(id).open)$(id).showModal();}
function openPreview(id){
  const item=state.catalog.find(i=>i.id===id);if(!item)return;state.preview=item;
  $('preview-title').textContent=item.variant||item.name;
  $('preview-subtitle').textContent=[libraryName(item),item.name,item.size,item.width&&item.height?`${item.width} × ${item.height} px`:''].filter(Boolean).join(' / ');
  const path=item.previewPath||`${item.library}.html`;
  const url='/library/'+path.replace(/^\/?library\//,'').replace(/^\//,'');
  $('preview-frame').src=url;$('preview-open').href=url;
  $('preview-help').textContent=item.details?.previewSelectionMode==='controls'?'Finding and applying the selected variant…':'This is the original component page from the current ZIP.';
  $('preview-open').textContent=item.details?.previewSelectionMode==='controls'?'Open default component page ↗':'Open in new tab ↗';
  $('preview-select').textContent=state.selected.has(id)?'Remove from selection':'Add to selection';showDialog('preview-dialog');
}
function syncPreviewControls(){
  const item=state.preview;if(!item)return false;
  try{
    const doc=$('preview-frame').contentDocument;
    const values=item.details?.selectionValues||item.selectionValues||{};
    let matched=0;
    for(const [key,value] of Object.entries(values)){
      const label=[...doc.querySelectorAll('label')].find(l=>l.textContent.trim()===key);
      const el=doc.getElementById('f-'+key)||(label?.htmlFor?doc.getElementById(label.htmlFor):null)||doc.querySelector(`[id$="-${CSS.escape(key)}"]`);
      if(el&&el.tagName==='SELECT'&&[...el.options].some(o=>o.value===String(value))){if(el.value!==String(value)){el.value=String(value);el.dispatchEvent(new Event('change',{bubbles:true}));}matched+=el.value===String(value)?1:0;}
      else if(el?.type==='checkbox'){if(el.checked!==Boolean(value))el.click();matched+=el.checked===Boolean(value)?1:0;}
      else if(el&&['INPUT','TEXTAREA'].includes(el.tagName)&&['string','number'].includes(typeof value)){
        if(el.value!==String(value)){
          const win=$('preview-frame').contentWindow;
          const proto=el.tagName==='TEXTAREA'?win.HTMLTextAreaElement.prototype:win.HTMLInputElement.prototype;
          Object.getOwnPropertyDescriptor(proto,'value').set.call(el,String(value));
          el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
        }
        matched+=el.value===String(value)?1:0;
      }
    }
    return matched===Object.keys(values).length;
  }catch{return false;}
}
function schedulePreviewSync(){
  const id=state.preview?.id;let tries=0;
  const check=()=>{if(state.preview?.id!==id||!$('preview-dialog').open)return;
    if(syncPreviewControls()){$('preview-help').textContent='Selected properties verified on the original component page in the current ZIP.';return;}
    if(++tries<12)setTimeout(check,400);else $('preview-help').textContent='Some properties could not be verified automatically. Check the variant in the source preview controls.';
  };check();
}
async function startRun(){
  $('run').disabled=true;error('');
  const request={selectionIds:[...state.selected],targetVersion:$('version').value,workspaceId:$('workspace-id').value.trim(),folderId:$('folder-id').value.trim(),skillId:state.skills.activeId,namePrefix:$('name-prefix').value,notes:$('notes').value,outputRoot:$('output-root').value,codexModel:$('codex-model').value,reasoningEffort:$('reasoning-effort').value,itemTimeoutSeconds:Number($('item-timeout').value),maxRepairs:Number($('max-repairs').value)};
  try{const job=await api('/api/jobs',{method:'POST',body:JSON.stringify(request)});setJob(job);$('job-panel').scrollIntoView({behavior:'smooth',block:'nearest'});pollJob(job.id);loadHistory(false);}catch(e){error(e.message);updateSelection();}
}
const statuses={queued:'Queued',running:'Running',cancelling:'Stopping',cancelled:'Cancelled',canceled:'Cancelled',failed:'Failed',needs_review:'Needs review',completed:'Completed',complete:'Completed',success:'Completed',partial:'Partially completed',interrupted:'Interrupted',needs_auth:'Sign-in required',blocked:'Action required',needs_source_evidence:'Insufficient source evidence',unsupported_version:'Version unavailable',needs_setup:'CLI setup required',model_unavailable:'Model unavailable',needs_context_reduction:'Source exceeds context limit',timed_out:'Timed out',timeout:'Timed out',not_run:'Not run',not_started:'Not run',skipped:'Not run',pending:'Queued',saved:'Saved, needs review',awaiting_approval:'Waiting for action',needs_tool_update:'Tool update required',repair_limit:'Repair limit reached',needs_recovery:'Recovery required',unsupported_version_pin:'Version not supported here'};
const activeStatuses=new Set(['running','cancelling','awaiting_approval']);
const terminalJobs=new Set(['cancelled','canceled','failed','needs_review','completed','complete','success','partial','interrupted','blocked','needs_setup','needs_auth']);
function statusGroup(status){
  if(['timed_out','timeout'].includes(status))return 'timedOut';
  if(['cancelled','canceled'].includes(status))return 'cancelled';
  if(['not_run','not_started','skipped'].includes(status))return 'notRun';
  if(['queued','pending'].includes(status))return 'waiting';
  if(activeStatuses.has(status))return 'running';
  if(['needs_review','saved'].includes(status))return 'needsReview';
  if(['completed','complete','success'].includes(status))return 'completed';
  return 'failed';
}
function jobItems(job){
  const requested=job.request?.selectionIds||[];
  const items=new Map();
  requested.forEach((id,index)=>items.set(id,{selectionId:id,name:job.selectionNames?.[index],status:terminalJobs.has(job.status)?'not_run':'queued'}));
  let partial=job.partialItems||[];
  if(!Array.isArray(partial))partial=Object.entries(partial).map(([selectionId,item])=>({selectionId,...item}));
  const reported=job.report?.items||job.report?.results||[];
  [...partial,...reported].forEach((item,index)=>{
    const id=item.selectionId||item.id||requested[index]||'item-'+index;
    items.set(id,{...items.get(id),...item,selectionId:id});
  });
  return [...items.values()].map(item=>{if(terminalJobs.has(job.status)&&['queued','pending'].includes(item.status))return {...item,status:'not_run'};if(terminalJobs.has(job.status)&&activeStatuses.has(item.status))return {...item,status:['cancelled','canceled'].includes(job.status)?'cancelled':'interrupted'};return item;});
}
function itemCounts(items){
  const counts={total:items.length,saved:0,completed:0,needsReview:0,failed:0,timedOut:0,cancelled:0,notRun:0,waiting:0,running:0};
  for(const item of items){if(item.templateId||item.url)counts.saved++;counts[statusGroup(item.status)]++;}
  return counts;
}
function countsHTML(items){
  const c=itemCounts(items);
  return `<span>Total <b>${c.total}</b></span><span>Saved <b>${c.saved}</b></span><span>Completed <b>${c.completed}</b></span><span>Needs review <b>${c.needsReview}</b></span><span class="${c.failed?'count-problem':''}">Failed <b>${c.failed}</b></span><span class="${c.timedOut?'count-problem':''}">Timed out <b>${c.timedOut}</b></span><span>Cancelled <b>${c.cancelled}</b></span><span>Not run <b>${c.notRun}</b></span>${c.waiting?`<span>Queued <b>${c.waiting}</b></span>`:''}${c.running?`<span>Running <b>${c.running}</b></span>`:''}`;
}
function elapsedValue(item){
  const start=item.startedAt||item.execution?.startedAt,end=item.finishedAt||item.completedAt||item.execution?.finishedAt;
  if(activeStatuses.has(item.status)&&start){const seconds=(Date.now()-Date.parse(start))/1000;if(Number.isFinite(seconds))return Math.max(0,seconds);}
  const given=item.elapsedSeconds??item.execution?.elapsedSeconds;
  if(typeof given==='number'&&Number.isFinite(given))return Math.max(0,given);
  if(start&&end){const seconds=(Date.parse(end)-Date.parse(start))/1000;if(Number.isFinite(seconds))return Math.max(0,seconds);}
  return null;
}
function durationText(seconds){if(seconds===null||seconds===undefined)return 'Time not recorded';const n=Math.round(seconds);return n<60?`${n} sec`:`${Math.floor(n/60)} min ${n%60} sec`;}
function itemName(item,index){const source=state.catalog.find(i=>i.id===(item.selectionId||item.id));return item.name||item.title||(source?[source.variant||source.name,source.size].filter(Boolean).join(' · '):`Component ${index+1}`);}
function renderJobQueue(job){
  const items=jobItems(job);
  $('job-counts').innerHTML=countsHTML(items);
  $('job-items').innerHTML=items.map((item,index)=>{
    const message=item.error||item.err||item.message||(item.summary?summaryText(item.summary):'');
    const elapsed=elapsedValue(item);
    return `<div class="job-item"><span class="queue-number">${index+1}</span><div class="queue-main"><strong>${escapeHTML(itemName(item,index))}</strong>${message?`<p>${escapeHTML(textValue(message))}</p>`:''}${item.templateId?`<a class="text-link" href="https://mosaic.ai.microsoft.com/templates/${encodeURIComponent(item.templateId)}" target="_blank" rel="noopener">Open saved template ↗</a>`:''}</div><div class="queue-result"><span class="status-pill ${escapeHTML(item.status||'queued')}">${escapeHTML(statuses[item.status]||item.status||'Queued')}</span><small>${elapsed!==null?escapeHTML(durationText(elapsed)):['waiting','notRun'].includes(statusGroup(item.status))?'—':'Time not recorded'}</small></div></div>`;
  }).join('');
}
function progressText(job){
  if(job.report)return summaryText(job.report.summary);
  const event=[...(job.events||[])].reverse().find(e=>e.message&&!['codexEvent','codexLog'].includes(e.type));
  const labels={read_source:'Reading source structure, styles, and assets',read_workflow_skill:'Reading the selected workflow skill',inspect_mosaic_contract:'Looking up Mosaic components and rules',save_draft:'Saving the Mosaic draft',validate_preview:'Checking the saved template and capturing its rendered view',save_report:'Recording the approach and differences'};
  if(event?.type==='tool'){
    if(event.phase==='completed'&&event.success===false)return 'Checks found an issue. Codex is working on a fix.';
    return labels[event.tool]||event.message;
  }
  if(event?.type==='phase')return {'codex-start':'Starting the Codex task for this component','codex-ready':'Codex is building this component','codex-finished':'Component task finished. Preparing the report'}[event.phase]||event.message;
  return event?.message||job.message||'';
}
function setJob(job){
  state.job=job;$('job-panel').hidden=false;$('job-status').textContent=statuses[job.status]||job.status;$('job-status').className='status-pill '+job.status;
  $('job-title').textContent=`${countLabel(job.selectionNames?.length||job.request?.selectionIds?.length||0,'component')} · ${job.request?.targetVersion||''}`;
  $('job-message').textContent=progressText(job);
  const running=['queued','running','cancelling'].includes(job.status);
  $('cancel-job').hidden=!running;$('cancel-job').disabled=job.status==='cancelling';$('show-report').hidden=!job.report;
  renderJobQueue(job);
  const events=job.events||[];
  $('job-events').innerHTML=events.map(e=>`<div class="event"><time>${escapeHTML(e.at?new Date(e.at).toLocaleTimeString('en-US',{hour12:false}):'')}</time><span>${escapeHTML(e.message||(e.item?`${itemName(e.item,0)}: ${statuses[e.item.status]||e.item.status}`:textValue(e)))}</span></div>`).join('');
  $('job-events').scrollTop=$('job-events').scrollHeight;
  const stage=events.at(-1)?.stage||'source';
  document.querySelectorAll('.stages span').forEach((el,i)=>el.classList.toggle('active',job.report?true:i===(stage==='source'?0:stage==='report'?2:1)));
  updateSelection();
}
function pollJob(id){clearTimeout(state.poll);state.poll=setTimeout(async()=>{try{const job=await api('/api/jobs/'+encodeURIComponent(id));setJob(job);if(['queued','running','cancelling'].includes(job.status))pollJob(id);else{loadHistory(false);toast(job.status==='failed'?'Batch finished. Review the error report.':'Batch finished. The report is saved.');}}catch(e){toast(e.message);state.poll=setTimeout(()=>pollJob(id),3000);}},1800);}
async function loadHistory(open=true){
  try{const data=await api('/api/jobs');$('history-count').textContent=data.jobs.length?String(data.jobs.length):'';
    $('history-list').innerHTML=data.jobs.length?data.jobs.map(j=>`<div class="history-item"><div><strong>${escapeHTML(j.selectionNames?.slice(0,2).join(', ')||'Build task')}${j.selectionNames?.length>2?' and more':''}</strong><p>${escapeHTML(formatDate(j.createdAt))} · ${escapeHTML(j.request.targetVersion)} · ${escapeHTML(statuses[j.status]||j.status)}</p></div><button class="secondary history-open" data-id="${escapeHTML(j.id)}">View</button></div>`).join(''):'<div class="empty-state">No tasks yet. Select components to start your first batch.</div>';
    $('history-list').querySelectorAll('.history-open').forEach(b=>b.onclick=async()=>{try{const j=await api('/api/jobs/'+b.dataset.id);$('history-dialog').close();setJob(j);if(j.report)showReport(j);else if(['queued','running','cancelling'].includes(j.status))pollJob(j.id);}catch(e){toast(e.message);}});
    if(open)showDialog('history-dialog');
  }catch(e){toast(e.message);}
}
function reportFile(job,path,label){if(typeof path!=='string'||!path)return '';const relative=path.startsWith(job.directory+'/')?path.slice(job.directory.length+1):path;if(relative.includes('..')||relative.startsWith('/'))return '';return `<a class="text-link" href="/runs/${encodeURIComponent(job.id)}/${relative.split('/').map(encodeURIComponent).join('/')}" target="_blank" rel="noopener">${escapeHTML(label)}</a>`;}
const evidenceLabels={captured:'Screenshot captured','not-captured':'No screenshot captured',pass:'Passed',fail:'Failed',failed:'Failed',exact:'Exact match',approximate:'Approximate match',unsupported:'Not supported by the platform',unverified:'Unverified','source-asset-only':'Source icon reused; host rendering not yet verified','not-tested':'Not tested','not-tested-by-workbench':'Not verified by the workbench',pending:'Awaiting human review',read:'Read','shell-only':'Entry page only; rules not read',unavailable:'Unavailable'};
function evidenceText(value){if(value&&typeof value==='object')return [evidenceLabels[value.status]||value.status,value.message||value.reason].filter(Boolean).join(' · ')||textValue(value);return evidenceLabels[value]||textValue(value);}
function iconSummary(icons){
  if(!icons)return 'No icon matching result recorded';
  if(typeof icons==='string')return icons;
  if(Array.isArray(icons))return icons.map(iconSummary).join('; ');
  return [evidenceText(icons.status||'not-tested'),icons.source?'Source: '+textValue(icons.source).replace(/[，,]?\s*SHA-256\s+[a-f0-9]{64}/ig,''):'',icons.target?'Used: '+textValue(icons.target):'',icons.reason==='Codex reports icon matching separately; the broker has not performed independent icon visual inspection.'?'Icon matching is reported by Codex and has not been independently verified.':icons.reason||''].filter(Boolean).join(' · ');
}
function validationHTML(validation,agent=false){
  const labels={hostScreenshot:'Host screenshot',parity:'Local and remote parity',visual:'Visuals',layout:'Layout',icons:'Icons',media:'Media rendering',schema:'Structure validation',structure:'Structure validation',saved:'Save result',canonical:'Canonical size',responsive:'Responsive behavior',images:'Image loading',interaction:'Interaction',savedVersion:'Saved version',workspace:'Workspace',folder:'Destination folder',readback:'Saved template readback',savedFull:'Full structure validation',preview:'SDL preview',targetHostVisual:agent?'Visual assessment':'Independent visual verification',pointer:'Pointer interaction',keyboard:'Keyboard interaction',userAcceptance:'Human acceptance'};
  const rows=Object.entries(validation).filter(([k])=>labels[k]);
  return rows.length?'<ul class="validation-list">'+rows.map(([k,v])=>`<li>${labels[k]}: ${escapeHTML(evidenceText(v))}</li>`).join('')+'</ul>'+(validation.errors?.length?`<p>${escapeHTML(validation.errors.join('; '))}</p>`:''):'<p>No validation results available.</p>';
}
function executionHTML(item,job){
  const execution=item.execution||{};
  const provider=execution.provider||job.report?.execution?.provider;
  const isCodex=provider==='codex-app-server';
  const rows=[['Executor',isCodex?'Codex · App Server':provider||'No Codex session recorded for this legacy task'],['Duration',durationText(elapsedValue(item))]];
  if(execution.model||job.request?.codexModel)rows.push(['Model',execution.model||job.request.codexModel]);
  const technical=[];
  if(execution.threadId)technical.push(['Codex session ID',execution.threadId]);
  if(execution.turnId)technical.push(['Turn ID',execution.turnId]);
  if(item.iteration!==undefined&&item.iteration!==null)rows.push(['Mosaic iteration',item.iteration]);
  const repairs=item.repairCount??execution.repairs;
  if(repairs!==undefined&&repairs!==null)rows.push(['Repairs',repairs]);
  const finalText=typeof execution.finalText==='string'?execution.finalText.trim():'';
  const excerpt=finalText.length>500?finalText.slice(0,500)+'…':finalText;
  return `<div class="report-section"><h4>Execution</h4><dl class="execution-details">${rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${escapeHTML(value)}</dd></div>`).join('')}</dl>${technical.length?`<details><summary>Session details</summary><dl class="execution-details">${technical.map(([label,value])=>`<div><dt>${label}</dt><dd>${escapeHTML(value)}</dd></div>`).join('')}</dl></details>`:''}${excerpt?`<details><summary>Codex summary</summary><p class="execution-excerpt">${escapeHTML(excerpt)}</p></details>`:''}</div>`;
}
function reportFiles(item){
  const files=Array.isArray(item.localFiles)?item.localFiles:Object.values(item.localFiles||{});
  const traces=[item.execution?.eventsPath,item.execution?.tracePath,item.execution?.traceFile].filter(v=>typeof v==='string');
  const seen=new Set();
  return [...files,...traces].filter(file=>{const path=typeof file==='string'?file:file?.path;if(!path||seen.has(path))return false;seen.add(path);return true;});
}
function visualReviewHTML(item,job){
  const validation=item.validation||{};
  const latest=item.latestValidation;
  const screenshots=reportFiles(item).map(f=>typeof f==='string'?f:f.path).filter(path=>
    /\.(png|jpe?g|webp)$/i.test(path)&&/(?:host[-_]|capture|screenshot)/i.test(path)&&(!latest||path.startsWith(latest+'/'))
  ).filter(path=>reportFile(job,path,'Screenshot'));
  const captured=validation.hostScreenshot==='captured'&&screenshots.length>0;
  const reported=item.agentReportedValidation;
  const hasReport=reported&&typeof reported==='object'&&Object.keys(reported).length>0;
  if(!captured)return `<div class="report-section"><h4>Codex reported checks</h4><p>Visual review is unverified: no matching host screenshot is available for this check.</p>${hasReport?`<details><summary>View Codex claims (unverified)</summary>${validationHTML(reported,true)}</details>`:''}</div>`;
  return `<div class="report-section"><h4>Codex visual review</h4>${hasReport?validationHTML(reported,true):'<p>Screenshot captured; no Codex visual assessment has been recorded.</p>'}<div class="report-links">${screenshots.map((path,index)=>reportFile(job,path,'Host screenshot'+(screenshots.length>1?' '+(index+1):'')+' ↗')).join('')}</div><p class="field-note">These are Codex assessments of the screenshot and execution. They do not replace independent verification, and screenshots alone do not prove interaction works.</p></div>`;
}
function renderReportItem(item,job,index){
  const name=itemName(item,index);
  const refs=item.refs||item.references||[];
  const differences=item.differences||[];
  const validation=item.validation||{};
  const templateURL=item.url||(item.templateId?'https://mosaic.ai.microsoft.com/templates/'+encodeURIComponent(item.templateId):'');
  const referenceList=rows=>Array.isArray(rows)?rows.map(r=>{
    if(typeof r==='string')return `<li>${escapeHTML(r)}</li>`;
    if(!r||typeof r!=='object')return '';
    const title=r.title||r.name||[r.kind,r.component,r.version].filter(Boolean).join(' ')||r.url||'Reference';
    const purpose=r.usedFor||r.purpose;
    const label=r.url?`<a href="${escapeHTML(safeURL(r.url))}" target="_blank" rel="noopener">${escapeHTML(title)}</a>`:r.localFile?reportFile(job,r.localFile,title)||escapeHTML(title):escapeHTML(title);
    return `<li>${label}${r.status?' · '+escapeHTML(evidenceText(r.status)):''}${purpose?' — '+escapeHTML(purpose):''}</li>`;
  }).join(''):'';
  const adopted=Array.isArray(item.agentReportedReferences)?item.agentReportedReferences:[];
  const refsHTML=referenceList(adopted.filter(r=>typeof r==='string'||(typeof r==='object'&&(!r.url||String(r.url).startsWith('https://mosaic.ai.microsoft.com/')))));
  const sourceRefsHTML=referenceList(adopted.filter(r=>typeof r==='object'&&r.url&&!String(r.url).startsWith('https://mosaic.ai.microsoft.com/')));
  const discoveryHTML=referenceList(refs);
  const diffHTML=Array.isArray(differences)&&differences.length?`<table><thead><tr><th>Item</th><th>Source</th><th>Mosaic result</th><th>Reason / impact</th></tr></thead><tbody>${differences.map(d=>typeof d==='string'?`<tr><td colspan="4">${escapeHTML(d)}</td></tr>`:`<tr><td>${escapeHTML(d.area||d.type||'Difference')}</td><td>${escapeHTML(textValue(d.source))}</td><td>${escapeHTML(textValue(d.target??d.actual))}</td><td>${escapeHTML(d.reason||d.description||'Not specified')}</td></tr>`).join('')}</tbody></table>`:'<p>No itemized differences were recorded. This does not establish full fidelity.</p>';
  const icons=item.icons||item.iconMatching;
  const agentIcons=item.agentReportedIcons;
  const hasAgentIcons=typeof agentIcons==='string'?Boolean(agentIcons.trim()):agentIcons&&typeof agentIcons==='object'&&Object.keys(agentIcons).length>0;
  const files=reportFiles(item);
  const components=Array.isArray(item.usedComponents)?item.usedComponents.map(c=>typeof c==='string'?c:[c.name||c.component,c.usedFor||c.purpose].filter(Boolean).join(': ')).join(', '):textValue(item.usedComponents);
  const problem=item.error||item.err;
  return `<article class="report-item"><div class="report-item-head"><h3>${escapeHTML(name)} <span class="status-pill ${escapeHTML(item.status||'')}">${escapeHTML(statuses[item.status]||item.status||'Not checked')}</span></h3>${templateURL?`<a class="secondary" href="${escapeHTML(safeURL(templateURL))}" target="_blank" rel="noopener">Open in Mosaic ↗</a>`:''}</div>${item.summary?`<p class="report-section">${escapeHTML(summaryText(item.summary))}</p>`:''}${problem?`<p class="notice error">${escapeHTML(textValue(problem))}</p>`:''}${item.workflowFailure?`<div class="notice error">Automatic Mosaic scoring did not complete for this legacy task.<details><summary>View legacy workflow details</summary>${escapeHTML(item.workflowFailure)}</details></div>`:''}${executionHTML(item,job)}<div class="report-section"><h4>How it was built</h4><p>${escapeHTML(item.componentSummary||(item.usedComponents?.length?'Components used: '+components:'No component list available for the saved template'))}</p></div><div class="report-section"><h4>References and usage</h4>${refsHTML?'<ul>'+refsHTML+'</ul><p class="field-note">Usage reported during execution. Refer to validation evidence for actual behavior.</p>':'<p>No adopted references recorded. Further verification is needed.</p>'}${sourceRefsHTML?'<details><summary>View library assets used</summary><ul>'+sourceRefsHTML+'</ul></details>':''}${discoveryHTML?'<details><summary>View official reference reads</summary><ul>'+discoveryHTML+'</ul></details>':''}</div><div class="report-section"><h4>Differences from the source</h4>${diffHTML}</div><div class="report-section"><h4>Icon matching</h4><p>${escapeHTML(iconSummary(icons))}</p>${hasAgentIcons?`<p class="field-note">Codex icon choice (not independently verified)</p><p>${escapeHTML(iconSummary(agentIcons))}</p>`:''}</div><details class="report-section"><summary>Validation details and evidence</summary><h4>Tool checks</h4>${validationHTML(validation)}<p class="field-note">Structure, preview, and screenshot results returned by tools. Untested or unverified checks are not passes.</p>${visualReviewHTML(item,job)}<div class="report-links">${files.filter(Boolean).map(f=>reportFile(job,typeof f==='string'?f:f.path,typeof f==='string'?(/codex-events.*\.jsonl$/.test(f)?'Codex execution trace (JSONL)':f.split('/').at(-1)):f.label||f.path)).join('')}</div></details></article>`;
}
function showReport(job=state.job){
  if(!job?.report)return;const report=job.report;
  const codexRun=report.execution?.provider==='codex-app-server'||job.request.codexModel!==undefined||report.items?.some(i=>i.execution?.provider==='codex-app-server');
  $('report-subtitle').textContent=`${codexRun?'Run by Codex':'Legacy task'} · ${job.request.targetVersion} · Skill v${job.skill?.version||'?'} · ${formatDate(job.createdAt)}`;
  const items=jobItems(job);
  $('report-body').innerHTML=`<div class="report-summary">${escapeHTML(summaryText(report.summary))}<div class="job-counts">${countsHTML(items)}</div><p class="field-note">Counts reflect each item’s status. Saved items may still have timed out or contain unresolved differences.</p></div><div class="report-meta"><span>${escapeHTML(statuses[job.status]||job.status)}</span><span>${escapeHTML(job.request.workspaceId)}</span><span>Folder ${escapeHTML(job.request.folderId)}</span>${job.request.itemTimeoutSeconds?`<span>${countLabel(Number(job.request.itemTimeoutSeconds)/60,'minute')} per item · Up to ${countLabel(Number(job.request.maxRepairs??1),'repair')}</span>`:''}</div>${report.limitations?.length?`<div class="report-section"><h4>Limitations</h4><ul>${report.limitations.map(l=>`<li>${escapeHTML(textValue(l))}</li>`).join('')}</ul></div>`:''}${items.map((item,i)=>renderReportItem(item,job,i)).join('')}<div class="report-links">${reportFile(job,'report.json','Full report (JSON)')}${reportFile(job,'request.json','Task settings')}${reportFile(job,'sources.json','Source specifications')}</div><p class="report-output">Local outputs: ${escapeHTML(job.directory)}</p>`;
  showDialog('report-dialog');
}
function bind(){
  document.querySelectorAll('.library-tabs button').forEach(b=>b.onclick=()=>{state.library=b.dataset.library;state.category='all';document.querySelectorAll('.library-tabs button').forEach(x=>x.classList.toggle('active',x===b));renderCategories();renderCatalog();});
  $('search').oninput=e=>{state.search=e.target.value.trim().toLowerCase();renderCatalog();};$('category').onchange=e=>{state.category=e.target.value;renderCatalog();};
  $('select-visible').onchange=()=>{const choose=$('select-visible').checked;if(choose){for(const i of state.filtered){if(state.selected.size>=50)break;state.selected.add(i.id);}if(state.filtered.length>50)toast('Selected the first 50 items. Run the rest in another batch.');}else state.filtered.forEach(i=>state.selected.delete(i.id));renderCatalog();};
  $('clear-selection').onclick=()=>{state.selected.clear();renderCatalog();};$('version').onchange=versionNote;$('codex-model').onchange=updateReasoningOptions;
  $('workspace').onchange=()=>{const id=$('workspace').value;if(id!==$('workspace-id').value.trim())$('folder-id').value='default';$('workspace-id').value=id;loadFolders();updateSelection();};
  $('workspace-id').oninput=()=>{++folderSequence;$('folder-id').value='default';renderWorkspaces();if(!$('workspace-id').value.trim())loadFolders();updateSelection();};$('workspace-id').onchange=loadFolders;
  $('folder').onchange=()=>{if(!$('folder').value)$('destination-details').open=true;if($('folder').value)$('folder-id').value=$('folder').value;updateSelection();};$('folder-id').oninput=updateSelection;
  $('reload-folders').onclick=loadFolders;$('refresh-env').onclick=()=>loadEnvironment(true);$('run').onclick=startRun;
  $('skill-button').onclick=$('manage-skill').onclick=()=>{renderSkills();showDialog('skill-dialog');};
  $('skill-upload').onchange=async e=>{const file=e.target.files[0];if(!file)return;$('skill-import-status').textContent='Checking the version and file references…';try{const result=await api('/api/skills/import',{method:'POST',body:file,headers:{'Content-Type':'application/zip','X-Filename':encodeURIComponent(file.name)}});state.skills=await api('/api/skills');renderSkills();$('skill-import-status').textContent=`v${result.version}: ${result.message}`;}catch(err){$('skill-import-status').textContent=err.message;}e.target.value='';};
  $('history-button').onclick=()=>loadHistory();$('show-report').onclick=()=>showReport();
  $('cancel-job').onclick=async()=>{if(!state.job)return;try{await api('/api/jobs/'+state.job.id+'/cancel',{method:'POST',body:'{}'});$('cancel-job').disabled=true;toast('Stop requested. Saved outputs will be kept.');}catch(e){toast(e.message);}};
  $('preview-select').onclick=()=>{if(state.preview){toggle(state.preview.id);$('preview-select').textContent=state.selected.has(state.preview.id)?'Remove from selection':'Add to selection';}};
  $('preview-frame').onload=schedulePreviewSync;
  document.querySelectorAll('.close-dialog').forEach(b=>b.onclick=()=>b.closest('dialog').close());
}
async function boot(){
  bind();
  try{const data=await api('/api/bootstrap');state.csrf=data.csrf;state.catalog=data.catalog.items;state.defaults=data.defaults;state.skills=data.skill;
    $('catalog-count').textContent=String(state.catalog.length);$('package-name').textContent=data.catalog.package.name||data.catalog.package.path?.split('/').at(-1)||'Local design library';
    $('workspace-id').value=data.defaults.workspaceId||'';$('folder-id').value=data.defaults.folderId||'default';$('output-root').value=data.defaults.outputRoot;
    renderWorkspaces();if(!$('workspace-id').value.trim())loadFolders();
    renderCategories();renderCatalog();renderSkills();loadHistory(false);loadEnvironment();
    const requestedJob=new URLSearchParams(location.search).get('job');
    if(requestedJob||data.activeJobId){const j=await api('/api/jobs/'+encodeURIComponent(requestedJob||data.activeJobId));setJob(j);if(j.report&&requestedJob)showReport(j);else if(['queued','running','cancelling'].includes(j.status))pollJob(j.id);}
  }catch(e){error(e.message);$('catalog').innerHTML='<div class="empty-state">Could not load the design library. Check the ZIP file, then refresh the page.</div>';}
}
boot();
