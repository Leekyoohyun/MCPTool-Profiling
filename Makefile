# Makefile for Node Benchmarks
# Supports: macOS (Apple Silicon/Intel), Linux (x86_64, ARM)

CC = gcc
CFLAGS = -O3 -march=native -ffast-math

# Detect OS
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

# macOS with Accelerate framework
ifeq ($(UNAME_S),Darwin)
	LDFLAGS = -framework Accelerate -lm
	CFLAGS += -I/usr/local/include
	# macOS clang doesn't support OpenMP by default - skip it
else
	# Linux: add OpenMP support
	CFLAGS += -fopenmp
endif

# Linux with OpenBLAS or MKL
ifeq ($(UNAME_S),Linux)
	# Try to find OpenBLAS
	ifneq ($(wildcard /usr/include/openblas),)
		LDFLAGS = -lopenblas -lm -lpthread
		CFLAGS += -I/usr/include/openblas
	else ifneq ($(wildcard /usr/lib/x86_64-linux-gnu/openblas-pthread),)
		LDFLAGS = -lopenblas -lm -lpthread
	else
		# Fallback: no BLAS (slower but works)
		LDFLAGS = -lm -lpthread
		CFLAGS += -DNO_BLAS
	endif
endif

all: peak_flops memory_bandwidth

peak_flops: peak_flops.c
	$(CC) $(CFLAGS) -o peak_flops peak_flops.c $(LDFLAGS)

memory_bandwidth: memory_bandwidth.c
	$(CC) $(CFLAGS) -o memory_bandwidth memory_bandwidth.c $(LDFLAGS)

clean:
	rm -f peak_flops memory_bandwidth

install:
	@echo "Installing required packages..."
ifeq ($(UNAME_S),Darwin)
	@echo "macOS: Using built-in Accelerate framework"
endif
ifeq ($(UNAME_S),Linux)
	@echo "Linux: Install OpenBLAS with:"
	@echo "  Ubuntu/Debian: sudo apt-get install libopenblas-dev fio"
	@echo "  Fedora/RHEL:   sudo dnf install openblas-devel fio"
endif

test: all
	@echo "Testing peak_flops..."
	./peak_flops 1024
	@echo ""
	@echo "Testing memory_bandwidth..."
	./memory_bandwidth

.PHONY: all clean install test
