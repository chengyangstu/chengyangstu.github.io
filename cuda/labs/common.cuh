#pragma once
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cerrno>

inline void checked(cudaError_t e, const char* file, int line) {
    if (e != cudaSuccess) {
        std::fprintf(stderr, "%s:%d: %s\n", file, line, cudaGetErrorString(e));
        std::exit(1);
    }
}
#define CUDA(call) checked((call), __FILE__, __LINE__)
inline int particle_count(int argc, char** argv) {
    if (argc == 1) return 1 << 20;
    char* end = nullptr;
    errno = 0;
    long n = std::strtol(argv[1], &end, 10);
    if (argc != 2 || errno || end == argv[1] || *end || n < 1 || n > 100000000) {
        std::fprintf(stderr, "Usage: %s [N in 1..100000000]\n", argv[0]);
        std::exit(2);
    }
    return static_cast<int>(n);
}
