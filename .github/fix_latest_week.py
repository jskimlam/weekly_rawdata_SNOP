from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old_sync="""async function syncDbWeeks(){try{const r=await gasGet('weeks');const ws=(r.weeks||[]).map(x=>typeof x==='string'?x:x.week_end).filter(Boolean);ws.forEach(addWeekOption);return ws;}catch(e){return [];}}"""
new_sync="""async function syncDbWeeks(){
  const found=new Set();
  try{
    const r=await gasGet('weeks');
    (r.weeks||[]).map(x=>typeof x==='string'?x:x.week_end).filter(w=>/^\\d{4}-\\d{2}-\\d{2}$/.test(String(w||''))).forEach(w=>found.add(w));
  }catch(e){console.warn('weeks 조회 실패',e);}
  try{
    const m=await gasGet('marketPrices');
    const rows=dedupeMarket(m.rows||m.marketPrices||[]).filter(r=>String(r.price_type||'').toLowerCase()!=='latest');
    REMOTE_MARKET=rows;
    rows.map(r=>r.week_end).filter(w=>/^\\d{4}-\\d{2}-\\d{2}$/.test(String(w||''))).forEach(w=>found.add(w));
  }catch(e){console.warn('marketPrices 주차 조회 실패',e);}
  const ws=[...found].sort().reverse();
  ws.forEach(addWeekOption);
  return ws;
}"""
if old_sync not in s:
    raise SystemExit('syncDbWeeks target not found')
s=s.replace(old_sync,new_sync,1)

old_change="""weekSelect.addEventListener('change',()=>{const w=weekSelect.value,local=getLocalWeek(w);if(local){applyData(local,{cache:false});setStatus('empty','로컬 자료 표시');}else loadFromGoogle(w);});"""
new_change="""weekSelect.addEventListener('change',async()=>{const w=weekSelect.value;if(!w)return;await loadFromGoogle(w);});"""
if old_change not in s:
    raise SystemExit('weekSelect change target not found')
s=s.replace(old_change,new_change,1)

old_boot="""    const remoteWeeks=await syncDbWeeks();
    const allWeeks=[...new Set([BASE_WEEK,...localWeeks,...remoteWeeks])].filter(x=>/^\\d{4}-\\d{2}-\\d{2}$/.test(x)).sort().reverse();
    const latest=allWeeks[0]||localLatest;
    refreshWeekSelect(latest);weekSelect.value=latest;
    if(remoteWeeks.includes(latest))await loadFromGoogle(latest);
    else {const local=getLocalWeek(latest);if(local)applyData(local,{cache:false});setStatus('empty','최신 로컬 주차 표시');}"""
new_boot="""    const remoteWeeks=await syncDbWeeks();
    const latest=remoteWeeks[0]||localLatest||BASE_WEEK;
    refreshWeekSelect(latest);weekSelect.value=latest;
    if(remoteWeeks.length)await loadFromGoogle(latest);
    else {const local=getLocalWeek(latest);if(local)applyData(local,{cache:false});setStatus('empty','최신 로컬 주차 표시');}"""
if old_boot not in s:
    raise SystemExit('boot latest target not found')
s=s.replace(old_boot,new_boot,1)

p.write_text(s,encoding='utf-8')
