# av-sim-vnv-evidence

When does simulation save real-world testing? This repository combines simulated and recorded outcomes of the same scenarios in one estimate, using prediction-powered inference (PPI) and its tuned version PPI++, and measures on real driving data how much real testing the simulation actually replaces.

**Technical report:** [`docs/technical_report.pdf`](docs/technical_report.pdf) ([Word](docs/technical_report.docx), [Markdown](docs/technical_report.md))

## Set-up

The inputs are the per-vehicle results of [av-sim-credibility](https://github.com/mohalbati/av-sim-credibility): 13,195 moving vehicles from 2,000 scenes of the Waymo Open Motion Dataset, each with a recorded outcome and a simulated outcome from closed-loop Waymax simulation with three simple driver models (default IDM, cautious IDM, constant speed). Since every vehicle has its recorded outcome, the true rate is known. The study hides the recorded outcome for all but n randomly chosen vehicles, estimates the rate with each method, and repeats this 1,000 times to measure error, interval coverage and the real-data saving.

## Results

| Setting | Recorded close-call rate | Simulated rate | Per-vehicle correlation ρ | Real data saved by PPI++ (n = 500) |
|---|---|---|---|---|
| IDM, cautious parameters | 4.10% | 4.26% | 0.06 | none |
| IDM, default parameters | 4.10% | 14.4% | 0.07 | about 1% |
| Constant speed | 4.10% | 16.3% | 0.17 | about 2% |

- Simulation-only estimates were far from the recorded rate for the default and constant-speed models, and their intervals almost never contained it. Fusion estimators corrected this.
- PPI++ was never meaningfully worse than real data alone, but saved little: at most about 10 to 12% in the best scenario family.
- The saving follows 1/(1 − ρ²) in the per-vehicle correlation. Halving the real data needs ρ of about 0.7, which a planted-agreement experiment at the same sample size confirmed.
- Matching the pooled rate is not enough: the cautious setting matched it best and agreed least, vehicle by vehicle.
- For the rare collision outcome (0.83%), normal-approximation intervals under-covered badly at small n for real-only and fused estimates alike (about 55 to 58% at n = 100). Exact or betting-style intervals are needed there.

The driver models are simple rule-based baselines. The results say what fusion is worth with such models; learned simulation agents can be evaluated with the same design.

The report also sets out how this fits a simulation validation plan organised by integration level (sensor, perception, other road users, planning, system) and states which levels were and were not covered.

## Reproduce

```bash
pip install -r requirements.txt
python tests/test_core.py                                                 # 4 tests
python scripts/fusion_study.py --agents-dir ../av-sim-credibility/results # needs the per-vehicle files
python scripts/make_figures.py                                            # figures from results/
python scripts/build_report.py                                            # Word and PDF (pandoc, Playwright)
```

`fusion_study.py` reads `womd_agents_<setting>.csv`, written by `av-sim-credibility/scripts/womd_pilot.py`. These files are derived from the Waymo Open Dataset and are not part of either repository. The aggregate results in `results/` are enough to rebuild every table and figure; with the fixed seed a rerun reproduces them exactly.

## Layout

```
src/simfusion/   fusion.py (estimators, gain, correlation ceiling, hierarchical pooling), levels.py
scripts/         fusion study, figures, report build
tests/           unit tests
results/         aggregate results
docs/            technical report and figures
```

## Data and licence

Results are derived from the [Waymo Open Dataset](https://waymo.com/open), used under its licence for non-commercial research. No scene data or per-vehicle values are redistributed. Code: MIT (see `LICENSE`).

Parts of the code were written with AI assistance; the study design, the runs, the checks and the interpretation are the author's.

Mohammad Albati, Ph.D.
