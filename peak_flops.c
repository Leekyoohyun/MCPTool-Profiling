/**
 * Peak FLOPS Benchmark
 * Measures theoretical peak floating-point performance
 *
 * Based on HPL-like DGEMM operations
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/time.h>

#ifdef __APPLE__
#include <Accelerate/Accelerate.h>
#define USE_ACCELERATE
#endif

double get_time() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}

// Manual DGEMM for non-Accelerate platforms
void dgemm_manual(int n, double *A, double *B, double *C) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            double sum = 0.0;
            for (int k = 0; k < n; k++) {
                sum += A[i*n + k] * B[k*n + j];
            }
            C[i*n + j] = sum;
        }
    }
}

int main(int argc, char *argv[]) {
    int n = 2048; // Matrix size (2048x2048)
    int iterations = 3;

    if (argc > 1) {
        n = atoi(argv[1]);
    }

    printf("=== Peak FLOPS Benchmark ===\n");
    printf("Matrix size: %d x %d\n", n, n);
    printf("Iterations: %d\n\n", iterations);

    // Allocate matrices
    double *A = (double*)malloc(n * n * sizeof(double));
    double *B = (double*)malloc(n * n * sizeof(double));
    double *C = (double*)malloc(n * n * sizeof(double));

    if (!A || !B || !C) {
        fprintf(stderr, "Memory allocation failed!\n");
        return 1;
    }

    // Initialize matrices
    for (int i = 0; i < n * n; i++) {
        A[i] = (double)rand() / RAND_MAX;
        B[i] = (double)rand() / RAND_MAX;
        C[i] = 0.0;
    }

    printf("Running DGEMM benchmark...\n");

    double total_time = 0.0;
    double best_gflops = 0.0;

    for (int iter = 0; iter < iterations; iter++) {
        double start = get_time();

#ifdef USE_ACCELERATE
        // Use Apple Accelerate framework (optimized)
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                    n, n, n, 1.0, A, n, B, n, 0.0, C, n);
#else
        // Fallback to manual implementation
        dgemm_manual(n, A, B, C);
#endif

        double end = get_time();
        double elapsed = end - start;
        total_time += elapsed;

        // DGEMM performs 2*n^3 floating-point operations
        double flops = 2.0 * n * n * n;
        double gflops = flops / elapsed / 1e9;

        printf("  Iteration %d: %.3f seconds, %.2f GFLOPS\n",
               iter + 1, elapsed, gflops);

        if (gflops > best_gflops) {
            best_gflops = gflops;
        }
    }

    double avg_time = total_time / iterations;
    double avg_gflops = (2.0 * n * n * n) / avg_time / 1e9;

    printf("\n=== Results ===\n");
    printf("Average time: %.3f seconds\n", avg_time);
    printf("Average GFLOPS: %.2f\n", avg_gflops);
    printf("Peak GFLOPS: %.2f\n", best_gflops);

#ifdef USE_ACCELERATE
    printf("\nNote: Using Apple Accelerate framework (optimized)\n");
#else
    printf("\nNote: Using manual DGEMM (not optimized)\n");
#endif

    free(A);
    free(B);
    free(C);

    return 0;
}
