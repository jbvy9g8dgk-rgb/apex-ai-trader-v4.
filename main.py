"""APEX V4: rule-based paper trading only. No real orders, no LLM claims."""
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import ccxt
import pandas as pd

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'paper_state.json'
OUTPUT=ROOT/'docs'/'data.json'
SYMBOLS=['BTC/AUD','ETH/AUD','SOL/AUD']
FEE=.004; SLIPPAGE=.001; MAX_SPEND=10.; MAX_POSITIONS=2

def initial():
    return dict(cash=100.,positions={},trades=[],equity=100.,equity_history=[],peak_equity=100.,day='',day_start_equity=100.,halted=False)

def market(ex,symbol):
    raw=ex.fetch_ohlcv(symbol,'15m',limit=160)
    if len(raw)<80: raise ValueError('Insufficient OHLCV data')
    df=pd.DataFrame(raw,columns=['time','open','high','low','close','volume']).iloc[:-1]
    c=df.close.astype(float); high=df.high.astype(float); low=df.low.astype(float)
    fast=c.ewm(span=20,adjust=False).mean();slow=c.ewm(span=50,adjust=False).mean()
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean();loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rsi=float((100-100/(1+gain/(loss+1e-12))).iloc[-1]);macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean();hist=macd-macd.ewm(span=9,adjust=False).mean()
    tr=pd.concat([high-low,(high-c.shift()).abs(),(low-c.shift()).abs()],axis=1).max(axis=1);atr=float(tr.ewm(alpha=1/14,adjust=False).mean().iloc[-1]);price=float(c.iloc[-1]);momentum=float(c.iloc[-1]/c.iloc[-9]-1)
    trend=fast.iloc[-1]>slow.iloc[-1];macd_up=hist.iloc[-1]>0
    points=int(trend)*30+int(macd_up)*25+int(48<=rsi<=68)*25+int(momentum>.002)*20
    fresh=(datetime.now(timezone.utc).timestamp()*1000-int(df.time.iloc[-1]))<60*60*1000
    volatile=atr/price>.035
    if not fresh: signal='WAIT';reason='stale candle data'
    elif volatile: signal='WAIT';reason='volatility filter'
    elif points>=75 and rsi<72: signal='BUY';reason='trend + momentum agreement'
    elif (not trend and not macd_up) or rsi<38: signal='SELL';reason='trend or momentum weakened'
    else: signal='WAIT';reason='insufficient indicator agreement'
    return dict(symbol=symbol,signal=signal,score=points,price=round(price,5),reason=reason,atr=atr,stale=not fresh)

def equity(s,prices):return s['cash']+sum(p['qty']*prices.get(sym,p['entry_price']) for sym,p in s['positions'].items())
def trade(s,side,m,now,reason):
    symbol=m['symbol'];price=m['price'];positions=s['positions']
    if side=='SELL' and symbol in positions:
        pos=positions.pop(symbol);value=pos['qty']*price*(1-SLIPPAGE)*(1-FEE);s['cash']+=value;aud=value
    elif side=='BUY' and symbol not in positions and len(positions)<MAX_POSITIONS and s['cash']>=10:
        aud=min(MAX_SPEND,s['cash']);qty=aud*(1-FEE)/(price*(1+SLIPPAGE));positions[symbol]=dict(qty=qty,entry_price=price,stop=price-max(m['atr']*2.5,price*.015),cost_aud=aud);s['cash']-=aud
    else:return
    s['trades'].append(dict(time=now,symbol=symbol,side=side,aud=round(aud,4),reason=reason))

def main():
    s=json.loads(STATE.read_text()) if STATE.exists() else initial()
    for k,v in initial().items():s.setdefault(k,v)
    ex=ccxt.kraken({'enableRateLimit':True,'timeout':20000});now=datetime.now(timezone.utc).isoformat();markets=[];traces=[]
    for sym in SYMBOLS:
        try:markets.append(market(ex,sym))
        except Exception as e:traces.append(sym+': data unavailable ('+str(e)[:130]+')')
    if not markets:raise RuntimeError('No market data; state not changed')
    prices={m['symbol']:m['price'] for m in markets};before=equity(s,prices);day=now[:10]
    if s['day']!=day:s['day']=day;s['day_start_equity']=before
    s['peak_equity']=max(s['peak_equity'],before)
    if before<=s['day_start_equity']-3 or before<=s['peak_equity']-10:s['halted']=True
    for m in markets:
        sym=m['symbol'];pos=s['positions'].get(sym)
        if pos and (m['price']<=pos['stop'] or m['signal']=='SELL'):
            trade(s,'SELL',m,now,'stop loss' if m['price']<=pos['stop'] else m['reason'])
    if not s['halted']:
        for m in markets:
            if m['signal']=='BUY':trade(s,'BUY',m,now,m['reason'])
    else:traces.append('Risk supervisor: entries halted; manual state review required')
    for m in markets:traces.append(f"{m['symbol']}: {m['signal']} • heuristic score {m['score']}/100 • {m['reason']}")
    s['equity']=round(equity(s,prices),4);s['peak_equity']=max(s['peak_equity'],s['equity'])
    s['equity_history']=(s['equity_history']+[dict(time=now,equity=s['equity'])])[-500:];s['trades']=s['trades'][-300:]
    summary='Risk halt active. Review state before any further entries.' if s['halted'] else f"{sum(m['signal']=='BUY' for m in markets)} BUY candidates, {sum(m['signal']=='SELL' for m in markets)} SELL signals. Data quality and risk filters applied."
    result=dict(mode='PAPER',updated_at=now,state=s,markets=markets,briefing=summary,traces=traces)
    OUTPUT.parent.mkdir(exist_ok=True);OUTPUT.write_text(json.dumps(result,indent=2));STATE.write_text(json.dumps(s,indent=2))
    print(summary,'Equity:',s['equity'])
if __name__=='__main__':main()
