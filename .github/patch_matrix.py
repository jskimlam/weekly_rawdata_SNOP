from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
old='''async function syncDbWeeks(){
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
}
'''
new='''async function syncDbWeeks(){
  const found=new Set();
  try{
    const r=await gasGet('weeks');
    (r.weeks||[]).map(x=>typeof x==='string'?x:x.week_end).filter(w=>/^\\d{4}-\\d{2}-\\d{2}$/.test(String(w||''))).forEach(w=>found.add(w));
  }catch(e){console.warn('weeks 조회 실패',e);}
  try{
    const m=await gasGet('marketPrices');
    const rows=dedupeMarket(m.rows||m.marketPrices||[]).filter(r=>String(r.price_type||'').toLowerCase()!=='latest');
    REMOTE_MARKET=rows;
    rows.filter(r=>String(r.price_type||'').toLowerCase()==='weekly')
      .map(r=>r.week_end).filter(w=>/^\\d{4}-\\d{2}-\\d{2}$/.test(String(w||''))).forEach(w=>found.add(w));
  }catch(e){console.warn('marketPrices 주차 조회 실패',e);}
  const ws=[...found].sort().reverse();
  ws.forEach(addWeekOption);
  return ws;
}
'''
if old not in s:
    raise SystemExit('syncDbWeeks target not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('syncDbWeeks patched')
