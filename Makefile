CXX ?= c++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -pedantic -O2

.PHONY: all test clean

all: build/basic

build:
	mkdir -p build

build/basic: examples/basic.cpp ftgd.hpp | build
	$(CXX) $(CXXFLAGS) examples/basic.cpp -o $@

build/smoke: tests/smoke.cpp ftgd.hpp | build
	$(CXX) $(CXXFLAGS) tests/smoke.cpp -o $@

test: build/smoke build/basic
	./build/smoke
	./build/basic

clean:
	rm -rf build
