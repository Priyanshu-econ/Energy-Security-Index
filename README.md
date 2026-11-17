# Energy Security Index (ESI)

A composite index of energy security for 40 countries, 2000–2024, built on the four As:
Availability, Accessibility, Affordability and Acceptability.

**Dashboard:** https://priyanshu-econ.github.io/Energy-Security-Index/

The site has an interactive dashboard (all countries, one country, comparisons), downloads of the
index, dimension scores and indicators (Excel and CSV), the methodology PDF and the paper.

## Cite

Citation is required whenever you use the index, its scores, its figures or the processed data.

- Chavda, P. (2026). Geopolitical Risk and Energy Security: Quantile and Logit Evidence from a
  Composite Index. Job market paper, Pandit Deendayal Energy University.
- Chavda, P. (2026). Energy Security Index (ESI), 40 countries, 2000-2024. Version 1.0.
  https://priyanshu-econ.github.io/Energy-Security-Index/

## Copyright and licence

© 2026 Priyanshu Chavda. The website, text, figures, methodology document and paper are the
author's copyright, all rights reserved. The ESI data (index, dimension and indicator scores) are
released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0): you may reuse
them with attribution, by citing the paper and the dataset above. The raw indicators remain under
their sources' terms (World Bank, Our World in Data, U.S. EIA).

## Method in brief

1. Energy CPI inflation is winsorised at its pooled 1st and 99th percentiles.
2. Each indicator is min–max normalised over all countries and years (direction-adjusted).
3. Each dimension is the arithmetic mean of its two indicators.
4. The ESI is the geometric mean of the four dimensions (equal weights).

## Rebuild

```
python code/build_esi.py               # data/esi.json and every file in downloads/
python code/docs/make_methodology.py   # downloads/ESI_methodology.pdf (needs Playwright)
```

Inputs: `code/esi_inputs.csv` (raw indicators). Sensitivity statistics for z-score and PCA:
`code/robustness.json`.
