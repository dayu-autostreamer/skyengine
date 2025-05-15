# Flexible Job-shop Instances

This repository contains instances of the flexible job shop scheduling problem (FJSSP).

WARNING! Data may not be accurate. If you find an error, please report an issue. Always refer to the original paper.

## Instances

Description in [instances.json](instances.json).

- `brandimarte` (15 instances from [1])
- `hurink` (3 × 66 instances from [2])
- `dauzere` (18 instances from [3])
- `barnes` (21 instances from [4])
- `kacem` (4 instances from [5])
- `fattahi` (20 instances from [6])
- `behnke` (60 instances from [7])

Data about bounds are from [7] and [8].

## Format

- First line: `<number of jobs> <number of machines>`
- Then one line per job: `<number of operations>` and then, for each operation, `<number of machines for this operation>` and for each machine, a pair `<machine> <processing time>`.
- Machine index starts at 0.

## References

1. P. Brandimarte. [Routing and Scheduling in a Flexible Job Shop by Tabu Search](https://doi.org/10.1007/BF02023073). Annals of Operations Research, 41(3):157–183, 1993.
2. J. Hurink, B. Jurisch, and M. Thole. [Tabu search for the job-shop scheduling problem with multi-purpose machines](https://doi.org/10.1007/BF01719451). Operations-Research-Spektrum, vol. 15, no. 4, pp. 205–215, 1994.
3. S. Dauzère-Pérès and J. Paulli. Solving the General Multiprocessor Job-Shop Scheduling Problem. Technical report, Rotterdam School of Management, Erasmus Universiteit Rotterdam, 1994.
4. J. B. Chambers and J. W. Barnes. [Flexible Job Shop Scheduling by Tabu Search](https://doi.org/10.1080/07408179508936739). The University of Texas, Austin, TX, Technical Report Series ORP96-09, Graduate Program in Operations Research and Industrial Engineering, 1996.
5. I. Kacem, S. Hammadi, and P. Borne. [Pareto-Optimality Approach for Flexible, Job-Shop Scheduling Problems: Hybridization of Evolutionary Algorithms and Fuzzy Logic](https://doi.org/10.1016/S0378-4754%2802%2900019-8). Mathematics and Computers in Simulation, 60(3-5):245–276, 2002.
6. P. Fattahi, M. S. Mehrabad, and F. Jolai. [Mathematical Modeling and Heuristic Approaches to Flexible Job Shop Scheduling Problems](https://doi.org/10.1007/s10845-007-0026-8). Journal of Intelligent Manufacturing, 18(3):331–342, 2007.
7. Behnke, D., & Geiger, M. J. (2012). Test instances for the flexible job shop scheduling problem with work centers. Arbeitspapier/Research Paper/Helmut-Schmidt-Universität, Lehrstuhl für Betriebswirtschaftslehre, insbes. Logistik-Management.
8. A. Schutt, T. Feydy, and P. J. Stuckey, “Scheduling Optional Tasks with Explanation,” in Principles and Practice of Constraint Programming, Berlin, Heidelberg, 2013, vol. 8124, pp. 628–644.


实例描述见 instances.json 文件。
brandimarte（来自 [1] 的 15 个实例）
hurink（来自 [2] 的 3×66 个实例）
dauzere（来自 [3] 的 18 个实例）
barnes（来自 [4] 的 21 个实例）
kacem（来自 [5] 的 4 个实例）
fattahi（来自 [6] 的 20 个实例）
behnke（来自 [7] 的 60 个实例）
边界数据来自 [7] 和 [8]。
格式
第一行：<作业数量> < 机器数量 >
然后每行对应一个作业：<工序数量>，接着对于每个工序，给出 < 该工序可使用的机器数量 >，对于每台机器，给出一对数据 < 机器编号 > < 加工时间 >。
机器编号从 0 开始。