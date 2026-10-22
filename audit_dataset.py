"""Reconcile saved original statements and generate auditable result files."""
from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
from app import calculate,screen,FIELDS
ROOT=Path(__file__).parent

def main():
    p=ROOT/'universe.csv';d=pd.read_csv(p)
    # Normalize the company-name identity consistently across cached metadata sources.
    d['issuer_id']=d['name'].str.lower().map(lambda s:re.sub(r'\bclass\s+[a-z]\b','',s).strip())
    duplicates=d[d.duplicated('issuer_id',keep='first')]
    duplicates.to_csv(ROOT/'duplicate_issuers_removed.csv',index=False)
    d=d.drop_duplicates('issuer_id',keep='first').copy()
    derived=[];checks=[]
    for idx,r in d.iterrows():
        folder=ROOT/'raw'/r.ticker
        if not (folder/'balance_sheet.csv').exists():continue
        b=pd.read_csv(folder/'balance_sheet.csv',index_col=0)
        def get(label):
            return b.loc[label,r.fiscal_date] if label in b.index and r.fiscal_date in b.columns else np.nan
        eq=get('Total Equity Gross Minority Interest')
        if pd.notna(eq):
            if pd.isna(r.total_liabilities):
                d.loc[idx,'total_liabilities']=r.total_assets-eq
                derived.append({'ticker':r.ticker,'field':'total_liabilities','identity':'assets minus consolidated equity'})
            if abs(eq+d.loc[idx,'total_liabilities']-r.total_assets)<=max(1,abs(r.total_assets)*1e-6):
                d.loc[idx,'equity_including_minority']=eq
                checks.append(r.ticker)
        totaldebt=get('Total Debt')
        if pd.isna(r.short_debt) and pd.notna(totaldebt) and pd.notna(r.long_debt) and totaldebt>=r.long_debt:
            d.loc[idx,'short_debt']=totaldebt-r.long_debt
            derived.append({'ticker':r.ticker,'field':'short_debt','identity':'total debt minus long-term debt including leases'})
    for idx,r in d.iterrows():d.loc[idx,'data_warnings']='; '.join(k+' missing' for k in FIELDS if pd.isna(r.get(k)))
    d.to_csv(p,index=False)
    m=calculate(d)
    _,buy,sell=screen(m,sorted(m.sector.unique()),3e8,1e13,0,.2,6,80,80,1.81,2)
    buy.to_csv(ROOT/'buy_rankings.csv',index=False);sell.to_csv(ROOT/'sell_rankings.csv',index=False)
    audit={'companies':len(d),'duplicate_issuers_removed':duplicates.ticker.tolist(),'financial_sector_rows':int(d.sector.eq('Financial Services').sum()),'duplicate_tickers':int(d.ticker.duplicated().sum()),'equity_reconciliations':len(checks),'derived_fields':derived,'coverage':m[['GPA','BM','F_SCORE','STA','SNOA','Z']].notna().sum().to_dict(),'default_BUY':len(buy),'default_SELL':len(sell),'fiscal_dates':sorted(d.fiscal_date.unique()),'retrieval_start':d.retrieved_at.min(),'retrieval_end':d.retrieved_at.max(),'pitch_exclusion_confirmed':False}
    (ROOT/'data_audit.json').write_text(json.dumps(audit,indent=2,default=str))
    # Independent scalar recalculation, separate from vectorized application functions.
    manual=[]
    for _,r in d.head(3).iterrows():
        calculations={'GPA':(r.revenue-r.cogs)/r.total_assets,'BM':r.common_equity/r.market_cap,'STA':(r.net_income-r.operating_cash_flow)/r.total_assets}
        if pd.notna(r.get('equity_including_minority')):calculations['SNOA']=(r.short_debt+r.long_debt+r.equity_including_minority-r.cash)/r.total_assets
        calculations['Z']=.012*(r.current_assets-r.current_liabilities)/r.total_assets+.014*r.retained_earnings/r.total_assets+.033*r.ebit/r.total_assets+.006*r.market_cap/r.total_liabilities+.999*r.revenue/r.total_assets
        expected=m[m.ticker.eq(r.ticker)].iloc[0]
        for measure,value in calculations.items():
            if pd.notna(value):
                assert np.isclose(value,expected[measure]),(r.ticker,measure)
                manual.append({'ticker':r.ticker,'measure':measure,'independent_value':value,'app_value':expected[measure],'passed':True})
    (ROOT/'manual_checks.json').write_text(json.dumps(manual,indent=2))
    print(json.dumps({k:v for k,v in audit.items() if k not in ['derived_fields','fiscal_dates']},indent=2))
if __name__=='__main__':main()
