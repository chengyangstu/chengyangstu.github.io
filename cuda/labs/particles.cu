// Lab 2: nonrelativistic Boris rotation, then independent periodic CIC charge deposition.
// This is a kernel verification lab, NOT a self-consistent electromagnetic PIC solver.
#include "common.cuh"
#include <vector>
#include <cmath>
#include <algorithm>

__global__ void rotate(float* vx, float* vy, int n, float dt) {
    const float t = -0.5f * dt; // q/m=-1, Bz=1, E=0, vz unchanged.
    const float s = 2 * t / (1 + t * t);
    for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < n; i += blockDim.x * gridDim.x) {
        const float x = vx[i], y = vy[i];
        const float px = x + y * t, py = y - x * t;
        vx[i] = x + py * s; vy[i] = y - px * s;
    }
}
__global__ void deposit(const float* x, float* rho, int n, int cells, float length, float weight) {
    for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < n; i += blockDim.x * gridDim.x) {
        const float wrapped = x[i] - floorf(x[i] / length) * length;
        const float g = wrapped * cells / length;
        const int j = int(floorf(g)); const float f = g - j;
        atomicAdd(&rho[j % cells], weight * (1 - f));
        atomicAdd(&rho[(j + 1) % cells], weight * f);
    }
}
int main(int argc, char** argv) {
    const int n = particle_count(argc, argv), cells = 128, steps = 1000;
    const float dt = 0.02f, length = 16.0f, dx = length / cells;
    const size_t bytes = size_t(n) * sizeof(float);
    std::vector<float> x(n), vx(n, 1.0f), vy(n, 0.0f), rho(cells);
    for (int i = 0; i < n; ++i) x[i] = float((i % 8191) + 0.5) / 8191 * length;
    float *gx, *gvx, *gvy, *gr;
    CUDA(cudaMalloc(&gx, bytes)); CUDA(cudaMalloc(&gvx, bytes));
    CUDA(cudaMalloc(&gvy, bytes)); CUDA(cudaMalloc(&gr, cells * sizeof(float)));
    CUDA(cudaMemcpy(gx, x.data(), bytes, cudaMemcpyHostToDevice));
    CUDA(cudaMemcpy(gvx, vx.data(), bytes, cudaMemcpyHostToDevice));
    CUDA(cudaMemcpy(gvy, vy.data(), bytes, cudaMemcpyHostToDevice));
    int blocks = std::min(4096, (n + 255) / 256);
    for (int s = 0; s < steps; ++s) rotate<<<blocks, 256>>>(gvx, gvy, n, dt);
    CUDA(cudaGetLastError()); CUDA(cudaDeviceSynchronize());
    CUDA(cudaMemcpy(vx.data(), gvx, bytes, cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(vy.data(), gvy, bytes, cudaMemcpyDeviceToHost));
    double speed_error = 0, phase_error = 0;
    const double angle = 2 * steps * std::atan(double(dt) / 2);
    for (int i = 0; i < n; ++i) {
        speed_error = std::max(speed_error, std::abs(double(vx[i])*vx[i] + double(vy[i])*vy[i] - 1));
        phase_error = std::max(phase_error, std::hypot(vx[i] - std::cos(angle), vy[i] - std::sin(angle)));
    }
    CUDA(cudaMemset(gr, 0, cells * sizeof(float)));
    // Electron density normalized to mean -1. Divide macro charge by cell width.
    const float weight = -length / (n * dx);
    deposit<<<blocks, 256>>>(gx, gr, n, cells, length, weight);
    CUDA(cudaGetLastError()); CUDA(cudaDeviceSynchronize());
    CUDA(cudaMemcpy(rho.data(), gr, cells * sizeof(float), cudaMemcpyDeviceToHost));
    double total = 0, grid_error = 0; std::vector<double> ref(cells, 0);
    for (int i = 0; i < n; ++i) {
        const float g = x[i] * cells / length;
        const int j = int(std::floor(g)); const float f = g - j;
        ref[j % cells] += weight * (1 - f); ref[(j + 1) % cells] += weight * f;
    }
    for (int j = 0; j < cells; ++j) { total += rho[j] * dx; grid_error = std::max(grid_error, std::abs(rho[j] - ref[j])); }
    std::printf("speed2_error=%.3g discrete_phase_error=%.3g charge_error=%.3g grid_error=%.3g\n",
        speed_error, phase_error, std::abs(total + length) / length, grid_error);
    CUDA(cudaFree(gx)); CUDA(cudaFree(gvx)); CUDA(cudaFree(gvy)); CUDA(cudaFree(gr));
    // Float atomics are order dependent. Use the documented 65536-particle lab baseline.
    return speed_error < 3e-4 && phase_error < 3e-4 && std::abs(total + length) / length < 2e-3 && grid_error < 2e-3 ? 0 : 1;
}
