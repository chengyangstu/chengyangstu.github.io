// Lab 1: out = a*x + y. Kernel-only timing; transfers reported separately in exercises.
#include "common.cuh"
#include <vector>
#include <cmath>
#include <algorithm>

__global__ void saxpy(const float* x, const float* y, float* out, int n, float a) {
    for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < n; i += blockDim.x * gridDim.x)
        out[i] = a * x[i] + y[i];
}
int main(int argc, char** argv) {
    const int n = particle_count(argc, argv), repeats = 50;
    const size_t bytes = size_t(n) * sizeof(float);
    std::vector<float> x(n), y(n), out(n);
    for (int i = 0; i < n; ++i) { x[i] = (i % 127) * 0.01f; y[i] = (i % 31) * 0.02f; }
    float *dx, *dy, *dz;
    CUDA(cudaMalloc(&dx, bytes)); CUDA(cudaMalloc(&dy, bytes)); CUDA(cudaMalloc(&dz, bytes));
    CUDA(cudaMemcpy(dx, x.data(), bytes, cudaMemcpyHostToDevice));
    CUDA(cudaMemcpy(dy, y.data(), bytes, cudaMemcpyHostToDevice));
    const int blocks = std::min(4096, (n + 255) / 256);
    saxpy<<<blocks, 256>>>(dx, dy, dz, n, 2.0f);
    CUDA(cudaGetLastError()); CUDA(cudaDeviceSynchronize());
    cudaEvent_t begin, end;
    CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
    CUDA(cudaEventRecord(begin));
    for (int r = 0; r < repeats; ++r) saxpy<<<blocks, 256>>>(dx, dy, dz, n, 2.0f);
    CUDA(cudaGetLastError()); CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
    float ms; CUDA(cudaEventElapsedTime(&ms, begin, end));
    CUDA(cudaMemcpy(out.data(), dz, bytes, cudaMemcpyDeviceToHost));
    double error = 0;
    for (int i = 0; i < n; ++i) error = std::max(error, std::abs(double(out[i]) - (2.0 * x[i] + y[i])));
    std::printf("N=%d kernel_ms=%.6f effective_GBps=%.3f max_abs_error=%.3g\n",
        n, ms / repeats, 3.0 * bytes * repeats / (ms * 1e6), error);
    CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
    CUDA(cudaFree(dx)); CUDA(cudaFree(dy)); CUDA(cudaFree(dz));
    return error < 2e-6 ? 0 : 1;
}
