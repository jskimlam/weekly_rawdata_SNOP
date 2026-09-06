from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

old = '''function matrixYearAverage(item,year,week){
  const d=parseDate(week);if(!d)return null;
  const lastMonth=(year===d.getFullYear())?Math.max(0,d.getMonth()):12; // 현재년도는 직전 완료월까지
  if(lastMonth<1)return null;
  const vals=[];
  for(let m=1;m<=lastMonth;m++){
    const v=matrixMonthAverage(item,year,m);if(v!==null&&Number.isFinite(Number(v)))vals.push(Number(v));
  }
  return vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null;
}
'''
new = '''function matrixDirectStatRow(item,type,year=null){
  const rows=ALL_MARKET.filter(r=>r.item===item&&String(r.price_type||'').toLowerCase()===type&&Number.isFinite(Number(r.price))&&
    (year===null||String(r.price_date||'').slice(0,4)===String(year))).sort((a,b)=>String(a.price_date).localeCompare(String(b.price_date)));
  return rows.length?rows.at(-1):null;
}
function matrixYearAverage(item,year,week){
  const d=parseDate(week);if(!d)return null;
  const lastMonth=(year===d.getFullYear())?Math.max(0,d.getMonth()):12;
  if(lastMonth<1)return null;
  const explicit=matrixDirectStatRow(item,'year_avg',year);
  if(explicit){
    const ed=parseDate(explicit.price_date),baseMonth=ed?ed.getMonth()+1:12,base=Number(explicit.price);
    if(year!==d.getFullYear()||lastMonth<=baseMonth)return base;
    let total=base*baseMonth,count=baseMonth;
    for(let m=baseMonth+1;m<=lastMonth;m++){
      const v=matrixMonthAverage(item,year,m);
      if(v!==null&&Number.isFinite(Number(v))){total+=Number(v);count++;}
    }
    return count?total/count:base;
  }
  const vals=[];
  for(let m=1;m<=lastMonth;m++){
    const v=matrixMonthAverage(item,year,m);if(v!==null&&Number.isFinite(Number(v)))vals.push(Number(v));
  }
  return vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null;
}
'''
if old not in s:
    raise SystemExit('matrixYearAverage target not found')
s = s.replace(old, new, 1)

old2 = '''function matrixYearExtreme(item,year,kind){
  const vals=matrixRawHistoryValues(item,year);if(!vals.length)return null;
  return kind==='high'?Math.max(...vals):Math.min(...vals);
}
function matrixHistoricalExtreme(item,kind){
  const vals=matrixRawHistoryValues(item,null);if(!vals.length)return null;
  return kind==='high'?Math.max(...vals):Math.min(...vals);
}
'''
new2 = '''function matrixYearExtreme(item,year,kind){
  const direct=matrixDirectStatRow(item,kind==='high'?'year_high':'year_low',year);
  if(direct)return Number(direct.price);
  const vals=matrixRawHistoryValues(item,year);if(!vals.length)return null;
  return kind==='high'?Math.max(...vals):Math.min(...vals);
}
function matrixHistoricalExtreme(item,kind){
  const direct=matrixDirectStatRow(item,kind==='high'?'historical_high':'historical_low',null);
  if(direct)return Number(direct.price);
  const vals=matrixRawHistoryValues(item,null);if(!vals.length)return null;
  return kind==='high'?Math.max(...vals):Math.min(...vals);
}
'''
if old2 not in s:
    raise SystemExit('extreme target not found')
s = s.replace(old2, new2, 1)

p.write_text(s, encoding='utf-8')
print('index.html patched')
