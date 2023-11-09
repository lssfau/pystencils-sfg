
CXX := clang++
CXX_FLAGS := -DDEBUG -g -std=c++2b -I/home/fhennig/lssgit/mdspan/include

PYTHON := python

MKDIR := mkdir -p
dir_guard = $(MKDIR) $(@D)	

OBJ := obj
BIN := bin
GEN_SRC := generated_src

.PHONY: all clean

all: $(BIN)/mdspan_test

clean: 
	rm -rf $(BIN) $(OBJ) $(GEN_SRC)

$(GEN_SRC)/kernels.cpp $(GEN_SRC)/kernels.h &: kernels.py
	@$(dir_guard)
	$(PYTHON) $< -d $(@D)

$(OBJ)/kernels.o: $(GEN_SRC)/kernels.cpp $(GEN_SRC)/kernels.h
	@$(dir_guard)
	$(CXX) $(CXX_FLAGS) -c -o $@ $<

$(OBJ)/main.o: main.cpp $(GEN_SRC)/kernels.h
	$(CXX) $(CXX_FLAGS) -c -o $@ $<

$(BIN)/mdspan_test: $(OBJ)/kernels.o $(OBJ)/main.o
	$(CXX) $(CXX_FLAGS) -o $@ $^

