"""Build the Energy Security Index (ESI) and every file the website serves.

Input : code/esi_inputs.csv  (one row per country-year, the 8 raw indicators)
Output: esi/data/esi.json        (data for the dashboard)
        esi/downloads/*.csv, *.xlsx

Method (see the methodology PDF for the reasoning):
  0. Energy CPI inflation is winsorised at the pooled 1st and 99th percentiles before normalisation
     (skewness 30, kurtosis 934: one hyperinflation episode would otherwise compress every other score).
  1. Min-max normalisation of each indicator over the pooled panel (all countries, all years),
     direction-adjusted so that 1 = most secure and 0 = least secure.
  2. Each dimension = arithmetic mean of its two normalised indicators (weight 0.5 each).
  3. ESI = geometric mean of the four dimensions (weight 0.25 each),
     so every indicator carries an overall weight of 0.125.
  4. Sensitivity: arithmetic aggregation, and 1,000 random dimension weightings (seed 123).

Run from the repository root:  python code/build_esi.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "1.0"
WINSORISE = {"energy_cpi_inflation": (0.01, 0.99)}
RELEASED = "2026-11"
ROOT = Path(__file__).resolve().parents[1]
SITE = "https://priyanshu-econ.github.io/Energy-Security-Index/"
CITE_PAPER = ("Chavda, P. (2026). Geopolitical Risk and Energy Security: Quantile and Logit "
              "Evidence from a Composite Index. Job market paper, Pandit Deendayal Energy University.")
CITE_DATA = (f"Chavda, P. (2026). Energy Security Index (ESI), 40 countries, 2000-2024. "
             f"Version {VERSION}. {SITE}")

# key, label, dimension, direction (+1 higher is more secure), unit, source
INDICATORS = [
    ("energy_use", "Energy use per capita", "Availability", +1, "kWh per person",
     "Our World in Data (primary energy consumption per capita)"),
    ("self_sufficiency", "Energy self-sufficiency", "Availability", +1, "ratio of production to consumption",
     "U.S. Energy Information Administration, International Energy Statistics"),
    ("access_electricity", "Access to electricity", "Accessibility", +1, "% of population",
     "World Bank, World Development Indicators (EG.ELC.ACCS.ZS)"),
    ("td_losses", "Power transmission and distribution losses", "Accessibility", -1, "% of output",
     "World Bank, World Development Indicators (EG.ELC.LOSS.ZS)"),
    ("gdppc_growth", "GDP per capita growth", "Affordability", +1, "annual %",
     "World Bank, World Development Indicators (NY.GDP.PCAP.KD.ZG)"),
    ("energy_cpi_inflation", "Energy CPI inflation", "Affordability", -1, "annual %",
     "World Bank, Global Database of Inflation (energy CPI inflation)"),
    ("ghg_per_capita", "GHG emissions per capita", "Acceptability", -1, "t CO2e per person",
     "World Bank, World Development Indicators (EN.GHG.ALL.PC.CE.AR5)"),
    ("energy_intensity", "Energy intensity", "Acceptability", -1, "MJ per $ of GDP (2021 PPP)",
     "World Bank, World Development Indicators (EG.EGY.PRIM.PP.KD)"),
]
DIMENSIONS = ["Availability", "Accessibility", "Affordability", "Acceptability"]


def build():
    df = pd.read_csv(ROOT / "code" / "esi_inputs.csv", dtype={"iso_num": str})
    df = df.sort_values(["country", "year"]).reset_index(drop=True)

    # 1. Pooled, direction-adjusted min-max normalisation
    for key, (ql, qh) in WINSORISE.items():
        df[key + "_winsorised"] = df[key].clip(df[key].quantile(ql), df[key].quantile(qh))
    for key, _, _, sign, _, _ in INDICATORS:
        x = df[key + "_winsorised"] if key in WINSORISE else df[key]
        lo, hi = x.min(), x.max()
        df[key + "_score"] = (x - lo) / (hi - lo) if sign > 0 else (hi - x) / (hi - lo)

    # 2. Dimensions: arithmetic mean of the two indicator scores
    for dim in DIMENSIONS:
        keys = [k for k, _, d, *_ in INDICATORS if d == dim]
        df[dim.lower()] = df[[k + "_score" for k in keys]].mean(axis=1)
    dims = [d.lower() for d in DIMENSIONS]

    # 3. ESI: geometric mean of the four dimensions
    df["esi"] = np.prod(df[dims].values, axis=1) ** 0.25
    df["esi_rank"] = df.groupby("year")["esi"].rank(ascending=False, method="min").astype(int)
    for d in dims:
        df[d + "_rank"] = df.groupby("year")[d].rank(ascending=False, method="min").astype(int)

    # 4. Sensitivity
    df["esi_arithmetic"] = df[dims].mean(axis=1)
    np.random.seed(123)
    sims = np.empty((len(df), 1000))
    logd = np.log(df[dims].values)
    for s in range(1000):
        w = np.random.random(4)
        w = w / w.sum()
        sims[:, s] = np.exp(logd @ w)
    df["esi_mc_mean"] = sims.mean(axis=1)
    df["esi_mc_p05"] = np.percentile(sims, 5, axis=1)
    df["esi_mc_p95"] = np.percentile(sims, 95, axis=1)
    return df


def write(df):
    dl = ROOT / "downloads"
    dl.mkdir(exist_ok=True)
    ids = ["country", "iso3", "year"]
    dims = [d.lower() for d in DIMENSIONS]
    r6 = lambda t: t.round(6)

    # Public downloads: the ESI and the four dimension scores only
    scores = r6(df[ids + ["esi"] + dims])

    code = [("country", "Country name", "", ""), ("iso3", "ISO 3166-1 alpha-3 code", "", ""),
            ("year", "Calendar year", "", ""),
            ("esi", "Energy Security Index: overall score combining the four dimensions", "0 to 1", "higher is more secure")]
    for d in DIMENSIONS:
        code.append((d.lower(), f"{d} dimension score", "0 to 1", "higher is more secure"))
    codebook = pd.DataFrame(code, columns=["variable", "description", "unit", "direction"])

    scores.to_csv(dl / "esi_scores.csv", index=False)
    codebook.to_csv(dl / "esi_codebook.csv", index=False)
    for old in ("esi_indicators.csv", "esi_sensitivity.csv"):
        (dl / old).unlink(missing_ok=True)

    readme = pd.DataFrame({"Energy Security Index (ESI)": [
        f"Version {VERSION}, released {RELEASED}. 40 countries, 2000-2024.",
        "",
        "Citation is required when you use these data. Please cite both:",
        CITE_PAPER,
        CITE_DATA,
        "",
        "Copyright (c) 2026 Priyanshu Chavda. The ESI data are released under the Creative Commons Attribution 4.0",
        "International licence (CC BY 4.0): you may reuse them with attribution (cite the paper and the dataset).",
        "",
        "Sheets: Scores (the ESI and its four dimensions: Availability, Accessibility, Affordability, Acceptability), Codebook.",
        f"Website and methodology: {SITE}",
    ]})
    with pd.ExcelWriter(dl / f"ESI_dataset_v{VERSION}.xlsx", engine="openpyxl") as xw:
        readme.to_excel(xw, sheet_name="Read me", index=False)
        scores.to_excel(xw, sheet_name="Scores", index=False)
        codebook.to_excel(xw, sheet_name="Codebook", index=False)
        for ws in xw.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 14 if ws.title != "Read me" else 110
        cb = xw.book["Codebook"]
        for letter, w in zip("ABCD", (16, 70, 12, 24)):
            cb.column_dimensions[letter].width = w

    # Compact JSON for the dashboard
    years = sorted(df.year.unique().tolist())
    keys = ["esi", "esi_rank"] + dims + [k for key, *_ in INDICATORS for k in (key, key + "_score", key + "_filled")] \
        + ["esi_mc_p05", "esi_mc_p95"]
    countries = []
    for (name, iso3, num), g in df.groupby(["country", "iso3", "iso_num"]):
        g = g.set_index("year").reindex(years)
        countries.append({"name": name, "iso3": iso3, "num": num,
                          "v": {k: [None if pd.isna(x) else (int(x) if k.endswith(("_rank", "_filled")) else round(float(x), 5))
                                    for x in g[k]] for k in keys}})
    dims_l = dims
    rk = lambda col: df.groupby("year")[col].rank(ascending=False, method="average")
    spear = lambda a, b: float(np.corrcoef(rk(a), rk(b))[0, 1])
    shift = (rk("esi") - rk("esi_mc_mean")).abs()
    sens_stats = {
        "pearson_arith": round(float(df.esi.corr(df.esi_arithmetic)), 3),
        "spearman_arith": round(float(df.esi.corr(df.esi_arithmetic, method="spearman")), 3),
        "base_mean": round(float(df.esi.mean()), 4), "base_sd": round(float(df.esi.std()), 4),
        "mc_mean": round(float(df.esi_mc_mean.mean()), 4), "mc_sd": round(float(df.esi_mc_mean.std()), 4),
        "shift_mean": round(float(shift.mean()), 2), "shift_max": int(round(shift.max())), "shift_sd": round(float(shift.std()), 3),
        "filled_share": round(float(df[[k + "_filled" for k, *_ in INDICATORS]].values.mean() * 100), 1),
    }
    # z-score and PCA comparisons come from the paper's sensitivity notebook (ESI Uncertainty.ipynb)
    rob = ROOT / "code" / "robustness.json"
    if rob.exists():
        sens_stats.update(json.loads(rob.read_text()))
    meta = {"version": VERSION, "sensitivity": sens_stats, "released": RELEASED, "years": years, "cite_paper": CITE_PAPER, "cite_data": CITE_DATA,
            "dimensions": DIMENSIONS,
            "indicators": [dict(key=k, label=l, dim=d, dir=s, unit=u, source=src) for k, l, d, s, u, src in INDICATORS]}
    (ROOT / "data" / "esi.json").write_text(json.dumps({"meta": meta, "countries": countries}, separators=(",", ":")))


if __name__ == "__main__":
    data = build()
    write(data)
    latest = data[data.year == data.year.max()].sort_values("esi_rank")
    print(latest[["country", "esi", "esi_rank"]].head(10).to_string(index=False))
