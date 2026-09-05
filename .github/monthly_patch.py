from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
old="""function matrixMonthAverage(item,year,month){
  const ref=matrixCaptureReference()[item]?.months?.[matrixYmKey(year,month)];
  if(ref!==null&&ref!==undefined&&Number.isFinite(Number(ref)))return Number(ref);
  return matrixObservedMonthAverage(item,year,month,2);
}"""
new="""function matrixMonthAverage(item,year,month){
  // 과거 월평균은 market_price의 monthly 행을 최우선 사용
  const ym=matrixYmKey(year,month);
  const monthly=ALL_MARKET.filter(r=>r.item===item&&String(r.price_type||'').toLowerCase()==='monthly'&&String(r.price_date||'').slice(0,7)===ym).sort((a,b)=>String(a.price_date).localeCompare(String(b.price_date)));
  if(monthly.length&&Number.isFinite(Number(monthly.at(-1).price)))return Number(monthly.at(-1).price);
  // 초기 엑셀 기준값은 DB에 없는 과거월의 보조 기준으로만 사용
  const ref=matrixCaptureReference()[item]?.months?.[ym];
  if(ref!==null&&ref!==undefined&&Number.isFinite(Number(ref)))return Number(ref);
  // 이후 누적된 주간 DB가 충분하면 월평균 자동 산출
  return matrixObservedMonthAverage(item,year,month,2);
}"""
if old not in s:
    if 'const monthly=ALL_MARKET.filter' in s:
        raise SystemExit(0)
    raise SystemExit('matrixMonthAverage target not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
