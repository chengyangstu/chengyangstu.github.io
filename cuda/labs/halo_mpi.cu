// Multi-GPU lab: periodic 1D diffusion, exact discrete Fourier-mode verification.
// Default: pinned host staging. --device requires a verified CUDA-aware MPI installation.
// This tests halo exchange, NOT particle migration or a full PIC cycle.
#include <mpi.h>
#include <cuda_runtime.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cerrno>
#include <vector>
#include <algorithm>

void check_cuda(cudaError_t e, const char* file, int line) {
    if (e != cudaSuccess) {
        std::fprintf(stderr, "%s:%d: %s\n", file, line, cudaGetErrorString(e));
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}
#define CUDA(x) check_cuda((x), __FILE__, __LINE__)
int positive(const char* arg, int maximum) {
    char* end; errno = 0; long n = std::strtol(arg, &end, 10);
    if (errno || end == arg || *end || n < 1 || n > maximum) {
        std::fprintf(stderr, "Invalid integer argument: %s\n", arg);
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    return int(n);
}
__global__ void stencil(const float* u, float* next, int begin, int end) {
    for (int i = begin + blockIdx.x * blockDim.x + threadIdx.x; i <= end; i += blockDim.x * gridDim.x)
        next[i] = u[i] + 0.2f * (u[i-1] - 2*u[i] + u[i+1]);
}
int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank, size; MPI_Comm_rank(MPI_COMM_WORLD, &rank); MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (argc > 4 || (argc == 4 && std::strcmp(argv[3], "--device"))) {
        if (!rank) std::fprintf(stderr, "Usage: halo_mpi [global_cells] [steps] [--device]\n");
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    int global = argc > 1 ? positive(argv[1], 10000000) : 256;
    int steps = argc > 2 ? positive(argv[2], 100000) : 100;
    bool direct = argc == 4;
    if (global % size || global / size < 2) {
        if (!rank) std::fprintf(stderr, "global_cells must divide ranks and provide >=2 cells/rank\n");
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    MPI_Comm local; MPI_Comm_split_type(MPI_COMM_WORLD, MPI_COMM_TYPE_SHARED, rank, MPI_INFO_NULL, &local);
    int local_rank, devices; MPI_Comm_rank(local, &local_rank); CUDA(cudaGetDeviceCount(&devices));
    // A scheduler may expose one assigned GPU per process, then its visible ordinal is 0.
    const int device = devices == 1 ? 0 : local_rank;
    if (devices == 0 || device >= devices) {
        std::fprintf(stderr, "Not enough visible GPUs for local rank %d\n", local_rank);
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    CUDA(cudaSetDevice(device));
    char host[MPI_MAX_PROCESSOR_NAME], bus[32]; int hostlen;
    MPI_Get_processor_name(host, &hostlen); CUDA(cudaDeviceGetPCIBusId(bus, sizeof(bus), device));
    std::printf("rank=%d host=%s local_rank=%d visible_device=%d PCI=%s mode=%s\n",
        rank, host, local_rank, device, bus, direct ? "device" : "host-staged");
    const int n = global / size, left = (rank+size-1)%size, right = (rank+1)%size;
    std::vector<float> initial(n+2, 0), result(n+2);
    const double pi = std::acos(-1.0);
    for (int i=1; i<=n; ++i) initial[i] = std::sin(2*pi*(rank*n+i-1)/global);
    float *u, *next, *send, *recv;
    CUDA(cudaMalloc(&u, (n+2)*sizeof(float))); CUDA(cudaMalloc(&next, (n+2)*sizeof(float)));
    CUDA(cudaMallocHost(&send, 2*sizeof(float))); CUDA(cudaMallocHost(&recv, 2*sizeof(float)));
    CUDA(cudaMemcpy(u, initial.data(), (n+2)*sizeof(float), cudaMemcpyHostToDevice));
    cudaStream_t stream; CUDA(cudaStreamCreate(&stream));
    MPI_Barrier(MPI_COMM_WORLD); const double begin = MPI_Wtime();
    for (int step=0; step<steps; ++step) {
        // The prior iteration synchronizes this producer stream before MPI can access u.
        if (!direct) {
            CUDA(cudaMemcpyAsync(send, u+1, sizeof(float), cudaMemcpyDeviceToHost, stream));
            CUDA(cudaMemcpyAsync(send+1, u+n, sizeof(float), cudaMemcpyDeviceToHost, stream));
            CUDA(cudaStreamSynchronize(stream));
        }
        MPI_Request requests[4];
        MPI_Irecv(direct ? u : recv, 1, MPI_FLOAT, left, 20, MPI_COMM_WORLD, &requests[0]);
        MPI_Irecv(direct ? u+n+1 : recv+1, 1, MPI_FLOAT, right, 10, MPI_COMM_WORLD, &requests[1]);
        MPI_Isend(direct ? u+1 : send, 1, MPI_FLOAT, left, 10, MPI_COMM_WORLD, &requests[2]);
        MPI_Isend(direct ? u+n : send+1, 1, MPI_FLOAT, right, 20, MPI_COMM_WORLD, &requests[3]);
        // Reads only owned cells, writes a separate output array. No halo dependence.
        if (n > 2) stencil<<<std::min(4096, (n+255)/256),256,0,stream>>>(u, next, 2, n-1);
        CUDA(cudaGetLastError());
        MPI_Waitall(4, requests, MPI_STATUSES_IGNORE);
        if (!direct) {
            CUDA(cudaMemcpyAsync(u, recv, sizeof(float), cudaMemcpyHostToDevice, stream));
            CUDA(cudaMemcpyAsync(u+n+1, recv+1, sizeof(float), cudaMemcpyHostToDevice, stream));
        }
        stencil<<<1,1,0,stream>>>(u, next, 1, 1);
        stencil<<<1,1,0,stream>>>(u, next, n, n);
        CUDA(cudaGetLastError()); CUDA(cudaStreamSynchronize(stream));
        std::swap(u, next);
    }
    double elapsed = MPI_Wtime()-begin, slowest;
    MPI_Reduce(&elapsed, &slowest, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    CUDA(cudaMemcpy(result.data(), u, (n+2)*sizeof(float), cudaMemcpyDeviceToHost));
    const double eigenvalue = 1 - 0.8*std::pow(std::sin(pi/global),2);
    const double amplitude = std::pow(eigenvalue,steps);
    double local_error = 0, error;
    for (int i=1; i<=n; ++i) {
        double exact = amplitude * std::sin(2*pi*(rank*n+i-1)/global);
        local_error = std::max(local_error, std::abs(result[i]-exact));
    }
    MPI_Allreduce(&local_error, &error, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
    if (!rank) std::printf("ranks=%d cells=%d steps=%d max_wall_s=%.6g max_error=%.6g %s\n",
        size, global, steps, slowest, error, error < 5e-5 ? "PASS" : "FAIL");
    CUDA(cudaStreamDestroy(stream)); CUDA(cudaFree(u)); CUDA(cudaFree(next));
    CUDA(cudaFreeHost(send)); CUDA(cudaFreeHost(recv));
    MPI_Comm_free(&local); MPI_Finalize();
    return error < 5e-5 ? 0 : 1;
}
