'use strict';
const $ = id => document.getElementById(id);
const state = {csrf:'',catalog:[],selected:new Set(),library:'all',search:'',category:'all',skills:null,environment:null,job:null,poll:null,preview:null,defaults:{},filtered:[]};
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL = value => { try { const u=new URL(String(value),location.origin); return ['http:','https:'].includes(u.protocol)?u.href:'#'; } catch {return '#';} };
const textValue = value => typeof value==='string'?value:JSON.stringify(value ?? '未记录');
const summaryText = value => typeof value==='string'?value:value?.message||value?.error||'任务结果已保存，请查看证据和差异。';
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,4200);}
function error(message){$('global-error').textContent=message;$('global-error').hidden=!message;}
async function api(path,options={}){
  const headers={...(options.body&&typeof options.body==='string'?{'Content-Type':'application/json'}:{}),...options.headers};
  if(options.method&&options.method!=='GET')headers['X-Workbench-Token']=state.csrf;
  const response=await fetch(path,{...options,headers});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||`请求失败 (${response.status})`);
  return data;
}
function libraryName(item){return item.libraryName||({'mm-image':'MM Image',aigc:'AIGC',video:'Video'}[item.library]||item.library);}
function visibleItems(){return state.catalog.filter(i=>(state.library==='all'||i.library===state.library)&&(state.category==='all'||(i.componentId||i.category)===state.category)&&(!state.search||[i.name,i.variant,i.size,i.description,i.componentId,libraryName(i)].join(' ').toLowerCase().includes(state.search)));}
function renderCategories(){
  const choices=new Map();
  for(const item of state.catalog.filter(i=>state.library==='all'||i.library===state.library))choices.set(item.componentId||item.category,item.name);
  $('category').innerHTML='<option value="all">所有类型</option>'+[...choices].map(([value,name])=>`<option value="${escapeHTML(value)}">${escapeHTML(name)}</option>`).join('');
  $('category').value=choices.has(state.category)?state.category:'all';state.category=$('category').value;
}
function thumb(item){
  if(item.thumbnail){const url=item.thumbnail.startsWith('/')?item.thumbnail:'/library/'+item.thumbnail;return `<img src="${escapeHTML(safeURL(url))}" alt="" loading="lazy">`;}
  return `<span class="wireframe ${escapeHTML(item.library)}" aria-hidden="true"><i></i><i></i><i></i></span>`;
}
function renderCatalog(){
  const items=visibleItems();state.filtered=items;
  $('filter-count').textContent=`${items.length} 个结果`;
  if(!items.length){$('catalog').innerHTML='<div class="empty-state">没有找到匹配的组件。试试其他名称或尺寸。</div>';updateSelection();return;}
  $('catalog').innerHTML=items.map(i=>`<div class="catalog-row ${state.selected.has(i.id)?'selected':''}" data-id="${escapeHTML(i.id)}"><input class="item-check" type="checkbox" aria-label="选择 ${escapeHTML(i.name+' '+(i.variant||'')+' '+(i.size||''))}" ${state.selected.has(i.id)?'checked':''}><div class="component-thumb">${thumb(i)}</div><div class="row-main"><strong>${escapeHTML(i.variant||i.name)}</strong><small>${escapeHTML(libraryName(i))} / ${escapeHTML(i.name)}${i.variant&&i.variant!==i.name?'':' / '+escapeHTML(i.category||'组件')}</small></div><div class="row-dim"><b>${escapeHTML(i.size||'默认')}</b>${i.width&&i.height?`<br>${escapeHTML(i.width)} × ${escapeHTML(i.height)}`:''}</div><button class="peek-button" aria-label="预览 ${escapeHTML(i.name+' '+(i.variant||''))}">预览</button></div>`).join('');
  $('catalog').querySelectorAll('.catalog-row').forEach(row=>{
    row.querySelector('.item-check').addEventListener('change',()=>toggle(row.dataset.id));
    row.querySelector('.peek-button').addEventListener('click',e=>{e.stopPropagation();openPreview(row.dataset.id);});
    row.addEventListener('click',e=>{if(e.target.closest('button,input'))return;toggle(row.dataset.id);});
  });updateSelection();
}
function toggle(id){if(state.selected.has(id))state.selected.delete(id);else if(state.selected.size<50)state.selected.add(id);else toast('每批最多选择50项，可以分批执行。');renderCatalog();}
function mosaicReady(env=state.environment){return env?.cli?.available!==false&&env?.cli?.authenticated===true&&env?.cli?.apiReachable===true;}
function codexReady(env=state.environment){return env?.codex?.ready===true;}
function updateSelection(){
  const n=state.selected.size;
  $('selection-total').textContent=n?`已选择 ${n} 项`:'未选择组件';
  $('run-selection').textContent=n?`本批 ${n} 个组件`:'先从左侧选择组件';
  $('run-version').textContent=$('version').value||'';
  $('clear-selection').hidden=!n;
  const total=state.filtered.length,checked=state.filtered.filter(i=>state.selected.has(i.id)).length;
  $('select-visible').checked=total>0&&checked===total;$('select-visible').indeterminate=checked>0&&checked<total;
  const ready=mosaicReady()&&codexReady();
  const version=state.environment?.versions?.find(v=>v.id===$('version').value);
  const running=state.job&&['queued','running','cancelling'].includes(state.job.status);
  const workspaceId=$('workspace-id').value.trim();
  $('run').disabled=!(n&&ready&&version?.authoringAvailable&&workspaceId&&$('folder-id').value.trim())||running;
  $('run-readiness').textContent=running?'本批运行中；可在执行队列查看进度或停止。':!ready?'首次使用请登录自己的 Codex 与 Mosaic，再刷新连接。':!workspaceId?'请选择输出工作区，或在目标 ID 中填写自己的工作区。':'Codex 按顺序处理各项，保存成果与差异报告。';
}
function renderCodexModels(){
  const previous=$('codex-model').value;
  const models=state.environment?.codex?.models||[];
  $('codex-model').innerHTML='<option value="">环境默认模型</option>'+models.map(m=>`<option value="${escapeHTML(m.model||m.id)}">${escapeHTML(m.displayName||m.model||m.id)}</option>`).join('');
  if(models.some(m=>(m.model||m.id)===previous))$('codex-model').value=previous;
  updateReasoningOptions();
}
function updateReasoningOptions(){
  const model=(state.environment?.codex?.models||[]).find(m=>(m.model||m.id)===$('codex-model').value);
  const supported=model?.supportedReasoningEfforts?.map(v=>typeof v==='string'?v:v.reasoningEffort||v.effort).filter(Boolean)||[];
  for(const o of $('reasoning-effort').options)o.disabled=supported.length>0&&!supported.includes(o.value);
  const selected=$('reasoning-effort').selectedOptions[0];
  if(selected?.disabled)$('reasoning-effort').value=[...$('reasoning-effort').options].find(o=>!o.disabled)?.value||'';
  $('codex-model-note').textContent=model?`${model.displayName||model.model||model.id} · 设置仅应用于本批任务。`:'使用 Codex 当前默认模型；任务会获得来源、skill 与补充说明。';
}
async function loadEnvironment(refresh=false){
  $('connection-dot').className='dot loading';$('connection-text').textContent='检查连接';$('refresh-env').disabled=true;
  try{
    const previousVersion=$('version').value;
    const env=await api('/api/environment'+(refresh?'?refresh=1':''));state.environment=env;
    const cli=env.cli||{},codex=env.codex||{};const ready=mosaicReady(env)&&codexReady(env);
    $('connection-dot').className='dot '+(ready?'good':'bad');$('connection-text').textContent=ready?'Codex + Mosaic 已就绪':!codexReady(env)?'Codex 待连接':'Mosaic 待连接';
    $('refresh-env').title=[`Codex ${codex.version||''}：${codexReady(env)?'就绪':'未就绪'}`,`Mosaic CLI ${cli.version||''}：${mosaicReady(env)?'就绪':'未就绪'}`,'点击刷新'].join(' · ');
    $('executor-status').textContent=`Codex ${codexReady(env)?'已就绪':'未就绪'} · Mosaic CLI ${mosaicReady(env)?'已连接':'未连接'}`;
    renderCodexModels();
    const versions=env.versions||[];
    $('version').innerHTML=versions.map(v=>`<option value="${escapeHTML(v.id)}" ${v.authoringAvailable?'':'disabled'}>${escapeHTML(v.label||v.id)}${v.authoringAvailable?'':' · '+escapeHTML(v.reason||'当前不可新建')}</option>`).join('');
    const preferred=previousVersion||state.defaults.targetVersion;
    if(versions.some(v=>v.id===preferred&&v.authoringAvailable))$('version').value=preferred;
    else $('version').value=versions.find(v=>v.authoringAvailable)?.id||'';
    versionNote();
    renderWorkspaces(env.workspaces||[]);
    const errors=Array.isArray(env.errors)?env.errors:Object.values(env.errors||{});
    if(env.error||errors.length)error(env.error||errors.map(textValue).join('；'));
    else if(!codexReady(env))error(codex.error||codex.reason||'Codex 尚未就绪，请检查本机 Codex 登录状态后刷新连接。');
    else if(!mosaicReady(env))error('Mosaic 尚未就绪。可在终端运行 mosaic login，完成后点击右上角刷新。');
    else error('');
    if(mosaicReady(env)||!$('workspace-id').value.trim())await loadFolders();
  }catch(e){state.environment=null;$('connection-dot').className='dot bad';$('connection-text').textContent='连接失败';$('executor-status').textContent='连接检查失败';error(e.message);$('version').innerHTML='<option value="">连接后选择版本</option>';}
  finally{$('refresh-env').disabled=false;updateSelection();}
}
function versionNote(){const v=state.environment?.versions?.find(v=>v.id===$('version').value);$('version-note').textContent=v?.reason||'按当前 Mosaic 环境确认可用版本，不修改全局偏好。';updateSelection();}
function renderWorkspaces(workspaces=state.environment?.workspaces||[]){
  const selectedId=$('workspace-id').value.trim();
  const known=workspaces.some(w=>(w.id||w.workspaceId)===selectedId);
  $('workspace').innerHTML='<option value="">请选择输出工作区</option>'+workspaces.map(w=>`<option value="${escapeHTML(w.id||w.workspaceId)}">${escapeHTML(w.name||w.displayName||w.workspaceName||w.id||w.workspaceId)}</option>`).join('')+(selectedId&&!known?`<option value="${escapeHTML(selectedId)}">按 ID 指定 · ${escapeHTML(selectedId)}</option>`:'');
  $('workspace').value=selectedId;
}
let folderSequence=0;
async function loadFolders(){
  const id=$('workspace-id').value.trim();
  const seq=++folderSequence;
  if(!id){$('folder').innerHTML='<option value="">请先选择工作区</option>';$('folder').disabled=true;$('reload-folders').disabled=true;return;}
  $('folder').disabled=false;$('reload-folders').disabled=true;
  try{const data=await api('/api/folders?workspaceId='+encodeURIComponent(id));if(seq!==folderSequence||id!==$('workspace-id').value.trim())return;
    const folders=data.folders||[];
    $('folder').innerHTML='<option value="">手动填写文件夹 ID</option>'+folders.map(f=>`<option value="${escapeHTML(f.id||f.folderId)}">${escapeHTML(f.path||f.name||f.displayName||f.id)}</option>`).join('');
    $('folder').value=folders.some(f=>(f.id||f.folderId)===$('folder-id').value)?$('folder-id').value:'';
  }catch(e){if(seq===folderSequence)toast('文件夹读取失败：'+e.message);}
  finally{if(seq===folderSequence)$('reload-folders').disabled=false;}
}
function renderSkills(){
  const data=state.skills,active=data.versions.find(v=>v.id===data.activeId);
  $('header-skill').textContent='v'+(active?.version||'?');$('skill-version').textContent=`v${active?.version||'?'} · 本次运行前加载`;
  $('official-skill').href=safeURL(data.officialUrl);
  $('skill-list').innerHTML=data.versions.map(v=>`<div class="skill-item"><span class="mini-icon">S</span><div><strong>Mosaic Gen Workflow v${escapeHTML(v.version)}</strong><small>${escapeHTML(v.fileCount)} 个文件 · ${escapeHTML(v.source==='project-installed'?'项目已安装版本':v.source)}</small></div>${v.id===data.activeId?'<span class="status-pill">当前使用</span>':`<button class="secondary activate-skill" data-id="${escapeHTML(v.id)}">启用</button>`}</div>`).join('');
  $('skill-list').querySelectorAll('.activate-skill').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await api('/api/skills/activate',{method:'POST',body:JSON.stringify({id:b.dataset.id})});state.skills=await api('/api/skills');renderSkills();toast('已切换，新任务将使用此版本。');}catch(e){toast(e.message);}finally{b.disabled=false;}});
}
function showDialog(id){if(!$(id).open)$(id).showModal();}
function openPreview(id){
  const item=state.catalog.find(i=>i.id===id);if(!item)return;state.preview=item;
  $('preview-title').textContent=item.variant||item.name;
  $('preview-subtitle').textContent=[libraryName(item),item.name,item.size,item.width&&item.height?`${item.width} × ${item.height} px`:''].filter(Boolean).join(' / ');
  const path=item.previewPath||`${item.library}.html`;
  const url='/library/'+path.replace(/^\/?library\//,'').replace(/^\//,'');
  $('preview-frame').src=url;$('preview-open').href=url;
  $('preview-help').textContent=item.details?.previewSelectionMode==='controls'?'正在定位并同步所选变体…':'来源为当前 ZIP 中的原始组件页面。';
  $('preview-open').textContent=item.details?.previewSelectionMode==='controls'?'打开组件页（默认配置） ↗':'独立打开 ↗';
  $('preview-select').textContent=state.selected.has(id)?'移出选择':'加入选择';showDialog('preview-dialog');
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
    if(syncPreviewControls()){$('preview-help').textContent='已核对所选属性。来源为当前 ZIP 中的原始组件页面。';return;}
    if(++tries<12)setTimeout(check,400);else $('preview-help').textContent='未能自动核对全部属性，请在原始预览右侧检查当前变体。';
  };check();
}
async function startRun(){
  $('run').disabled=true;error('');
  const request={selectionIds:[...state.selected],targetVersion:$('version').value,workspaceId:$('workspace-id').value.trim(),folderId:$('folder-id').value.trim(),skillId:state.skills.activeId,namePrefix:$('name-prefix').value,notes:$('notes').value,outputRoot:$('output-root').value,codexModel:$('codex-model').value,reasoningEffort:$('reasoning-effort').value,itemTimeoutSeconds:Number($('item-timeout').value),maxRepairs:Number($('max-repairs').value)};
  try{const job=await api('/api/jobs',{method:'POST',body:JSON.stringify(request)});setJob(job);$('job-panel').scrollIntoView({behavior:'smooth',block:'nearest'});pollJob(job.id);loadHistory(false);}catch(e){error(e.message);updateSelection();}
}
const statuses={queued:'排队中',running:'执行中',cancelling:'正在停止',cancelled:'已取消',canceled:'已取消',failed:'失败',needs_review:'待审阅',completed:'已完成',complete:'已完成',success:'已完成',partial:'部分完成',interrupted:'已中断',needs_auth:'需要登录',blocked:'需要处理',needs_source_evidence:'来源不足',unsupported_version:'版本不可用',needs_setup:'需要安装 CLI',model_unavailable:'模型不可用',needs_context_reduction:'来源规格过大',timed_out:'超时',timeout:'超时',not_run:'未执行',not_started:'未执行',skipped:'未执行',pending:'排队中',saved:'已保存待审阅',awaiting_approval:'等待处理',needs_tool_update:'需要更新工具',repair_limit:'达到修复上限',needs_recovery:'需要恢复任务',unsupported_version_pin:'当前环境不支持此版本'};
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
  return `<span>共 <b>${c.total}</b> 项</span><span>已保存 <b>${c.saved}</b></span><span>已完成 <b>${c.completed}</b></span><span>待审阅 <b>${c.needsReview}</b></span><span class="${c.failed?'count-problem':''}">失败 <b>${c.failed}</b></span><span class="${c.timedOut?'count-problem':''}">超时 <b>${c.timedOut}</b></span><span>取消 <b>${c.cancelled}</b></span><span>未执行 <b>${c.notRun}</b></span>${c.waiting?`<span>排队 <b>${c.waiting}</b></span>`:''}${c.running?`<span>执行中 <b>${c.running}</b></span>`:''}`;
}
function elapsedValue(item){
  const start=item.startedAt||item.execution?.startedAt,end=item.finishedAt||item.completedAt||item.execution?.finishedAt;
  if(activeStatuses.has(item.status)&&start){const seconds=(Date.now()-Date.parse(start))/1000;if(Number.isFinite(seconds))return Math.max(0,seconds);}
  const given=item.elapsedSeconds??item.execution?.elapsedSeconds;
  if(typeof given==='number'&&Number.isFinite(given))return Math.max(0,given);
  if(start&&end){const seconds=(Date.parse(end)-Date.parse(start))/1000;if(Number.isFinite(seconds))return Math.max(0,seconds);}
  return null;
}
function durationText(seconds){if(seconds===null||seconds===undefined)return '耗时未记录';const n=Math.round(seconds);return n<60?`${n} 秒`:`${Math.floor(n/60)} 分 ${n%60} 秒`;}
function itemName(item,index){const source=state.catalog.find(i=>i.id===(item.selectionId||item.id));return item.name||item.title||(source?[source.variant||source.name,source.size].filter(Boolean).join(' · '):`组件 ${index+1}`);}
function renderJobQueue(job){
  const items=jobItems(job);
  $('job-counts').innerHTML=countsHTML(items);
  $('job-items').innerHTML=items.map((item,index)=>{
    const message=item.error||item.err||item.message||(item.summary?summaryText(item.summary):'');
    const elapsed=elapsedValue(item);
    return `<div class="job-item"><span class="queue-number">${index+1}</span><div class="queue-main"><strong>${escapeHTML(itemName(item,index))}</strong>${message?`<p>${escapeHTML(textValue(message))}</p>`:''}${item.templateId?`<a class="text-link" href="https://mosaic.ai.microsoft.com/templates/${encodeURIComponent(item.templateId)}" target="_blank" rel="noopener">已保存模板 ↗</a>`:''}</div><div class="queue-result"><span class="status-pill ${escapeHTML(item.status||'queued')}">${escapeHTML(statuses[item.status]||item.status||'排队中')}</span><small>${elapsed!==null?escapeHTML(durationText(elapsed)):['waiting','notRun'].includes(statusGroup(item.status))?'—':'耗时未记录'}</small></div></div>`;
  }).join('');
}
function progressText(job){
  if(job.report)return summaryText(job.report.summary);
  const event=[...(job.events||[])].reverse().find(e=>e.message&&!['codexEvent','codexLog'].includes(e.type));
  const labels={read_source:'读取原稿的结构、样式与资源',read_workflow_skill:'读取本次选定的工作流规范',inspect_mosaic_contract:'查找 Mosaic 原生组件与规则',save_draft:'保存 Mosaic 草稿',validate_preview:'核对保存结果并取得实际画面',save_report:'记录还原方式和差异'};
  if(event?.type==='tool'){
    if(event.phase==='completed'&&event.success===false)return '检查发现需要修正的问题，Codex 正在处理。';
    return labels[event.tool]||event.message;
  }
  if(event?.type==='phase')return {'codex-start':'启动当前组件的 Codex 任务','codex-ready':'Codex 正在还原当前组件','codex-finished':'当前组件执行结束，正在整理报告'}[event.phase]||event.message;
  return event?.message||job.message||'';
}
function setJob(job){
  state.job=job;$('job-panel').hidden=false;$('job-status').textContent=statuses[job.status]||job.status;$('job-status').className='status-pill '+job.status;
  $('job-title').textContent=`${job.selectionNames?.length||job.request?.selectionIds?.length||0} 项组件 · ${job.request?.targetVersion||''}`;
  $('job-message').textContent=progressText(job);
  const running=['queued','running','cancelling'].includes(job.status);
  $('cancel-job').hidden=!running;$('cancel-job').disabled=job.status==='cancelling';$('show-report').hidden=!job.report;
  renderJobQueue(job);
  const events=job.events||[];
  $('job-events').innerHTML=events.map(e=>`<div class="event"><time>${escapeHTML(e.at?new Date(e.at).toLocaleTimeString('zh-CN',{hour12:false}):'')}</time><span>${escapeHTML(e.message||(e.item?`${itemName(e.item,0)}：${statuses[e.item.status]||e.item.status}`:textValue(e)))}</span></div>`).join('');
  $('job-events').scrollTop=$('job-events').scrollHeight;
  const stage=events.at(-1)?.stage||'source';
  document.querySelectorAll('.stages span').forEach((el,i)=>el.classList.toggle('active',job.report?true:i===(stage==='source'?0:stage==='report'?2:1)));
  updateSelection();
}
function pollJob(id){clearTimeout(state.poll);state.poll=setTimeout(async()=>{try{const job=await api('/api/jobs/'+encodeURIComponent(id));setJob(job);if(['queued','running','cancelling'].includes(job.status))pollJob(id);else{loadHistory(false);toast(job.status==='failed'?'任务已结束，请查看错误报告。':'任务已结束，报告已保存。');}}catch(e){toast(e.message);state.poll=setTimeout(()=>pollJob(id),3000);}},1800);}
async function loadHistory(open=true){
  try{const data=await api('/api/jobs');$('history-count').textContent=data.jobs.length?String(data.jobs.length):'';
    $('history-list').innerHTML=data.jobs.length?data.jobs.map(j=>`<div class="history-item"><div><strong>${escapeHTML(j.selectionNames?.slice(0,2).join('、')||'还原任务')}${j.selectionNames?.length>2?' 等':''}</strong><p>${escapeHTML(new Date(j.createdAt).toLocaleString('zh-CN'))} · ${escapeHTML(j.request.targetVersion)} · ${escapeHTML(statuses[j.status]||j.status)}</p></div><button class="secondary history-open" data-id="${escapeHTML(j.id)}">查看</button></div>`).join(''):'<div class="empty-state">还没有任务。选好组件后，开始第一批还原。</div>';
    $('history-list').querySelectorAll('.history-open').forEach(b=>b.onclick=async()=>{try{const j=await api('/api/jobs/'+b.dataset.id);$('history-dialog').close();setJob(j);if(j.report)showReport(j);else if(['queued','running','cancelling'].includes(j.status))pollJob(j.id);}catch(e){toast(e.message);}});
    if(open)showDialog('history-dialog');
  }catch(e){toast(e.message);}
}
function reportFile(job,path,label){if(typeof path!=='string'||!path)return '';const relative=path.startsWith(job.directory+'/')?path.slice(job.directory.length+1):path;if(relative.includes('..')||relative.startsWith('/'))return '';return `<a class="text-link" href="/runs/${encodeURIComponent(job.id)}/${relative.split('/').map(encodeURIComponent).join('/')}" target="_blank" rel="noopener">${escapeHTML(label)}</a>`;}
const evidenceLabels={captured:'已取得截图','not-captured':'未取得截图',pass:'通过',fail:'未通过',failed:'未通过',exact:'精确匹配',approximate:'近似匹配',unsupported:'平台暂不支持',unverified:'未确认','source-asset-only':'已复用源图标，未完成宿主验收','not-tested':'未测试','not-tested-by-workbench':'工作台未验证',pending:'待人工审阅',read:'已读取','shell-only':'仅访问入口，未读取规则',unavailable:'未取得'};
function evidenceText(value){if(value&&typeof value==='object')return [evidenceLabels[value.status]||value.status,value.message||value.reason].filter(Boolean).join(' · ')||textValue(value);return evidenceLabels[value]||textValue(value);}
function iconSummary(icons){
  if(!icons)return '未记录图标匹配结果';
  if(typeof icons==='string')return icons;
  if(Array.isArray(icons))return icons.map(iconSummary).join('；');
  return [evidenceText(icons.status||'not-tested'),icons.source?'原稿：'+textValue(icons.source).replace(/[，,]?\s*SHA-256\s+[a-f0-9]{64}/ig,''):'',icons.target?'采用：'+textValue(icons.target):'',icons.reason==='Codex reports icon matching separately; the broker has not performed independent icon visual inspection.'?'图标由 Codex 对照截图检查，尚未经独立验收。':icons.reason||''].filter(Boolean).join(' · ');
}
function validationHTML(validation,agent=false){
  const labels={hostScreenshot:'宿主截图',parity:'本地与远端一致性',visual:'画面',layout:'布局',icons:'图标',media:'媒体显示',schema:'结构校验',structure:'结构校验',saved:'保存结果',canonical:'标准尺寸',responsive:'响应式',images:'图片加载',interaction:'交互',savedVersion:'保存版本',workspace:'Workspace',folder:'目标文件夹',readback:'保存回读',savedFull:'完整结构校验',preview:'SDL 预览',targetHostVisual:agent?'画面判断':'独立画面验收',pointer:'点击行为',keyboard:'键盘操作',userAcceptance:'人工验收'};
  const rows=Object.entries(validation).filter(([k])=>labels[k]);
  return rows.length?'<ul class="validation-list">'+rows.map(([k,v])=>`<li>${labels[k]}：${escapeHTML(evidenceText(v))}</li>`).join('')+'</ul>'+(validation.errors?.length?`<p>${escapeHTML(validation.errors.join('；'))}</p>`:''):'<p>未取得验证结果。</p>';
}
function executionHTML(item,job){
  const execution=item.execution||{};
  const provider=execution.provider||job.report?.execution?.provider;
  const isCodex=provider==='codex-app-server';
  const rows=[['执行者',isCodex?'Codex · App Server':provider||'旧任务未记录 Codex 执行会话'],['本项耗时',durationText(elapsedValue(item))]];
  if(execution.model||job.request?.codexModel)rows.push(['模型',execution.model||job.request.codexModel]);
  const technical=[];
  if(execution.threadId)technical.push(['Codex 会话 ID',execution.threadId]);
  if(execution.turnId)technical.push(['执行轮次 ID',execution.turnId]);
  if(item.iteration!==undefined&&item.iteration!==null)rows.push(['Mosaic 工作迭代',item.iteration]);
  const repairs=item.repairCount??execution.repairs;
  if(repairs!==undefined&&repairs!==null)rows.push(['修复次数',repairs]);
  const finalText=typeof execution.finalText==='string'?execution.finalText.trim():'';
  const excerpt=finalText.length>500?finalText.slice(0,500)+'…':finalText;
  return `<div class="report-section"><h4>执行记录</h4><dl class="execution-details">${rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${escapeHTML(value)}</dd></div>`).join('')}</dl>${technical.length?`<details><summary>执行会话详情</summary><dl class="execution-details">${technical.map(([label,value])=>`<div><dt>${label}</dt><dd>${escapeHTML(value)}</dd></div>`).join('')}</dl></details>`:''}${excerpt?`<details><summary>Codex 执行摘要</summary><p class="execution-excerpt">${escapeHTML(excerpt)}</p></details>`:''}</div>`;
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
  ).filter(path=>reportFile(job,path,'截图'));
  const captured=validation.hostScreenshot==='captured'&&screenshots.length>0;
  const reported=item.agentReportedValidation;
  const hasReport=reported&&typeof reported==='object'&&Object.keys(reported).length>0;
  if(!captured)return `<div class="report-section"><h4>Codex 检查声明</h4><p>画面审阅未确认：未取得与本次检查对应的宿主截图证据。</p>${hasReport?`<details><summary>查看 Codex 声明（未确认）</summary>${validationHTML(reported,true)}</details>`:''}</div>`;
  return `<div class="report-section"><h4>Codex 画面审阅</h4>${hasReport?validationHTML(reported,true):'<p>已取得截图，尚未记录 Codex 的画面判断。</p>'}<div class="report-links">${screenshots.map((path,index)=>reportFile(job,path,'宿主截图'+(screenshots.length>1?' '+(index+1):'')+' ↗')).join('')}</div><p class="field-note">以上为 Codex 对截图与执行过程的判断，不代替独立验收；截图本身不证明交互通过。</p></div>`;
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
    const title=r.title||r.name||[r.kind,r.component,r.version].filter(Boolean).join(' ')||r.url||'参考资料';
    const purpose=r.usedFor||r.purpose;
    const label=r.url?`<a href="${escapeHTML(safeURL(r.url))}" target="_blank" rel="noopener">${escapeHTML(title)}</a>`:r.localFile?reportFile(job,r.localFile,title)||escapeHTML(title):escapeHTML(title);
    return `<li>${label}${r.status?' · '+escapeHTML(evidenceText(r.status)):''}${purpose?' — '+escapeHTML(purpose):''}</li>`;
  }).join(''):'';
  const adopted=Array.isArray(item.agentReportedReferences)?item.agentReportedReferences:[];
  const refsHTML=referenceList(adopted.filter(r=>typeof r==='string'||(typeof r==='object'&&(!r.url||String(r.url).startsWith('https://mosaic.ai.microsoft.com/')))));
  const sourceRefsHTML=referenceList(adopted.filter(r=>typeof r==='object'&&r.url&&!String(r.url).startsWith('https://mosaic.ai.microsoft.com/')));
  const discoveryHTML=referenceList(refs);
  const diffHTML=Array.isArray(differences)&&differences.length?`<table><thead><tr><th>项目</th><th>原稿</th><th>Mosaic 结果</th><th>原因 / 影响</th></tr></thead><tbody>${differences.map(d=>typeof d==='string'?`<tr><td colspan="4">${escapeHTML(d)}</td></tr>`:`<tr><td>${escapeHTML(d.area||d.type||'差异')}</td><td>${escapeHTML(textValue(d.source))}</td><td>${escapeHTML(textValue(d.target??d.actual))}</td><td>${escapeHTML(d.reason||d.description||'未说明')}</td></tr>`).join('')}</tbody></table>`:'<p>未提供逐项差异证据；不代表已完全还原。</p>';
  const icons=item.icons||item.iconMatching;
  const agentIcons=item.agentReportedIcons;
  const hasAgentIcons=typeof agentIcons==='string'?Boolean(agentIcons.trim()):agentIcons&&typeof agentIcons==='object'&&Object.keys(agentIcons).length>0;
  const files=reportFiles(item);
  const components=Array.isArray(item.usedComponents)?item.usedComponents.map(c=>typeof c==='string'?c:[c.name||c.component,c.usedFor||c.purpose].filter(Boolean).join('：')).join('、'):textValue(item.usedComponents);
  const problem=item.error||item.err;
  return `<article class="report-item"><div class="report-item-head"><h3>${escapeHTML(name)} <span class="status-pill ${escapeHTML(item.status||'')}">${escapeHTML(statuses[item.status]||item.status||'待检查')}</span></h3>${templateURL?`<a class="secondary" href="${escapeHTML(safeURL(templateURL))}" target="_blank" rel="noopener">打开 Mosaic ↗</a>`:''}</div>${item.summary?`<p class="report-section">${escapeHTML(summaryText(item.summary))}</p>`:''}${problem?`<p class="notice error">${escapeHTML(textValue(problem))}</p>`:''}${item.workflowFailure?`<div class="notice error">旧任务的 Mosaic 自动评分未完成。<details><summary>查看旧工作流记录</summary>${escapeHTML(item.workflowFailure)}</details></div>`:''}${executionHTML(item,job)}<div class="report-section"><h4>实际拼装方式</h4><p>${escapeHTML(item.componentSummary||(item.usedComponents?.length?'采用组件：'+components:'尚未取得保存后的组件清单'))}</p></div><div class="report-section"><h4>参考与采用方式</h4>${refsHTML?'<ul>'+refsHTML+'</ul><p class="field-note">执行记录中的采用说明；实际表现以验证证据为准。</p>':'<p>未记录实际采用的参考，需继续核验。</p>'}${sourceRefsHTML?'<details><summary>查看所用 Library 素材</summary><ul>'+sourceRefsHTML+'</ul></details>':''}${discoveryHTML?'<details><summary>查看官方资料读取记录</summary><ul>'+discoveryHTML+'</ul></details>':''}</div><div class="report-section"><h4>与原稿的差异</h4>${diffHTML}</div><div class="report-section"><h4>图标匹配</h4><p>${escapeHTML(iconSummary(icons))}</p>${hasAgentIcons?`<p class="field-note">Codex 图标选择说明（未独立验收）</p><p>${escapeHTML(iconSummary(agentIcons))}</p>`:''}</div><details class="report-section"><summary>验证细节与执行证据</summary><h4>程序检查</h4>${validationHTML(validation)}<p class="field-note">由工具返回的结构、预览与截图结果；未测试或未确认不计为通过。</p>${visualReviewHTML(item,job)}<div class="report-links">${files.filter(Boolean).map(f=>reportFile(job,typeof f==='string'?f:f.path,typeof f==='string'?(/codex-events.*\.jsonl$/.test(f)?'Codex 执行轨迹 JSONL':f.split('/').at(-1)):f.label||f.path)).join('')}</div></details></article>`;
}
function showReport(job=state.job){
  if(!job?.report)return;const report=job.report;
  const codexRun=report.execution?.provider==='codex-app-server'||job.request.codexModel!==undefined||report.items?.some(i=>i.execution?.provider==='codex-app-server');
  $('report-subtitle').textContent=`${codexRun?'Codex 执行':'历史任务'} · ${job.request.targetVersion} · Skill v${job.skill?.version||'?'} · ${new Date(job.createdAt).toLocaleString('zh-CN')}`;
  const items=jobItems(job);
  $('report-body').innerHTML=`<div class="report-summary">${escapeHTML(summaryText(report.summary))}<div class="job-counts">${countsHTML(items)}</div><p class="field-note">按每项实际状态汇总；已保存项仍可能超时或存在未实现的差异。</p></div><div class="report-meta"><span>${escapeHTML(statuses[job.status]||job.status)}</span><span>${escapeHTML(job.request.workspaceId)}</span><span>文件夹 ${escapeHTML(job.request.folderId)}</span>${job.request.itemTimeoutSeconds?`<span>每项最多 ${Number(job.request.itemTimeoutSeconds)/60} 分钟 · 最多修复 ${Number(job.request.maxRepairs??1)} 次</span>`:''}</div>${report.limitations?.length?`<div class="report-section"><h4>本轮限制</h4><ul>${report.limitations.map(l=>`<li>${escapeHTML(textValue(l))}</li>`).join('')}</ul></div>`:''}${items.map((item,i)=>renderReportItem(item,job,i)).join('')}<div class="report-links">${reportFile(job,'report.json','完整报告 JSON')}${reportFile(job,'request.json','任务配置')}${reportFile(job,'sources.json','来源规格')}</div><p class="report-output">本地成果：${escapeHTML(job.directory)}</p>`;
  showDialog('report-dialog');
}
function bind(){
  document.querySelectorAll('.library-tabs button').forEach(b=>b.onclick=()=>{state.library=b.dataset.library;state.category='all';document.querySelectorAll('.library-tabs button').forEach(x=>x.classList.toggle('active',x===b));renderCategories();renderCatalog();});
  $('search').oninput=e=>{state.search=e.target.value.trim().toLowerCase();renderCatalog();};$('category').onchange=e=>{state.category=e.target.value;renderCatalog();};
  $('select-visible').onchange=()=>{const choose=$('select-visible').checked;if(choose){for(const i of state.filtered){if(state.selected.size>=50)break;state.selected.add(i.id);}if(state.filtered.length>50)toast('已选择前50项，其余可分批执行。');}else state.filtered.forEach(i=>state.selected.delete(i.id));renderCatalog();};
  $('clear-selection').onclick=()=>{state.selected.clear();renderCatalog();};$('version').onchange=versionNote;$('codex-model').onchange=updateReasoningOptions;
  $('workspace').onchange=()=>{const id=$('workspace').value;if(id!==$('workspace-id').value.trim())$('folder-id').value='default';$('workspace-id').value=id;loadFolders();updateSelection();};
  $('workspace-id').oninput=()=>{++folderSequence;$('folder-id').value='default';renderWorkspaces();if(!$('workspace-id').value.trim())loadFolders();updateSelection();};$('workspace-id').onchange=loadFolders;
  $('folder').onchange=()=>{if(!$('folder').value)$('destination-details').open=true;if($('folder').value)$('folder-id').value=$('folder').value;updateSelection();};$('folder-id').oninput=updateSelection;
  $('reload-folders').onclick=loadFolders;$('refresh-env').onclick=()=>loadEnvironment(true);$('run').onclick=startRun;
  $('skill-button').onclick=$('manage-skill').onclick=()=>{renderSkills();showDialog('skill-dialog');};
  $('skill-upload').onchange=async e=>{const file=e.target.files[0];if(!file)return;$('skill-import-status').textContent='正在检查版本和文件引用…';try{const result=await api('/api/skills/import',{method:'POST',body:file,headers:{'Content-Type':'application/zip','X-Filename':encodeURIComponent(file.name)}});state.skills=await api('/api/skills');renderSkills();$('skill-import-status').textContent=`v${result.version}：${result.message}`;}catch(err){$('skill-import-status').textContent=err.message;}e.target.value='';};
  $('history-button').onclick=()=>loadHistory();$('show-report').onclick=()=>showReport();
  $('cancel-job').onclick=async()=>{if(!state.job)return;try{await api('/api/jobs/'+state.job.id+'/cancel',{method:'POST',body:'{}'});$('cancel-job').disabled=true;toast('已请求停止。已经保存的成果会保留。');}catch(e){toast(e.message);}};
  $('preview-select').onclick=()=>{if(state.preview){toggle(state.preview.id);$('preview-select').textContent=state.selected.has(state.preview.id)?'移出选择':'加入选择';}};
  $('preview-frame').onload=schedulePreviewSync;
  document.querySelectorAll('.close-dialog').forEach(b=>b.onclick=()=>b.closest('dialog').close());
}
async function boot(){
  bind();
  try{const data=await api('/api/bootstrap');state.csrf=data.csrf;state.catalog=data.catalog.items;state.defaults=data.defaults;state.skills=data.skill;
    $('catalog-count').textContent=String(state.catalog.length);$('package-name').textContent=data.catalog.package.name||data.catalog.package.path?.split('/').at(-1)||'本地设计库';
    $('workspace-id').value=data.defaults.workspaceId||'';$('folder-id').value=data.defaults.folderId||'default';$('output-root').value=data.defaults.outputRoot;
    renderWorkspaces();if(!$('workspace-id').value.trim())loadFolders();
    renderCategories();renderCatalog();renderSkills();loadHistory(false);loadEnvironment();
    const requestedJob=new URLSearchParams(location.search).get('job');
    if(requestedJob||data.activeJobId){const j=await api('/api/jobs/'+encodeURIComponent(requestedJob||data.activeJobId));setJob(j);if(j.report&&requestedJob)showReport(j);else if(['queued','running','cancelling'].includes(j.status))pollJob(j.id);}
  }catch(e){error(e.message);$('catalog').innerHTML='<div class="empty-state">设计库读取失败。请检查 ZIP 文件后刷新页面。</div>';}
}
boot();
