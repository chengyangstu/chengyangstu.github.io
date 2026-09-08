# 教材练习代码

这些独立的小程序配合 [CUDA 与 GPU 高性能等离子体计算](https://chengyangstu.github.io/cuda/) 使用。
代码为本站原创教学实现。`pic1d.py` 是完整的 1D1V 静电 PIC 参考程序；CUDA 文件是独立内核练习，并非完整电磁重联程序。

## CPU 参考：Python 3 + NumPy

```sh
python -m pip install numpy
python check.py
python pic1d.py --case cold --output cold.csv
python pic1d.py --case twostream --ppc 256 --steps 1000 --output twostream.csv
python analyze.py twostream.csv --start 5 --end 15
```

输出采用排他创建；换文件名重跑，保留参数扫描数据。拟合区间只是操作示例，必须先画幅值曲线确认线性增长区。Landau 阻尼需足够粒子数、多个随机种子及峰值包络拟合，不保证默认小算例给出精确阻尼率。

`check.py` 运行冷等离子体、两种热分布初始化、电荷与泊松检查，以及已知指数增长率的拟合检查。单独运行静电程序自检也可以使用 `python pic1d.py --check`。

## CUDA：Toolkit + 支持的 C++ 编译器

在包含 `common.cuh` 的目录执行（Windows 的可执行文件为 `.exe`）：

```sh
nvcc -O3 -lineinfo -std=c++17 saxpy.cu -o saxpy
nvcc -O3 -lineinfo -std=c++17 particles.cu -o particles
./saxpy 1048576
./saxpy 1048583
./particles 65536
compute-sanitizer --tool memcheck ./particles 65536
```

`saxpy` 输出内核平均耗时、算法有效带宽与最大误差；不含传输和初始化时间，不能当作端到端加速比。`particles` 检查纯磁场 Boris 旋转与独立 CIC 电荷沉积。大粒子数下 FP32 原子累加误差可能超出教学基线阈值，须改进归约/精度并量化，不可直接放宽误差冒充验证。

教材发布时 CPU 参考检查已运行；本机未发现 `nvcc`，CUDA 示例尚未完成编译与 GPU 执行验证。请在配置 Toolkit 后完成编译、数值检查及 Compute Sanitizer 检查，再开始性能实验。此限制在网页中同样注明。

## 多 GPU / 云端：MPI + CUDA

`halo_mpi.cu` 是完整的周期一维扩散 halo 交换训练，用离散 Fourier 解检查结果。它不包含粒子迁移或完整 PIC。
服务器安装兼容的 CUDA、MPI、CMake 后，在当前目录运行：

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
mpirun -np 1 ./build/halo_mpi 256 100
mpirun -np 2 ./build/halo_mpi 256 100
mpirun -np 4 ./build/halo_mpi 256 100
mpirun -np 8 ./build/halo_mpi 256 100
```

需要相应数量 GPU；默认使用页锁定主机中转。打印的主机名和 PCI 标识用于核对每个 rank 的物理 GPU 绑定。仅在 CUDA-aware MPI 已验证的环境中追加 `--device`。Slurm 环境按站点配置改用 `srun`；不要盲目嵌套启动器。该示例交换的消息很小，首先用于正确性训练；强/弱扩展性能训练需扩大局部网格和消息。

此多卡示例尚未完成编译或服务器实测。完整粒子迁移、沉积贡献归并、跨域连续性、重联多卡对照和检查点训练详见教材第十九章。
