from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# 1) 1P 월 컬럼: 현재월 + 직전 3개월 (9월 기준 26.09/08/07/06)
s=s.replace("const rollingMonths=[1,2,3,4].map(n=>matrixMonthShift(week,n));","const rollingMonths=[0,1,2,3].map(n=>matrixMonthShift(week,n));")

# 2) Macro bullet 중복 제거
old="""function updateMacro(macro,reports){const box=document.querySelector('#p1 .macro');if(!box)return;const wti=reports.find(x=>x.item==='WTI');const raw=parseJsonSafeSafe(wti?.raw_text);if(raw?.macro_html){box.innerHTML=raw.macro_html;scheduleAutoFit();return;}const lines=normalizeText(macro||wti?.market_commentary||'').split('\\n').map(x=>x.trim()).filter(Boolean);box.querySelector('.head').textContent='[ Macro Issue ]';box.querySelector('.lead').innerHTML=lines.length?'- '+esc(lines[0]):'-';const bs=[...box.querySelectorAll('.bullet')];bs.forEach((b,i)=>{b.textContent=lines[i+1]?'· '+lines[i+1]:'';});scheduleAutoFit();}
"""
new="""function cleanMacroLine(v){return String(v||'').replace(/^(?:\\s*[-·•▪]\\s*)+/,'').trim();}
function normalizeMacroBullets(box){if(!box)return;box.querySelectorAll('.bullet').forEach(b=>{const t=cleanMacroLine(b.textContent);b.textContent=t?'· '+t:'';});}
function updateMacro(macro,reports){const box=document.querySelector('#p1 .macro');if(!box)return;const wti=reports.find(x=>x.item==='WTI');const raw=parseJsonSafeSafe(wti?.raw_text);if(raw?.macro_html){box.innerHTML=raw.macro_html;normalizeMacroBullets(box);scheduleAutoFit();return;}const lines=normalizeText(macro||wti?.market_commentary||'').split('\\n').map(cleanMacroLine).filter(Boolean);box.querySelector('.head').textContent='[ Macro Issue ]';box.querySelector('.lead').innerHTML=lines.length?'- '+esc(lines[0]):'-';const bs=[...box.querySelectorAll('.bullet')];bs.forEach((b,i)=>{b.textContent=lines[i+1]?'· '+lines[i+1]:'';});normalizeMacroBullets(box);scheduleAutoFit();}
"""
if old not in s: raise SystemExit('updateMacro target not found')
s=s.replace(old,new,1)

# 3) 외부 그래프 이미지 표시 CSS
css_target=".chart-controls button:hover{background:#eef3f8}.chart-controls button.active{background:#1f2937;color:#fff;border-color:#1f2937}\n"
css_add=""".chart-controls button:hover{background:#eef3f8}.chart-controls button.active{background:#1f2937;color:#fff;border-color:#1f2937}
.chart-file-input{display:none!important}
.chart-image-layer{position:absolute;left:5px;top:42px;width:calc(100% - 10px);height:calc(100% - 47px);object-fit:contain;object-position:center;background:#fff;z-index:6;display:none}
.chart-card.image-mode .chart-image-layer{display:block}
.chart-card.image-mode svg,.chart-card.image-mode .legend,.chart-card.image-mode .unit,.chart-card.image-mode .bep-note,.chart-card.image-mode .anbd-notes{visibility:hidden}
.chart-card.image-mode .chart-head{z-index:8}.chart-card.image-mode .chart-controls{z-index:10}
"""
if css_target not in s: raise SystemExit('css target not found')
s=s.replace(css_target,css_add,1)

# 4) 적용 데이터가 바뀔 때 주차별 외부 그래프 이미지 복원
apply_old="updateBasis(data.week); updatePriceMatrix(data.week); renderWtiChart(data.week); updateReportRows(data.reports||[],data.week); updateMacro(data.macro||'',data.reports||[]); updateDerivedCharts(data.week); refreshDetailDeltaColors(data.reports||[]);"
apply_new="updateBasis(data.week); updatePriceMatrix(data.week); renderWtiChart(data.week); updateReportRows(data.reports||[],data.week); updateMacro(data.macro||'',data.reports||[]); updateDerivedCharts(data.week); restoreChartImages(data.week); refreshDetailDeltaColors(data.reports||[]);"
if apply_old not in s: raise SystemExit('applyData target not found')
s=s.replace(apply_old,apply_new,1)

# 5) IndexedDB 기반 주차별 외부 그래프 이미지 저장/복원
anchor="const CHART_MODE_KEY='raw_material_chart_modes_v14';\n"
insert="""const CHART_MODE_KEY='raw_material_chart_modes_v14';
const CHART_IMAGE_DB='raw_material_chart_images_v1',CHART_IMAGE_STORE='images';
let CHART_IMAGE_DB_PROMISE=null;
function openChartImageDb(){
  if(CHART_IMAGE_DB_PROMISE)return CHART_IMAGE_DB_PROMISE;
  CHART_IMAGE_DB_PROMISE=new Promise((resolve,reject)=>{const req=indexedDB.open(CHART_IMAGE_DB,1);req.onupgradeneeded=()=>{const db=req.result;if(!db.objectStoreNames.contains(CHART_IMAGE_STORE))db.createObjectStore(CHART_IMAGE_STORE);};req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
  return CHART_IMAGE_DB_PROMISE;
}
async function chartImageGet(key){try{const db=await openChartImageDb();return await new Promise((resolve,reject)=>{const tx=db.transaction(CHART_IMAGE_STORE,'readonly'),req=tx.objectStore(CHART_IMAGE_STORE).get(key);req.onsuccess=()=>resolve(req.result||'');req.onerror=()=>reject(req.error);});}catch(e){console.warn('그래프 이미지 읽기 실패',e);return '';}}
async function chartImagePut(key,data){try{const db=await openChartImageDb();await new Promise((resolve,reject)=>{const tx=db.transaction(CHART_IMAGE_STORE,'readwrite');tx.objectStore(CHART_IMAGE_STORE).put(data,key);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);});return true;}catch(e){console.warn('그래프 이미지 저장 실패',e);return false;}}
function chartImageKey(card,week=CURRENT_WEEK){return `${week}__${chartId(card)}`;}
function ensureChartImageLayer(card){let img=card.querySelector('.chart-image-layer');if(!img){img=document.createElement('img');img.className='chart-image-layer';img.alt=(card.querySelector('.chart-head')?.textContent||'그래프')+' 외부 이미지';card.appendChild(img);}return img;}
function showChartImage(card,data){if(!card||!data)return;const img=ensureChartImageLayer(card);img.src=data;card._externalImageData=data;card.classList.add('image-mode');}
function showNativeChart(card){if(!card)return;card.classList.remove('image-mode');}
async function restoreChartImages(week=CURRENT_WEEK){for(const card of chartCards()){const data=await chartImageGet(chartImageKey(card,week));const img=ensureChartImageLayer(card);if(data){showChartImage(card,data);}else{card._externalImageData='';img.removeAttribute('src');showNativeChart(card);}}}
async function loadExternalChartFile(card,file){if(!file)return;const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.readAsDataURL(file);});const ok=await chartImagePut(chartImageKey(card),data);showChartImage(card,data);toast(ok?'그래프 이미지를 적용하고 이 브라우저에 저장했습니다.':'그래프 이미지를 적용했습니다.');}
"""
if anchor not in s: raise SystemExit('chart mode anchor not found')
s=s.replace(anchor,insert,1)

# 6) 그래프 모드 선택 시 기본 차트로 전환
s=s.replace("function applyChartMode(card,mode,remember=true){\n  const svg=card?.querySelector('svg');if(!svg)return;","function applyChartMode(card,mode,remember=true){\n  const svg=card?.querySelector('svg');if(!svg)return;\n  showNativeChart(card);")

# 7) 그래프 컨트롤에 외부 이미지/기본 차트 버튼 추가
pattern=re.compile(r"function initChartControls\(\)\{.*?\n\}\n\n/\* ---------- 텍스트 자동맞춤",re.S)
m=pattern.search(s)
if not m: raise SystemExit('initChartControls block not found')
new_block="""function initChartControls(){
  chartCards().forEach((card,i)=>{
    const page=card.closest('.report')?.id||'p';card.dataset.chartId=`${page}_${i+1}`;
    if(!card.querySelector('.chart-controls')){
      const ctl=document.createElement('div');ctl.className='chart-controls';ctl.setAttribute('data-export-hide','1');
      [['line','선형'],['bar','막대'],['marker','마커'],['trend','추세']].forEach(([mode,label])=>{const b=document.createElement('button');b.type='button';b.dataset.mode=mode;b.textContent=label;b.title=`그래프를 ${label} 보기로 변경`;b.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();applyChartMode(card,mode,true);});ctl.appendChild(b);});
      const imgBtn=document.createElement('button');imgBtn.type='button';imgBtn.textContent='이미지';imgBtn.title='외부 그래프 이미지 파일 선택/교체';
      const baseBtn=document.createElement('button');baseBtn.type='button';baseBtn.textContent='기본';baseBtn.title='DB 기반 기본 그래프로 복귀';
      const input=document.createElement('input');input.type='file';input.accept='image/png,image/jpeg,image/webp';input.className='chart-file-input';input.setAttribute('data-export-hide','1');
      imgBtn.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();input.click();});
      baseBtn.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();showNativeChart(card);});
      input.addEventListener('change',async()=>{const file=input.files?.[0];if(file)await loadExternalChartFile(card,file);input.value='';});
      ctl.appendChild(imgBtn);ctl.appendChild(baseBtn);card.appendChild(ctl);card.appendChild(input);ensureChartImageLayer(card);
    }
    chartBaseSnapshot(card);
    const mode=chartModeStore[chartId(card)]||card.dataset.chartDefault||(card.classList.contains('anbd-card')?'marker':'line');
    applyChartMode(card,mode,false);
  });
}

/* ---------- 텍스트 자동맞춤"""
s=s[:m.start()]+new_block+s[m.end():]

p.write_text(s,encoding='utf-8')
print('final dashboard patch applied')
