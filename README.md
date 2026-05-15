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
