This project implements a **Multi-Objective OSPF Weight Optimization** framework designed for modern IP backbone networks. Using **Mixed-Integer Linear Programming (MILP)** and metaheuristic algorithms, the system optimizes network traffic distribution by precisely tuning OSPF link weights.

##  Core Optimization Models
[cite_start]The framework evaluates four distinct operational objectives[cite: 21, 22, 23, 37]:

* [cite_start]**Model A (Min-MLU)**: Minimizes the Maximum Link Utilization (MLU) to reach the theoretical performance upper bound[cite: 21, 37].
* [cite_start]**Model B (Min-Cost)**: Minimizes total routing cost by preferring shorter, low-weight paths[cite: 22, 37].
* [cite_start]**Model C (SLA-Constrained)**: Optimizes cost while enforcing a hard 85% link utilization cap as a Service Level Agreement (SLA) safety net[cite: 22, 37, 439].
* [cite_start]**Model D (Sparse/ROI)**: **Project Highlight.** Limits weight modifications ($\Delta \le 5$) to achieve near-optimal congestion relief with minimal operational risk[cite: 23, 37, 451].

##  Key Findings & ROI
* [cite_start]**High Efficiency**: Model D captures **93.6%** of the performance gains of a full reconfiguration (Model A) using an average of only **2.4 weight changes**[cite: 26, 632].
* [cite_start]**Massive ROI**: In "single-bottleneck" topologies like *Airtel*, Model D achieves a **48.8x efficiency ratio** compared to Model A[cite: 778].
* [cite_start]**Diminishing Returns**: Sensitivity analysis proves that the first 3–5 weight changes capture over **88%** of the maximum possible MLU reduction[cite: 27, 803].

##  Getting Started

### 1. Prerequisites
* [cite_start]**Gurobi Optimizer**: Ensure you have a valid Gurobi license installed.
* **Python 3.8+**

### 2. Environment Setup
It is highly recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py --config configs/default.yaml
streamlit run app.py
