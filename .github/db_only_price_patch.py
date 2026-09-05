from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# 1) Remove hard-coded 1P matrix values from source markup. Keep row/item structure only.
m=re.search(r'(<table class="price-matrix">.*?<tbody>)(.*?)(</tbody>\s*</table>)',s,re.S)
if not m:
    raise SystemExit('price-matrix tbody not found')
body=m.group(2)

def blank_row(match):
    row=match.group(0)
    cells=list(re.finditer(r'<td([^>]*)>.*?</td>',row,re.S))
    if not cells:
        return row
    out=[]; pos=0
    for i,c in enumerate(cells):
        out.append(row[pos:c.start()])
        if i==0:
            out.append(c.group(0))
        else:
            content='' if i==1 else '-'
            out.append(f'<td{c.group(1)}>{content}</td>')
        pos=c.end()
    out.append(row[pos:])
    return ''.join(out)

body2=re.sub(r'<tr(?:\s[^>]*)?>.*?</tr>',blank_row,body,flags=re.S)
s=s[:m.start(2)]+body2+s[m.end(2):]

# 2) Remove hard-coded detailed price cells on P2/P3. DB/report_weekly will paint them.
s=re.sub(r'<td class="price">.*?</td>', '<td class="price"><div class="price-main">—</div><div class="delta">(-)</div></td>', s, flags=re.S)

# 3) Never seed market data from the HTML design; legacy seed function may remain but is unused.
s=s.replace("function rebuildAllMarket(extra=[]){ALL_MARKET=mergeMarket(BASE_MARKET,REMOTE_MARKET,allCachedMarket(),extra);}",
            "function rebuildAllMarket(extra=[]){ALL_MARKET=mergeMarket(REMOTE_MARKET,allCachedMarket().filter(r=>String(r.source||'')!=='기본화면'),extra);}")

old_boot="initRowMap(); initChartControls(); document.querySelectorAll('.market-table td.body').forEach(normalizeRenderedBody); document.querySelectorAll('.market-table td.price .delta').forEach(d=>{normalizeDeltaNotation(d);normalizeDeltaColor(d);}); setTimeout(()=>refreshDetailDeltaColors(),0); BASE_MARKET=seedBaseMarket(); rebuildAllMarket();"
new_boot="initRowMap(); initChartControls(); document.querySelectorAll('.market-table td.body').forEach(normalizeRenderedBody); document.querySelectorAll('.market-table td.price .delta').forEach(d=>{normalizeDeltaNotation(d);normalizeDeltaColor(d);}); setTimeout(()=>refreshDetailDeltaColors(),0); BASE_MARKET=[]; rebuildAllMarket();"
if old_boot not in s:
    raise SystemExit('boot seed target not found')
s=s.replace(old_boot,new_boot,1)

# 4) Replace matrix reference/fallback logic with DB-only logic.
start=s.find('/* ---------- 1P 가격표 자동 롤링 규칙 ---------- */')
end=s.find('function renderWtiChart(week){',start)
if start<0 or end<0:
    raise SystemExit('rolling matrix block not found')

new_block=r'''/* ---------- 1P 가격표 자동 롤링 규칙: 가격은 DB 전용 ---------- */
function matrixYmKey(y,m){return `${y}-${String(m).padStart(2,'0')}`;}
function matrixMonthShift(week,back){
  const d=parseDate(week);if(!d)return null;
  const x=new Date(d.getFullYear(),d.getMonth()-back,1);
  return {year:x.getFullYear(),month:x.getMonth()+1};
}
function matrixYear2(y){return String(y).slice(-2);}
function matrixPriceForWeek(item,week){
  const direct=priceForWeek(item,week);
  if(direct!==null&&Number.isFinite(Number(direct)))return Number(direct);
  if(item==='Cost'){
    const sm=priceForWeek('SM',week),an=priceForWeek('AN',week),bd=priceForWeek('BD',week);
    return [sm,an,bd].every(v=>v!==null&&Number.isFinite(Number(v))) ? Number(sm)*0.60+Number(an)*0.25+Number(bd)*0.15 : null;
  }
  if(item==='ABS Spread'){
    const abs=priceForWeek('ABS',week),cost=matrixPriceForWeek('Cost',week);
    return abs!==null&&cost!==null?Number(abs)-Number(cost):null;
  }
  if(item==='PC-BPA Spread'){
    const pc=priceForWeek('PC',week),bpa=priceForWeek('BPA',week);
    return pc!==null&&bpa!==null?Number(pc)-Number(bpa):null;
  }
  return null;
}
function matrixSeries(item){
  const weeks=[...new Set(ALL_MARKET.filter(r=>r.price_type==='weekly').map(r=>r.week_end||r.price_date).filter(Boolean))].sort();
  return weeks.map(week=>({week,value:matrixPriceForWeek(item,week)})).filter(x=>x.value!==null&&Number.isFinite(Number(x.value)));
}
function matrixObservedMonthAverage(item,year,month,minPoints=1){
  const vals=matrixSeries(item).filter(x=>{const d=parseDate(x.week);return d&&d.getFullYear()===year&&d.getMonth()+1===month;}).map(x=>Number(x.value));
  if(vals.length<minPoints)return null;
  return vals.reduce((a,b)=>a+b,0)/vals.length;
}
function matrixDirectMonthly(item,year,month){
  const ym=matrixYmKey(year,month);
  const rows=ALL_MARKET.filter(r=>r.item===item&&String(r.price_type||'').toLowerCase()==='monthly'&&String(r.price_date||'').slice(0,7)===ym).sort((a,b)=>String(a.price_date).localeCompare(String(b.price_date)));
  return rows.length&&Number.isFinite(Number(rows.at(-1).price))?Number(rows.at(-1).price):null;
}
function matrixMonthAverage(item,year,month){
  const direct=matrixDirectMonthly(item,year,month);
  if(direct!==null)return direct;
  if(item==='WTI_MT'){
    const w=matrixMonthAverage('WTI',year,month);return w===null?null:wtiMt(w);
  }
  if(item==='Cost'){
    const sm=matrixMonthAverage('SM',year,month),an=matrixMonthAverage('AN',year,month),bd=matrixMonthAverage('BD',year,month);
    return [sm,an,bd].every(v=>v!==null)?sm*.60+an*.25+bd*.15:null;
  }
  if(item==='ABS Spread'){
    const a=matrixMonthAverage('ABS',year,month),c=matrixMonthAverage('Cost',year,month);return a!==null&&c!==null?a-c:null;
  }
  if(item==='PC-BPA Spread'){
    const pc=matrixMonthAverage('PC',year,month),bpa=matrixMonthAverage('BPA',year,month);return pc!==null&&bpa!==null?pc-bpa:null;
  }
  // 월별 summary가 아직 생성되지 않은 경우에도 DB에 저장된 weekly 값으로만 보완
  return matrixObservedMonthAverage(item,year,month,1);
}
function matrixYearAverage(item,year,week){
  const d=parseDate(week);if(!d)return null;
  const lastMonth=(year===d.getFullYear())?Math.max(0,d.getMonth()):12; // 현재년도는 직전 완료월까지
  if(lastMonth<1)return null;
  const vals=[];
  for(let m=1;m<=lastMonth;m++){
    const v=matrixMonthAverage(item,year,m);if(v!==null&&Number.isFinite(Number(v)))vals.push(Number(v));
  }
  return vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null;
}
function matrixDecember(item,year){return matrixMonthAverage(item,year,12);}
function matrixRawHistoryValues(item,year=null){
  let rows=ALL_MARKET.filter(r=>r.item===item&&['daily','weekly','monthly'].includes(String(r.price_type||'').toLowerCase())&&Number.isFinite(Number(r.price)));
  if(year!==null)rows=rows.filter(r=>String(r.price_date||'').slice(0,4)===String(year));
  if(rows.length)return rows.map(r=>Number(r.price));
  if(item==='WTI_MT'){
    const vals=matrixRawHistoryValues('WTI',year);return vals.map(wtiMt).filter(Number.isFinite);
  }
  // 파생 품목은 monthly/weekly DB 계산값으로 보완
  const years=year!==null?[year]:[...new Set(ALL_MARKET.map(r=>Number(String(r.price_date||'').slice(0,4))).filter(Number.isFinite))];
  const vals=[];
  for(const y of years){for(let m=1;m<=12;m++){const v=matrixMonthAverage(item,y,m);if(v!==null&&Number.isFinite(Number(v)))vals.push(Number(v));}}
  return vals;
}
function matrixYearExtreme(item,year,kind){
  const vals=matrixRawHistoryValues(item,year);if(!vals.length)return null;
  return kind==='high'?Math.max(...vals):Math.min(...vals);
}
function matrixHistoricalExtreme(item,kind){
  const vals=matrixRawHistoryValues(item,null);if(!vals.length)return null;
  return kind==='high'?Math.max(...vals):Math.min(...vals);
}
function setMatrixStat(td,v,item){
  if(v===null||v===undefined||!Number.isFinite(Number(v))){td.textContent='-';return;}
  td.textContent=fmt(v,item);
}
function setMatrixPair(td,hi,lo,item){
  if(hi===null||lo===null||!Number.isFinite(Number(hi))||!Number.isFinite(Number(lo))){td.textContent='-';return;}
  td.innerHTML=`${fmt(hi,item)}&nbsp;&nbsp;&nbsp;${fmt(lo,item)}`;
}
function updatePriceMatrix(week){
  const table=document.querySelector('#p1 .price-matrix'),ths=[...table.querySelectorAll('thead th')];
  const prev=addDays(week,-7),prev2=addDays(week,-14),prev3=addDays(week,-21),latestDate=addDays(week,3);
  const d=parseDate(week); if(!d)return;
  const currentYear=d.getFullYear(),currentMonth=d.getMonth()+1,prevYear=currentYear-1;
  const rollingMonths=[1,2,3,4].map(n=>matrixMonthShift(week,n));

  if(ths.length>=19){
    ths[1].textContent=md(latestDate);
    ths[2].textContent=md(week);
    ths[3].innerHTML=`전주比<br><span class="tiny">${md(prev)}→${md(week)}</span>`;
    ths[5].textContent=md(prev);ths[6].textContent=md(prev2);ths[7].textContent=md(prev3);
    rollingMonths.forEach((x,i)=>ths[8+i].innerHTML=`${matrixYear2(x.year)}년<br>${x.month}월`);
    ths[12].innerHTML=`${matrixYear2(currentYear)}년<br>평균`;
    ths[13].innerHTML=`${matrixYear2(prevYear)}년<br>평균`;
    ths[14].innerHTML=`${matrixYear2(prevYear)}년<br>12월`;
    ths[15].innerHTML=`${matrixYear2(prevYear)}년<br>${currentMonth}월`;
    ths[16].innerHTML=`${matrixYear2(prevYear)}년<br>High`;
    ths[17].innerHTML=`${matrixYear2(prevYear)}년<br>Low`;
    ths[18].innerHTML='Historical<br>High&nbsp;&nbsp;&nbsp;Low';
  }

  for(const item of PRICE_ROW_ITEMS){
    const tr=getPriceRow(item);if(!tr)continue;const c=tr.cells;
    const latest=latestForWeek(item,week),cur=matrixPriceForWeek(item,week),p1=matrixPriceForWeek(item,prev),p2=matrixPriceForWeek(item,prev2),p3=matrixPriceForWeek(item,prev3);
    setMatrix(c[1],latest?Number(latest.price):null,item,true);setMatrix(c[2],cur,item);setMatrix(c[5],p1,item);setMatrix(c[6],p2,item);setMatrix(c[7],p3,item);

    c[1].classList.remove('up','down');c[1].style.removeProperty('color');
    if(latest&&cur!==null){const ld=Number(latest.price)-Number(cur);if(ld>0)c[1].classList.add('up');else if(ld<0)c[1].classList.add('down');}
    c[3].classList.remove('up','down');c[4].classList.remove('up','down');
    if(cur!==null&&p1!==null){
      const diff=cur-p1,pct=p1?diff/p1*100:0,mark=diff>0?'+':diff<0?'△':'';
      c[3].textContent=diff===0?'-':`${mark}${fmt(Math.abs(diff),item)}`;
      c[4].textContent=diff===0?'-':`${mark}${Math.abs(pct).toFixed(Math.abs(pct)<1?1:0)}`;
      if(diff>0){c[3].classList.add('up');c[4].classList.add('up');}else if(diff<0){c[3].classList.add('down');c[4].classList.add('down');}
    }else{c[3].textContent='-';c[4].textContent='-';}

    rollingMonths.forEach((x,i)=>setMatrixStat(c[8+i],matrixMonthAverage(item,x.year,x.month),item));
    setMatrixStat(c[12],matrixYearAverage(item,currentYear,week),item);
    setMatrixStat(c[13],matrixYearAverage(item,prevYear,week),item);
    setMatrixStat(c[14],matrixDecember(item,prevYear),item);
    setMatrixStat(c[15],matrixMonthAverage(item,prevYear,currentMonth),item);
    setMatrixStat(c[16],matrixYearExtreme(item,prevYear,'high'),item);
    setMatrixStat(c[17],matrixYearExtreme(item,prevYear,'low'),item);
    setMatrixPair(c[18],matrixHistoricalExtreme(item,'high'),matrixHistoricalExtreme(item,'low'),item);
  }
}

function setMatrix(td,v,item,blankIfMissing=false){if(v===null||v===undefined||!Number.isFinite(Number(v))){td.innerHTML=blankIfMissing?'':'-';return;}td.textContent=fmt(v,item);}
'''

s=s[:start]+new_block+s[end:]

p.write_text(s,encoding='utf-8')
