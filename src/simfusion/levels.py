"""Simulation validation by integration level: what is compared, with which data and metric, and what claim it supports.

Each level's evidence feeds the next: a system-level claim ("simulated miles may support clearance of family F")
holds only if every level below it is validated for the same operational design domain and scenario family.
`STATUS` records what the companion study (av-sim-credibility) and this repository cover; the rest is a plan.
"""
LEVELS = [
    {"level": "L1 Sensor", "sim_output": "camera / lidar / radar returns",
     "real_reference": "recorded sensor logs of the same scene (re-simulated or neurally rendered)",
     "metrics": "per-pixel / per-point error, lidar range and intensity distributions, radar RCS; detection-relevant statistics",
     "comparison": "paired residuals per sensor and condition (weather, lighting, range); distribution distance",
     "claim": "sensor model fidelity is good enough that perception outputs do not change beyond tolerance"},
    {"level": "L2 Perception", "sim_output": "detections, tracks, classes on simulated sensor data",
     "real_reference": "perception run on the real logs + labels",
     "metrics": "detection / tracking metrics (AP, recall by range and class, false-positive rate), latency",
     "comparison": "same scenes, perception on real vs simulated sensors; difference in metrics with intervals",
     "claim": "perception behaves the same on simulated input, so planning tests do not hinge on sim artefacts"},
    {"level": "L3 Agents (behaviour of other road users)", "sim_output": "trajectories of simulated vehicles, pedestrians, cyclists",
     "real_reference": "logged trajectories of the same agents (WOMD in the companion study)",
     "metrics": "min TTC, conflict rate (TTC < 1.5 s), collisions, attribution; distribution-realism features",
     "comparison": "paired bias delta / scatter omega, tail ratio R, area metric, per scenario family",
     "claim": "simulated traffic produces conflicts at the real frequency and severity, per family"},
    {"level": "L4 Planning in closed loop", "sim_output": "AV plan and resulting interaction outcomes",
     "real_reference": "on-road / log-replay outcomes for the same scenario families",
     "metrics": "safety-relevant outcomes (collision, near miss, rule violations), comfort; disengagement-type events",
     "comparison": "paired re-simulation of logged scenarios; per-family outcome rates; per-scenario agreement",
     "claim": "planner outcomes in simulation predict on-road outcomes per family within quantified uncertainty"},
    {"level": "L5 Full pipeline / system", "sim_output": "end-to-end outcome rates over the scenario mix",
     "real_reference": "fleet exposure and event data (miles, events by severity)",
     "metrics": "collision / injury / fatality rate per mile; confidence bounds",
     "comparison": "fusion estimators (PPI, control variates, power prior, hierarchical model) with exposure weighting",
     "claim": "simulated miles count toward the safety case with a stated weight and uncertainty"},
]
STATUS = {"L1 Sensor": "plan", "L2 Perception": "plan", "L3 Agents (behaviour of other road users)": "demonstrated (WOMD + Waymax)",
          "L4 Planning in closed loop": "partly (closed-loop agents; AV replays its log)", "L5 Full pipeline / system": "demonstrated (estimators on L3 outcomes)"}
