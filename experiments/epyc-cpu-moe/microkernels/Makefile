CC ?= gcc
CFLAGS ?= -O3 -std=c11 -Wall -Wextra -Werror -mavx2 -march=znver1 -mtune=znver1

.PHONY: all check clean disassemble
all: dot_u5s8

dot_u5s8: dot_u5s8.c
	$(CC) $(CFLAGS) $< -o $@

check: dot_u5s8
	@if grep -qw avx2 /proc/cpuinfo; then ./dot_u5s8; else echo 'SKIP: host has no AVX2'; fi

disassemble: dot_u5s8
	objdump -d -Mintel dot_u5s8 | grep -Ei 'vpmaddubsw|vpmaddwd' || true

clean:
	rm -f dot_u5s8
