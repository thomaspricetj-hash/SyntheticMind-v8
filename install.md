\# Installation Guide — SyntheticMind v8

© 2026 Thomas Price — Licensed under GPLv3



This document provides installation and setup instructions for the

SyntheticMind v8 cognitive AI system. The system includes multiple subsystems:

the orchestrator, helper mesh, physics and math engines, memory architecture,

world‑model, simulation engine, debate modules, strategy planners, taskgraph

engine, tool learning, vision subsystem, and the BitDrop compression kernel.



\---



\## 1. System Requirements



\### Operating System

\- Windows 10/11 (recommended)

\- Linux (Ubuntu 20.04+)

\- macOS (Intel or Apple Silicon)



\### Python

\- Python \*\*3.10 – 3.13\*\* supported  

\- Recommended: Python \*\*3.12+\*\*



\### Hardware

\- 16 GB RAM minimum  

\- 32 GB RAM recommended  

\- GPU optional (system is CPU‑compatible)



\---



\## 2. Clone the Repository



git clone https://github.com/<your-username>/syntheticmind-v8.git

cd s

\---



\## 3. Create a Virtual Environment (Recommended)



\### Windows

yntheticmind-v8





\---



\## 3. Create a Virtual Environment (Recommended)



\### Windows



python -m venv venv

venv\\Scripts\\activate





\### Linux / macOS



python3 -m venv venv

source venv/bin/activate





\---



\## 4. Install Dependencies



SyntheticMind v8 uses a modular architecture with multiple subsystems.  

Install all required Python packages:





pip install -r requirements.txt





If you do not yet have a `requirements.txt`, generate one from your environment:





\---



\## 5. Running SyntheticMind v8



The main entry point is:





\---



python main.py





This initializes:

\- the orchestrator  

\- helper mesh  

\- memory system  

\- physics/math engines  

\- world model  

\- runtime pipeline  



\---



\## 6. Directory Overview



The core system lives under:



syntheticmind/





Key subsystems include:



\- `ai/metamodel/` — orchestrator, router, model‑book, self‑audit  

\- `ai/helpers/` — conversation, reasoning, summarization, safety, hallucination, code, logic, compression, physics, math, domain routing  

\- `ai/math/` — math engine, symbolic CAS, detectors, solver  

\- `ai/physics/` — physics engine, circuits, symbolic physics  

\- `ai/memory/` — episodic, semantic, vector store  

\- `ai/world\_model/` — dynamics, extraction, simulation  

\- `ai/simulation/` — counterfactual rollouts  

\- `ai/debate/` — multi‑agent debate engine  

\- `ai/strategy/` — goal manager, tree planner  

\- `ai/taskgraph/` — graph‑structured execution  

\- `ai/tools/` — tool registry, python tool, file tool  

\- `ai/tool\_learning/` — generator, infer, tester  

\- `ai/vision/` — vision client + processor  

\- `bitdrop\_core/` — BitDrop compression kernel  

\- `benchmark\_results/` — benchmark logs and JSON outputs  



\---



\## 7. Running Benchmarks



SyntheticMind includes a built‑in benchmark suite:



python syntheticmind/ai/benchmark/benchmark\_smart\_runner\_v1.py





Benchmark results are written to:



benchmark\_results/





\---



\## 8. Updating the System



To pull updates:



git pull origin main





If dependencies changed:

pip install -r requirements.txt





\---



\## 9. License



SyntheticMind v8 is released under the \*\*GNU GPLv3\*\* license.  

See the `LICENSE` file for full terms.



\---



\## 10. Support



Maintainer: \*\*Thomas Price\*\*  

Project: SyntheticMind v8 — Cognitive AI System  

Location: Crestwood, KY



For issues, open a GitHub Issue in the repository.





\---



\## 9. License



SyntheticMind v8 is released under the \*\*GNU GPLv3\*\* license.  

See the `LICENSE` file for full terms.



\---



\## 10. Support



Maintainer: \*\*Thomas Price\*\*  

Project: SyntheticMind v8 — Cognitive AI System  

Location: Crestwood, KY



For issues, open a GitHub Issue in the repository.









