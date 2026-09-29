# Makefile — Cautreo Weight Pager shared library
# Toolchain: LLVM-MinGW GCC (Windows)
#
# Usage:
#   make            # build cautreo_pager.dll
#   make clean      # remove build artifacts
#   make test       # build and run C unit tests

CC      = gcc
CFLAGS  = -shared -O2 -Wall -Wextra -DCT_PAGER_BUILD=1
LDFLAGS = -lm
TARGET  = ../../bin/cautreo_pager.dll
SRCS    = ct_gguf_reader.c ct_weight_pager.c
OBJS    = $(SRCS:.c=.o)
TESTBIN = test_ct_pager.exe

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS) $(LDFLAGS)

%.o: %.c ct_gguf_reader.h ct_weight_pager.h
	$(CC) $(CFLAGS) -c $< -o $@

test: $(TARGET) $(TESTBIN)
	./$(TESTBIN)

$(TESTBIN): test_ct_pager.c $(SRCS)
	$(CC) -O2 -Wall -Wextra -DCT_PAGER_BUILD=1 -o $(TESTBIN) test_ct_pager.c $(SRCS) $(LDFLAGS)

clean:
	rm -f $(OBJS) $(TARGET) $(TESTBIN)
