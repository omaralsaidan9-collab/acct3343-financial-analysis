from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="ACCT 3343 Financial Screen", page_icon="◈", layout="wide")

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "universe.csv"
PERIOD_DATES_PATH = ROOT / "period_dates.csv"

st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: #0d1117; color: #e6edf3; }
[data-testid="stSidebar"] { background: #111821; border-right: 1px solid #263241; }
[data-testid="stMetric"] { background: #151e29; border: 1px solid #2a394a; padding: 14px 16px; border-radius: 12px; }
.card { background: #151e29; border: 1px solid #2a394a; border-radius: 12px; padding: 18px 20px; margin: 8px 0 16px; }
.buy-card { border-left: 5px solid #36c77b; }
.sell-card { border-left: 5px solid #f06464; }
.buy-title { color: #4bd18c !important; }
.sell-title { color: #ff7373 !important; }
.small-note { color: #a6b2bf; font-size: .9rem; }
h1, h2, h3 { color: #e8eef5; }
[data-testid="stTabs"] button[role="tab"] { color: #c3ced9; }
[data-testid="stTabs"] button[role="tab"]:nth-of-type(1) { color: #4bd18c; }
[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) { color: #ff7373; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { border-bottom-color: #6ea6d9; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid #2a394a; border-radius: 10px; }
[data-testid="stExpander"] { background: #121a23; border: 1px solid #2a394a; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

@st.cache_data

def load_data(path, period_dates_file_stamp=None):
    d = pd.read_csv(path)
    d["ticker"] = d["ticker"].astype(str).str.upper().str.strip()
    dates_path = Path(path).with_name("period_dates.csv")
    if dates_path.exists():
        dates = pd.read_csv(dates_path, usecols=["ticker", "y0_period_end", "y1_period_end", "y2_period_end"])
        dates["ticker"] = dates["ticker"].astype(str).str.upper().str.strip()
        d = d.merge(dates, on="ticker", how="left", validate="one_to_one")
    numeric = ["market_cap_usd", "GPA", "Book_to_Market", "STA", "SNOA", "Altman_Z", "F_SCORE", "BUY_score", "SELL_score"]
    for c in numeric:
        if c in d:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d

if not DATA_PATH.exists():
    st.error("universe.csv is missing. Put it in the same folder as app.py.")
    st.stop()

date_file_stamp = PERIOD_DATES_PATH.stat().st_mtime_ns if PERIOD_DATES_PATH.exists() else None
df = load_data(str(DATA_PATH), date_file_stamp)
# WDC is retained in the raw source for auditability but never appears in recommendations.
recommendation_universe = df[df["ticker"] != "WDC"].copy()

captured = pd.to_datetime(recommendation_universe.get("captured_at_utc"), errors="coerce", utc=True).dropna()
as_of = captured.max().strftime("%b %d, %Y %H:%M UTC") if not captured.empty else "Not recorded"

st.title("Financial Analysis Screen")
st.caption("ACCT 3343 · Course-based BUY and SELL screens")
st.markdown(f"<div class='small-note'>Universe capture: {as_of} · Yahoo Finance annual statements · WDC excluded from recommendations</div>", unsafe_allow_html=True)

st.subheader("Market snapshot · October 22, 2026")
news_col, leader_col = st.columns(2)
with news_col:
    st.markdown("""
<div class="card">
<b>Today’s market news</b><br>
U.S. stock futures moved lower as investors assessed Tesla and Meta earnings, with technology leading the declines.<br>
<a href="https://ca.finance.yahoo.com/news/live/stock-market-today-thursday-october-21-dow-sp-500-nasdaq-tesla-meta-094500493.html" target="_blank">Read Yahoo Finance’s market coverage</a>
</div>
""", unsafe_allow_html=True)
with leader_col:
    st.markdown("""
<div class="card">
<b>Leading S&amp;P 500 sector recently</b><br>
Yahoo Finance’s sector tracker currently ranks Energy first year to date (+43.52%), followed by Industrials (+40.83%). Higher oil prices amid the Iran conflict have supported energy shares. Returns are year to date, not today’s single-session performance.<br>
<a href="https://finance.yahoo.com/sectors/energy/" target="_blank">View Yahoo Finance’s Energy sector performance</a> · <a href="https://finance.yahoo.com/energy/articles/oil-prices-back-above-100-102500097.html" target="_blank">Read why oil prices matter for energy stocks</a>
</div>
""", unsafe_allow_html=True)

# Sidebar controls rerun the app automatically whenever a value changes.
st.sidebar.header("Screen filters")
sectors = sorted(recommendation_universe["sector"].dropna().astype(str).unique().tolist())
size_options = ["All sizes", "Large cap (≥ $10B)", "Mid cap ($2B–$10B)", "Small cap (< $2B)"]

def reset_filters():
    st.session_state["selected_sectors"] = sectors
    st.session_state["size_choice"] = size_options[0]
    st.session_state["score_buy"] = 0.70
    st.session_state["min_fscore"] = 6
    st.session_state["gpa_min"] = 0.0
    st.session_state["bm_min"] = 0.0
    st.session_state["score_sell"] = 0.70
    st.session_state["sta_cut"] = 0.10
    st.session_state["snoa_cut"] = 0.50
    st.session_state["z_cut"] = 1.81
    st.session_state["flags_required"] = 2

st.sidebar.button("Reset filters", on_click=reset_filters, use_container_width=True)
selected_sectors = st.sidebar.multiselect("Sectors", sectors, default=sectors, key="selected_sectors")
size_choice = st.sidebar.selectbox("Company size", size_options, key="size_choice")

base = recommendation_universe[recommendation_universe["sector"].astype(str).isin(selected_sectors)].copy()
cap = base["market_cap_usd"]
if size_choice == "Large cap (≥ $10B)":
    base = base[cap >= 10_000_000_000]
elif size_choice == "Mid cap ($2B–$10B)":
    base = base[(cap >= 2_000_000_000) & (cap < 10_000_000_000)]
elif size_choice == "Small cap (< $2B)":
    base = base[cap < 2_000_000_000]

# Peer-relative composite scores recalculate on sector and size selections.
buy_inputs = ["GPA", "Book_to_Market", "F_SCORE"]
sell_inputs = ["STA", "SNOA", "Altman_Z"]

def rank_score(frame, cols, directions):
    available = frame[cols].notna().all(axis=1)
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    if available.any():
        pieces = []
        for col, high_is_good in zip(cols, directions):
            ranks = frame.loc[available, col].rank(pct=True, method="average")
            pieces.append(ranks if high_is_good else 1.0 - ranks)
        out.loc[available] = pd.concat(pieces, axis=1).mean(axis=1)
    return out

base["BUY_score_live"] = rank_score(base, buy_inputs, [True, True, True])
base["SELL_score_live"] = rank_score(base, sell_inputs, [True, True, False])

# Adjustable BUY thresholds.
score_buy = st.sidebar.slider("Minimum BUY composite score", 0.0, 1.0, 0.70, 0.01, key="score_buy")
min_fscore = st.sidebar.slider("Minimum F_SCORE", 0, 9, 6, 1, key="min_fscore")
gpa_min = st.sidebar.slider("Minimum GPA", -1.0, 2.0, 0.0, 0.01, key="gpa_min")
bm_min = st.sidebar.slider("Minimum Book-to-Market", -1.0, 3.0, 0.0, 0.01, key="bm_min")

# Independent SELL red-flag thresholds.
score_sell = st.sidebar.slider("Minimum SELL risk score", 0.0, 1.0, 0.70, 0.01, key="score_sell")
sta_cut = st.sidebar.slider("Flag STA above", -0.5, 0.5, 0.10, 0.01, key="sta_cut")
snoa_cut = st.sidebar.slider("Flag SNOA above", -1.0, 2.0, 0.50, 0.01, key="snoa_cut")
z_cut = st.sidebar.slider("Flag Altman Z below", -2.0, 6.0, 1.81, 0.01, key="z_cut")
flags_required = st.sidebar.slider("Required SELL red flags", 1, 3, 2, 1, key="flags_required")

buy = base[
    base["BUY_score_live"].ge(score_buy)
    & base["F_SCORE"].ge(min_fscore)
    & base["GPA"].ge(gpa_min)
    & base["Book_to_Market"].ge(bm_min)
].copy()
buy = buy.sort_values("BUY_score_live", ascending=False)

sell = base.copy()
sell["STA_flag"] = sell["STA"].gt(sta_cut)
sell["SNOA_flag"] = sell["SNOA"].gt(snoa_cut)
sell["Altman_flag"] = sell["Altman_Z"].lt(z_cut)
sell["SELL_red_flags"] = sell[["STA_flag", "SNOA_flag", "Altman_flag"]].sum(axis=1)
sell = sell[
    sell["SELL_score_live"].ge(score_sell)
    & sell["SELL_red_flags"].ge(flags_required)
].sort_values("SELL_score_live", ascending=False)

# Top-level counts and data-quality visibility.
pulled = int(df.get("data_pull_status", pd.Series(index=df.index, dtype=object)).isin(["pulled", "partial"]).sum())
partial = int((df.get("data_pull_status", pd.Series(index=df.index, dtype=object)) == "partial").sum())
rankable_buy = int(recommendation_universe[buy_inputs].notna().all(axis=1).sum())
rankable_sell = int(recommendation_universe[sell_inputs].notna().all(axis=1).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Companies screened", f"{len(df):,}")
m2.metric("BUY candidates", f"{len(buy):,}", f"{rankable_buy:,} fully rankable before filters")
m3.metric("SELL candidates", f"{len(sell):,}", f"{rankable_sell:,} fully rankable before filters")
m4.metric("Full core statements", f"{int((df.get('data_pull_status', pd.Series(dtype=object)) == 'pulled').sum()):,}/1,000", f"{partial} partial")


buy_tab, sell_tab, company_tab, conclusion_tab, method_tab = st.tabs(["BUY screen", "SELL screen", "Company analysis", "Investment conclusions", "Methodology"])

with buy_tab:
    st.markdown('<h2 class="buy-title">BUY candidates</h2>', unsafe_allow_html=True)
    st.caption("Higher GPA, higher Book-to-Market, and higher F_SCORE contribute to the BUY composite. These are not SELL signals in reverse.")
    bcols = [c for c in ["ticker", "company_name", "sector", "market_cap_usd", "GPA", "Book_to_Market", "F_SCORE", "BUY_score_live"] if c in buy]
    st.dataframe(buy[bcols].rename(columns={"BUY_score_live":"BUY composite"}), width="stretch", hide_index=True)
    if not buy.empty:
        top = buy.iloc[0]
        st.markdown(f"<div class='card buy-card'><b>Top BUY screen result: {top['company_name']} ({top['ticker']})</b><br>GPA {top['GPA']:.3f}, Book-to-Market {top['Book_to_Market']:.3f}, F_SCORE {top['F_SCORE']:.0f}/9. This is the strongest result under the selected filters, not a price target or guarantee of undervaluation.</div>", unsafe_allow_html=True)
    else:
        st.write("No companies meet the current BUY filters.")

with sell_tab:
    st.markdown('<h2 class="sell-title">SELL risk candidates</h2>', unsafe_allow_html=True)
    st.caption("SELL ranks earnings accruals, accumulated operating assets, and Altman distress risk. A high risk rank does not by itself mean a stock is overvalued.")
    scols = [c for c in ["ticker", "company_name", "sector", "market_cap_usd", "STA", "SNOA", "Altman_Z", "SELL_red_flags", "SELL_score_live"] if c in sell]
    st.dataframe(sell[scols].rename(columns={"SELL_score_live":"SELL risk score"}), width="stretch", hide_index=True)
    if not sell.empty:
        top = sell.iloc[0]
        flags = ", ".join(name for name, col in [("STA", "STA_flag"), ("SNOA", "SNOA_flag"), ("Altman Z", "Altman_flag")] if bool(top[col]))
        st.markdown(f"<div class='card sell-card'><b>Top SELL risk result: {top['company_name']} ({top['ticker']})</b><br>Flagged measures: {flags}. STA {top['STA']:.3f}, SNOA {top['SNOA']:.3f}, Altman Z {top['Altman_Z']:.3f}. This indicates accounting or distress risk under the selected screen, not a valuation conclusion.</div>", unsafe_allow_html=True)
    else:
        st.write("No companies meet the current SELL filters.")

with company_tab:
    st.subheader("Individual company analysis")
    choices = base.sort_values("ticker")["ticker"].dropna().unique().tolist()
    selected = st.selectbox("Select a company", choices) if choices else None
    if selected:
        row = base[base.ticker == selected].iloc[0]
        st.markdown(f"### {row.get('company_name', selected)} ({selected})")
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("GPA", "—" if pd.isna(row.GPA) else f"{row.GPA:.3f}")
        k2.metric("Book-to-Market", "—" if pd.isna(row.Book_to_Market) else f"{row.Book_to_Market:.3f}")
        k3.metric("F_SCORE", "—" if pd.isna(row.F_SCORE) else f"{row.F_SCORE:.0f}/9")
        k4.metric("Altman Z", "—" if pd.isna(row.Altman_Z) else f"{row.Altman_Z:.3f}")
        k5,k6,k7,k8 = st.columns(4)
        k5.metric("STA", "—" if pd.isna(row.STA) else f"{row.STA:.3f}")
        k6.metric("SNOA", "—" if pd.isna(row.SNOA) else f"{row.SNOA:.3f}")
        k7.metric("Market cap", "—" if pd.isna(row.market_cap_usd) else f"${row.market_cap_usd/1e9:,.1f}B")
        k8.metric("Statement currency", str(row.get("financial_currency", "Unknown")) if pd.notna(row.get("financial_currency")) else "Unknown")
        st.markdown("#### Annual statement period ends")
        st.caption("y0 is the latest annual period in the export; y1 and y2 are the two preceding annual periods. Fiscal year-end dates vary by company.")
        period_dates = pd.DataFrame({
            "Period": ["Latest annual period (y0)", "Prior annual period (y1)", "Two years prior (y2)"],
            "Fiscal period end": [row.get("y0_period_end"), row.get("y1_period_end"), row.get("y2_period_end")],
        })
        period_dates["Fiscal period end"] = period_dates["Fiscal period end"].fillna("Not reported by Yahoo")
        st.dataframe(period_dates, width="stretch", hide_index=True)
        raw = [c for c in row.index if c.endswith("_y0") or c.startswith("F_")]
        st.dataframe(row[raw].rename("Value").to_frame(), width="stretch")

with conclusion_tab:
    st.subheader("Written investment conclusions")
    st.caption("These screen-based conclusions update with the sector, size, and threshold filters. They explain why the highest-ranked candidates merit further review; they are not personalized investment advice.")
    conclusion_buy, conclusion_sell = st.columns(2)

    with conclusion_buy:
        st.markdown('<h3 class="buy-title">BUY case</h3>', unsafe_allow_html=True)
        if buy.empty:
            st.write("No BUY candidate meets the current filters, so there is no qualifying BUY case to summarize.")
        else:
            top_buy = buy.iloc[0]
            peer_buy = base.loc[base[buy_inputs].notna().all(axis=1)]
            buy_percentiles = {
                "GPA": peer_buy["GPA"].rank(pct=True, method="average").get(top_buy.name, np.nan),
                "Book-to-Market": peer_buy["Book_to_Market"].rank(pct=True, method="average").get(top_buy.name, np.nan),
                "F_SCORE": peer_buy["F_SCORE"].rank(pct=True, method="average").get(top_buy.name, np.nan),
            }
            st.markdown(f"**{top_buy['company_name']} ({top_buy['ticker']}) — highest BUY composite under the current filters ({top_buy['BUY_score_live']:.0%}).**")
            st.write(
                f"GPA is {top_buy['GPA']:.3f} ({buy_percentiles['GPA']:.0%} percentile), "
                f"Book-to-Market is {top_buy['Book_to_Market']:.3f} ({buy_percentiles['Book-to-Market']:.0%} percentile), "
                f"and F_SCORE is {top_buy['F_SCORE']:.0f}/9 ({buy_percentiles['F_SCORE']:.0%} percentile) among companies with complete BUY inputs in the filtered peer set."
            )
            st.write(
                "**Conclusion:** Together, these results suggest strong gross profitability, relatively high book value compared with market value, and positive financial signals. "
                f"Based on this screen, I would consider {top_buy['ticker']} a candidate for further research as a potential investment. "
                "This ranking does not prove that its shares are undervalued or account for factors outside the measures used."
            )

    with conclusion_sell:
        st.markdown('<h3 class="sell-title">SELL risk case</h3>', unsafe_allow_html=True)
        if sell.empty:
            st.write("No SELL risk candidate meets the current filters, so there is no qualifying SELL case to summarize.")
        else:
            top_sell = sell.iloc[0]
            peer_sell = base.loc[base[sell_inputs].notna().all(axis=1)]
            sell_percentiles = {
                "STA": peer_sell["STA"].rank(pct=True, method="average").get(top_sell.name, np.nan),
                "SNOA": peer_sell["SNOA"].rank(pct=True, method="average").get(top_sell.name, np.nan),
                "Altman Z risk": 1 - peer_sell["Altman_Z"].rank(pct=True, method="average").get(top_sell.name, np.nan),
            }
            flagged_measures = [name for name, flag in [("STA", "STA_flag"), ("SNOA", "SNOA_flag"), ("Altman Z", "Altman_flag")] if bool(top_sell[flag])]
            unflagged_measures = [name for name, flag in [("STA", "STA_flag"), ("SNOA", "SNOA_flag"), ("Altman Z", "Altman_flag")] if not bool(top_sell[flag])]
            st.markdown(f"**{top_sell['company_name']} ({top_sell['ticker']}) — highest SELL risk composite under the current filters ({top_sell['SELL_score_live']:.0%}).**")
            st.write(
                f"STA is {top_sell['STA']:.3f} ({sell_percentiles['STA']:.0%} high-accrual risk percentile), "
                f"SNOA is {top_sell['SNOA']:.3f} ({sell_percentiles['SNOA']:.0%} high-SNOA risk percentile), "
                f"and Altman Z is {top_sell['Altman_Z']:.3f} ({sell_percentiles['Altman Z risk']:.0%} low-Z risk percentile)."
            )
            st.write(
                f"**Conclusion:** {', '.join(flagged_measures)} trigger the selected risk thresholds"
                + (f", while {', '.join(unflagged_measures)} do not." if unflagged_measures else ".")
                + f" The flagged measures point to possible earnings-quality or financial-distress concerns. Based on this screen, I would review {top_sell['ticker']} more closely before making an investment decision. This result does not establish that its shares are overvalued or, by itself, mean that investors should sell them."
            )

with method_tab:
    st.subheader("Course methodology")
    st.markdown("""
**BUY screen**

- **Gross Profitability (GPA):** (Revenue − Cost of Goods Sold) ÷ Total Assets. Higher values indicate more gross profit generated per asset dollar.
- **Book-to-Market (B/M):** Book Value of Common Equity ÷ Market Capitalization. Higher values indicate more book equity relative to market value; this is a value measure, not a guarantee of undervaluation.
- **F_SCORE:** Nine binary signals from the course slides: positive ROA, positive operating cash flow/assets, improving ROA, CFO greater than ROA, declining long-term-debt/assets, improving current ratio, no net equity offering, improving gross margin, and improving asset turnover. A complete score ranges from 0 to 9.
- **BUY composite:** Average of the within-peer-set percentile ranks for GPA, B/M, and F_SCORE. All three measures must be available.

**SELL screen**

- **Scaled Total Accruals (STA):** (Net Income − Operating Cash Flow) ÷ Total Assets. Higher values indicate earnings less supported by operating cash flow. This follows the course slide formula.
- **Scaled Net Operating Assets (SNOA):** (Operating Assets − Operating Liabilities) ÷ Total Assets. Operating assets = Total Assets − Cash. Operating liabilities = Total Assets − short-term debt − long-term debt − minority interest − preferred stock − common equity. Preferred stock is treated as zero only when the course slide allows it to be absent; other missing inputs remain missing.
- **Altman Z:** 0.012X1 + 0.014X2 + 0.033X3 + 0.006X4 + 0.999X5. X1 = Working Capital/Assets; X2 = Retained Earnings/Assets; X3 = EBIT/Assets; X4 = Market Equity/Book Total Liabilities; X5 = Sales/Assets. The course materials give 1.81 as the distress cutoff.
- **SELL red flags:** STA above its threshold, SNOA above its threshold, and Altman Z below its cutoff. The SELL composite separately ranks high STA, high SNOA, and low Altman Z risk percentiles. Companies need all three indicators to receive a composite rank.

**Data dates and limitations:** The source is a Yahoo Finance screen of US-listed securities, which can include foreign issuers. y0 is the latest annual period in the export; y1 and y2 are the two preceding annual periods. Fiscal year-end dates differ by company. Dates come from Yahoo Finance annual balance-sheet periods; for date fields that could not be matched to the exported total-assets values, the corresponding date from Yahoo’s returned annual-period list was used. All three annual dates are available for 994 companies. Six companies have only two annual periods in Yahoo’s available list, so no y2 date is shown for them. Some companies also have incomplete financial statements. Altman Z was developed for specific firm populations, so interpret it cautiously across industries. This educational screen is not investment advice.
    """)

# Full-sample sector mix is independent of the interactive recommendation filters.
st.subheader("Sector mix of the 1,000-company sample")
st.caption("Share of the original sample by sector; includes all 1,000 companies, including WDC, and does not change with the filters.")
sector_mix = (
    df.assign(sector_label=df["sector"].fillna("Not classified").astype(str).replace("", "Not classified"))
      .groupby("sector_label", as_index=False)
      .size()
      .rename(columns={"sector_label": "Sector", "size": "Companies"})
)
sector_mix["Share of sample (%)"] = sector_mix["Companies"] / len(df) * 100
sector_mix = sector_mix.sort_values("Share of sample (%)", ascending=True)
sector_fig = px.bar(
    sector_mix,
    x="Share of sample (%)",
    y="Sector",
    orientation="h",
    text="Share of sample (%)",
    hover_data={"Companies": True, "Share of sample (%)": ":.1f", "Sector": False},
    color_discrete_sequence=["#48b5a2"],
    title="Company count by sector as a percentage of the full sample",
)
sector_fig.update_traces(texttemplate="%{x:.1f}%", textposition="outside", cliponaxis=False)
sector_fig.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#111821", font_color="#e6edf3", height=480, showlegend=False)
sector_fig.update_xaxes(gridcolor="#273444", ticksuffix="%", range=[0, sector_mix["Share of sample (%)"].max() * 1.18 if not sector_mix.empty else 1])
sector_fig.update_yaxes(gridcolor="#273444")
st.plotly_chart(sector_fig, width="stretch")

# This chart responds to sector and size filters.
st.subheader("Filtered universe overview")
plot_df = base.dropna(subset=["GPA", "Book_to_Market", "F_SCORE"]).copy()
if not plot_df.empty:
    fig = px.scatter(plot_df, x="Book_to_Market", y="GPA", color="F_SCORE", hover_name="ticker", hover_data=["company_name","sector"], color_continuous_scale=["#8eb9b5","#173b60"], title="Profitability and book-to-market")
    fig.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#111821", font_color="#e6edf3", height=430)
    fig.update_xaxes(gridcolor="#273444", zerolinecolor="#3a4a5d")
    fig.update_yaxes(gridcolor="#273444", zerolinecolor="#3a4a5d")
    st.plotly_chart(fig, width="stretch")
else:
    st.write("No rows have all three BUY inputs under the current sector and size filters.")

st.subheader("Data coverage and source notes")
st.caption("Counts show how many companies have the reported inputs needed to calculate each measure. Availability varies by measure because company statements do not always include every required item; missing values are left blank.")
coverage = pd.DataFrame({"Measure":["GPA","Book-to-Market","STA","SNOA","Altman Z","Complete F_SCORE","BUY composite","SELL composite"],"Available companies":[int(recommendation_universe[c].notna().sum()) for c in ["GPA","Book_to_Market","STA","SNOA","Altman_Z","F_SCORE","BUY_score","SELL_score"]]})
st.dataframe(coverage, hide_index=True, width="stretch")

st.markdown("**Verified annual statement period-end dates**")
st.caption("y0 is the latest annual period in the export; y1 and y2 are the two preceding annual periods. Dates come from Yahoo Finance annual balance-sheet periods; where an exported total-assets match was unavailable, the date was taken from Yahoo’s returned annual-period list. Fiscal year ends vary by company.")
period_coverage = pd.DataFrame({
    "Annual period": ["Latest (y0)", "Prior (y1)", "Two years prior (y2)"],
    "Companies with a verified date": [
        int(recommendation_universe.get("y0_period_end", pd.Series(index=recommendation_universe.index, dtype=object)).notna().sum()),
        int(recommendation_universe.get("y1_period_end", pd.Series(index=recommendation_universe.index, dtype=object)).notna().sum()),
        int(recommendation_universe.get("y2_period_end", pd.Series(index=recommendation_universe.index, dtype=object)).notna().sum()),
    ],
})
period_coverage["Coverage"] = period_coverage["Companies with a verified date"].map(lambda n: f"{n:,}/1,000")
st.dataframe(period_coverage, hide_index=True, width="stretch")
st.caption("Yahoo Finance annual-period dates are available for all three periods for 994 companies. Six companies have only two annual periods listed, so y2 is shown as “Not reported by Yahoo.” No adjacent company dates were copied or estimated.")

measure_descriptions = [
    ("Gross Profitability (GPA)", "**Formula:** (Revenue − Cost of Goods Sold) ÷ Total Assets. It measures gross profit generated per dollar of assets; higher values score better in the BUY screen."),
    ("Book-to-Market (B/M)", "**Formula:** Book Value of Common Equity ÷ Market Capitalization. It compares accounting equity with the market value of the company; higher values can indicate a value stock, but do not prove undervaluation."),
    ("F_SCORE", "**Formula:** A sum of nine binary signals covering profitability, cash flow, improving returns, leverage, liquidity, equity issuance, gross margin, and asset turnover. Scores range from 0 to 9; higher scores indicate stronger financial performance."),
    ("Scaled Total Accruals (STA)", "**Formula:** (Net Income − Operating Cash Flow) ÷ Total Assets. Higher values mean a larger share of reported earnings is not supported by operating cash flow, which can flag earnings-quality risk."),
    ("Scaled Net Operating Assets (SNOA)", "**Formula:** (Operating Assets − Operating Liabilities) ÷ Total Assets. Higher values indicate more net operating assets accumulated relative to the asset base; this is used as an accounting-quality warning signal."),
    ("Altman Z-Score", "**Formula:** 0.012X1 + 0.014X2 + 0.033X3 + 0.006X4 + 0.999X5. It combines working capital, retained earnings, EBIT, market equity, liabilities, sales, and assets to screen for distress risk. The course materials use 1.81 as the distress cutoff; interpret it cautiously across industries."),
]
for title, description in measure_descriptions:
    with st.expander(title):
        st.markdown(description)
