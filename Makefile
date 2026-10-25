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

.PHONY: counter-menu counter-test
counter-menu: build/counter-menu

build/counter-menu: examples/counter_menu/menu.cpp ftgd.hpp | build
	$(CXX) $(CXXFLAGS) examples/counter_menu/menu.cpp -o $@

counter-test: build/counter-menu
	python3 -m unittest discover -s examples/counter_menu -p 'test_*.py' -v
