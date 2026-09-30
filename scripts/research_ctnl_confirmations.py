"""CTNL-Reversal: Bestaetigungen + Kill-Switch-Varianten (2026-09-30, Befund 18).

Anlass: Short-Serie 29./30.09. (9 SL, dann ein Gewinner nach News-Spike).
Misst je Trade Merkmale der Signalbar (Range/ATR, Wick, Sweep-Tiefe,
Whole-Level, Stunde, vorherige SL gleicher Richtung) und vergleicht
Kill-Switch-/Risiko-Varianten auf der R-Reihe. Engine-R (next_open, ohne
Live-Lag) -- Richtungsaussagen, keine Live-Zahlen. Nur lesend.

Aufruf: python scripts/research_ctnl_confirmations.py <cache.pkl>
(baut Signale beim ersten Lauf, ~10 Min.)
"""
# ---------------- Schritt ctnl_diag0
def _ctnl_diag0():
    import sys
    import sys; sys.path[:0]=['.','scripts','ou_paper_backtest']
    import pandas as pd, pickle
    from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_w1
    from gold_smc_htf_ltf.live_signal import REV_KWARGS
    from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
    from research_ctnl_execution_costs import load_bars
    from research_ctnl_ribbon_both_legs import ribbon_direction
    S,E='2016-01-01','2026-10-01'
    bars=load_bars(S,E)
    rib=ribbon_direction(bars['h4'],fetch_gold_d1(S,E),fetch_gold_w1(S,E))
    sig=run_reversal(bars['h4'],bars['h1'],bars['m15'],**REV_KWARGS)
    print(sig.columns.tolist()); print(sig[sig.signal!=0].tail(3).T)
    pickle.dump({'bars':bars,'rib':rib,'sig':sig},open(sys.argv[1],'wb'))
# ---------------- Schritt ctnl_diag1
def _ctnl_diag1():
    import sys
    import sys; sys.path[:0]=['.','scripts','ou_paper_backtest']
    import pandas as pd, numpy as np, pickle
    from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent
    from gold_smc_htf_ltf.live_signal import REV_MAX_CONCURRENT
    from research_ctnl_execution_costs import _cap_concurrent
    from research_ctnl_optimization import MEASURED_BPS
    from strategy.backtest import BacktestConfig
    d=pickle.load(open(sys.argv[1],'rb')); sig=d['sig']; rib=d['rib']
    cfg=BacktestConfig(spread_bps=MEASURED_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, max_hold_bars=96*4)
    raw=simulate_trades_concurrent(sig,cfg)
    print('cols',raw.columns.tolist(), len(raw))
    tr=_cap_concurrent(raw,REV_MAX_CONCURRENT); print('capped',len(tr))
    raw.to_pickle(sys.argv[1]+'.raw'); tr.to_pickle(sys.argv[1]+'.tr')
# ---------------- Schritt ctnl_diag2
def _ctnl_diag2():
    import sys
    import sys; sys.path[:0]=['.','scripts','ou_paper_backtest']
    import pandas as pd, numpy as np, pickle
    P=sys.argv[1]
    d=pickle.load(open(P,'rb')); sig=d['sig']; rib=d['rib']
    tr=pd.read_pickle(P+'.tr').copy()
    print(tr.signal_bar.head(2).tolist(), tr.entry_time.head(2).tolist())
    def utc(s):
        s=pd.to_datetime(s); return s.dt.tz_convert('UTC') if s.dt.tz is not None else s.dt.tz_localize('UTC')
    tr['et']=utc(tr.entry_time); tr['xt']=utc(tr.exit_time)
    si=sig.index.tz_convert('UTC') if sig.index.tz is not None else sig.index.tz_localize('UTC')
    sg=sig.copy(); sg.index=si
    sb=tr.signal_bar
    if np.issubdtype(np.asarray(sb).dtype, np.integer): row=sg.iloc[sb.values]
    else: row=sg.loc[utc(sb)]
    row=row.reset_index(drop=True); tr=tr.reset_index(drop=True)
    dr=tr.direction.values
    rng=(row.high-row.low)
    tr['spike']=(rng/row.atr).values
    top=np.where(dr<0,row.high-np.maximum(row.open,row.close),np.minimum(row.open,row.close)-row.low)
    tr['wick']=(top/rng.replace(0,np.nan)).values
    ref=np.where(dr<0,row.prev_high,row.prev_low)
    tr['sweep']=(np.where(dr<0,row.high-ref,ref-row.low)/row.atr).values
    tr['hour']=tr.et.dt.hour
    L=50.0
    lvl=np.where(dr<0,np.floor(row.high/L)*L,np.ceil(row.low/L)*L)
    tr['whole']=np.where(dr<0,(row.high>=lvl)&(row.close<lvl)&(row.open<lvl+L),(row.low<=lvl)&(row.close>lvl))
    ri=rib.copy(); ri.index=(ri.index.tz_convert('UTC') if ri.index.tz is not None else ri.index.tz_localize('UTC'))
    tr['rib']=ri.reindex(tr.et,method='ffill').values
    tr['konform']=((dr==1)&(tr.rib>0))|((dr==-1)&(tr.rib<0))
    # prior same-direction losses in last 48h, closed before entry
    k=[]; opn=[]
    for i,r in tr.iterrows():
        m=(tr.direction==r.direction)&(tr.et<r.et)&(tr.et>=r.et-pd.Timedelta('48h'))
        k.append(int((m&(tr.xt<=r.et)&(tr.r_multiple<0)).sum()))
        opn.append(int((m&(tr.xt>r.et)).sum()))
    tr['k_sl']=k; tr['k_open']=opn
    tr['R']=tr.r_multiple; tr['win']=tr.R>0
    tr.to_pickle(P+'.feat')
    def rep(g,name):
        a=tr.groupby(g).agg(n=('R','size'),win=('win','mean'),avgR=('R','mean'),sumR=('R','sum'))
        print('\n##',name); print(a.round(3).to_string())
    print('ALL',len(tr),tr.R.mean().round(3),tr.R.sum().round(1),'win',tr.win.mean().round(3))
    for sub,lab in [(tr,'alle'),(tr[tr.konform],'ribbon-konform')]:
        t=sub
        print('\n==========',lab,len(t),round(t.R.mean(),3))
        for g,name in [(pd.cut(t.k_sl,[-1,0,1,2,3,5,99]),'vorherige SL gleiche Richtung 48h'),
                       (pd.cut(t.k_open,[-1,0,1,2,99]),'offene gleiche Richtung'),
                       (pd.qcut(t.spike,4),'Signalbar-Range/ATR'),
                       (pd.qcut(t.wick,4),'Wick-Anteil Ablehnung'),
                       (pd.qcut(t.sweep.fillna(0),4,duplicates='drop'),'Sweep-Tiefe/ATR'),
                       (pd.cut(t.hour,[-1,6,11,15,19,24]),'Stunde UTC'),
                       (t.whole,'Whole-Level 50 gesweept+zurueck'),
                       (t.direction,'Richtung')]:
            a=t.groupby(g,observed=True).agg(n=('R','size'),win=('win','mean'),avgR=('R','mean'),sumR=('R','sum'))
            print('--',name); print(a.round(3).to_string())
# ---------------- Schritt ctnl_diag3
def _ctnl_diag3():
    import sys
    import pandas as pd, numpy as np, sys
    t=pd.read_pickle(sys.argv[1]+'.feat'); k=t[t.konform].copy()
    k['y']=k.et.dt.year; k['klein']=k.spike<0.75; k['serie']=k.k_sl>=1
    print('Spike<0.75 ATR je Jahr (ribbon-konform):')
    print(k.groupby(['y','klein']).R.agg(['size','mean','sum']).unstack().round(2).to_string())
    print('\nSerie (>=1 vorheriger SL) je Jahr:')
    print(k.groupby(['y','serie']).R.agg(['size','mean','sum']).unstack().round(2).to_string())
    print('\nShorts ribbon-konform nach spike:')
    s=k[k.direction==-1]; print(s.groupby(s.klein).R.agg(['size','mean','sum']).round(3))
    print('\nMaxDD in R (ribbon-konform), mit/ohne Spike-Filter:')
    for lab,x in [('alle',k),('spike>=0.75',k[~k.klein])]:
        c=x.sort_values('et').R.cumsum(); print(lab,len(x),round(x.R.sum(),1),'maxDD R',round((c-c.cummax()).min(),1))
    print('\nletzte Trades 29./30.09:')
    print(t[t.et>='2026-09-29'][['et','direction','R','spike','wick','sweep','k_sl','k_open','konform','exit_reason']].round(2).to_string())
# ---------------- Schritt ctnl_diag4
def _ctnl_diag4():
    import sys
    import pandas as pd, numpy as np, sys
    t=pd.read_pickle(sys.argv[1]+'.feat')
    def dd(r):
        c=np.cumsum(r); return (c-np.maximum.accumulate(np.r_[0,c])[1:]).min()
    def run(k,name):
        k=k.sort_values('et').reset_index(drop=True); R=k.R.values
        res={}
        res['heute (alle nehmen)']=R
        # DD-Kill in R auf Schatten-Kurve: aus bei -44R (=6,6%/0,15%), an bei -22R
        for thr in (44,20,10):
            c=0;pk=0;off=False;out=[]
            for r in R:
                out.append(0.0 if off else r)
                c+=r; pk=max(pk,c); d=c-pk
                if not off and d<=-thr: off=True
                elif off and d>=-thr/2: off=False
            res[f'DD-Kill {thr}R/{thr/2:g}R']=np.array(out)
        # Tages-Serienstopp: nach 3 SL gleicher Richtung am selben Tag Richtung pausieren
        out=[]; cnt={}
        for i,r in k.iterrows():
            key=(r.et.date(),r.direction)
            out.append(0.0 if cnt.get(key,0)>=3 else r.R)
            if r.R<0: cnt[key]=cnt.get(key,0)+1
        res['Tagesstopp 3 SL/Richtung']=np.array(out)
        # halbes Risiko nach 3 Verlusten in Folge bis zum naechsten Gewinner
        out=[];streak=0
        for r in R:
            out.append(r*(0.5 if streak>=3 else 1)); streak=0 if r>0 else streak+1
        res['halbes Risiko nach 3 Verlusten']=np.array(out)
        k2=k[k.spike>=0.75]; res['Spike-Filter >=0,75 ATR']=None
        print('\n####',name,len(k))
        for n,v in res.items():
            if v is None: v=k2.R.values
            print(f'  {n:34s} SumR {v.sum():+7.1f}  MaxDD {dd(v):+6.1f}R  Ret/DD {v.sum()/-dd(v):5.2f}')
    run(t,'alle Reversal (ohne Ribbon)')
    run(t[t.konform],'Ribbon-konform (live seit heute)')

if __name__ == "__main__":
    import os, sys
    if not os.path.exists(sys.argv[1]): _ctnl_diag0()
    if not os.path.exists(sys.argv[1] + ".tr"): _ctnl_diag1()
    for s in (_ctnl_diag2, _ctnl_diag3, _ctnl_diag4): s()
