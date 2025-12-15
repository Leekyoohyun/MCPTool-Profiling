/**
 * Memory Bandwidth Benchmark
 * Based on STREAM Triad: A[i] = B[i] + scalar * C[i]
 *
 * Reference: https://www.cs.virginia.edu/stream/
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#ifdef _OPENMP
#include <omp.h>
#endif

// Array size: 80M elements = 640MB (needs to exceed cache)
#ifndef STREAM_ARRAY_SIZE
#define STREAM_ARRAY_SIZE 80000000
#endif

// Number of iterations
#define NTIMES 10

// Data arrays
static double a[STREAM_ARRAY_SIZE];
static double b[STREAM_ARRAY_SIZE];
static double c[STREAM_ARRAY_SIZE];

double get_time() {
#ifdef __APPLE__
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
#endif
}

int main(int argc, char *argv[]) {
    int i, k;
    double scalar = 3.0;
    double times[4][NTIMES];
    double avgtime[4] = {0.0, 0.0, 0.0, 0.0};
    double maxtime[4] = {0.0, 0.0, 0.0, 0.0};
    double mintime[4] = {1e9, 1e9, 1e9, 1e9};

    char *label[4] = {"Copy:      ", "Scale:     ", "Add:       ", "Triad:     "};

    double bytes[4] = {
        2 * sizeof(double) * STREAM_ARRAY_SIZE,  // Copy: a = b
        2 * sizeof(double) * STREAM_ARRAY_SIZE,  // Scale: a = scalar * b
        3 * sizeof(double) * STREAM_ARRAY_SIZE,  // Add: a = b + c
        3 * sizeof(double) * STREAM_ARRAY_SIZE   // Triad: a = b + scalar * c
    };

    printf("=== Memory Bandwidth Benchmark (STREAM) ===\n");
    printf("Array size: %d elements (%.1f MB per array)\n",
           STREAM_ARRAY_SIZE,
           STREAM_ARRAY_SIZE * sizeof(double) / 1024.0 / 1024.0);
    printf("Total memory: %.1f MB\n",
           3 * STREAM_ARRAY_SIZE * sizeof(double) / 1024.0 / 1024.0);

#ifdef _OPENMP
    int num_threads;
    #pragma omp parallel
    {
        #pragma omp master
        {
            num_threads = omp_get_num_threads();
        }
    }
    printf("Number of threads: %d\n", num_threads);
#else
    printf("Number of threads: 1 (OpenMP not enabled)\n");
#endif

    printf("Iterations: %d\n\n", NTIMES);

    // Initialize arrays
    #pragma omp parallel for
    for (i = 0; i < STREAM_ARRAY_SIZE; i++) {
        a[i] = 1.0;
        b[i] = 2.0;
        c[i] = 0.0;
    }

    printf("Running benchmark...\n");

    // Main benchmark loop
    volatile double dummy;
    for (k = 0; k < NTIMES; k++) {
        // Copy: a = b
        double t0 = get_time();
        #pragma omp parallel for
        for (i = 0; i < STREAM_ARRAY_SIZE; i++) {
            a[i] = b[i];
        }
        double t1 = get_time();
        times[0][k] = t1 - t0;
        dummy = a[STREAM_ARRAY_SIZE-1]; // Prevent optimization

        // Scale: a = scalar * b
        t0 = get_time();
        #pragma omp parallel for
        for (i = 0; i < STREAM_ARRAY_SIZE; i++) {
            a[i] = scalar * b[i];
        }
        t1 = get_time();
        times[1][k] = t1 - t0;
        dummy = a[STREAM_ARRAY_SIZE-1];

        // Add: a = b + c
        t0 = get_time();
        #pragma omp parallel for
        for (i = 0; i < STREAM_ARRAY_SIZE; i++) {
            a[i] = b[i] + c[i];
        }
        t1 = get_time();
        times[2][k] = t1 - t0;
        dummy = a[STREAM_ARRAY_SIZE-1];

        // Triad: a = b + scalar * c
        t0 = get_time();
        #pragma omp parallel for
        for (i = 0; i < STREAM_ARRAY_SIZE; i++) {
            a[i] = b[i] + scalar * c[i];
        }
        t1 = get_time();
        times[3][k] = t1 - t0;
        dummy = a[STREAM_ARRAY_SIZE-1];
    }

    // Calculate statistics (skip first iteration for warmup)
    for (k = 1; k < NTIMES; k++) {
        for (int j = 0; j < 4; j++) {
            avgtime[j] += times[j][k];
            mintime[j] = (times[j][k] < mintime[j]) ? times[j][k] : mintime[j];
            maxtime[j] = (times[j][k] > maxtime[j]) ? times[j][k] : maxtime[j];
        }
    }

    for (int j = 0; j < 4; j++) {
        avgtime[j] /= (double)(NTIMES - 1);
    }

    // Print results
    printf("\n=== Results ===\n");
    printf("Function    Best Rate (MB/s)  Avg time    Min time    Max time\n");

    for (int j = 0; j < 4; j++) {
        double best_rate = bytes[j] / mintime[j] / 1e6;
        printf("%s%12.1f  %11.6f  %11.6f  %11.6f\n",
               label[j],
               best_rate,
               avgtime[j],
               mintime[j],
               maxtime[j]);
    }

    // Print Memory Bandwidth (Triad is the most important)
    double memory_bw_gb = bytes[3] / mintime[3] / 1e9;
    printf("\n=== Memory Bandwidth ===\n");
    printf("Triad (Best): %.2f GB/s\n", memory_bw_gb);

    return 0;
}
