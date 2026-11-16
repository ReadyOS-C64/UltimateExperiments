ifneq ($(wildcard /Library/Developer/CommandLineTools/usr/bin/clang),)
DEVELOPER_DIR ?= /Library/Developer/CommandLineTools
export DEVELOPER_DIR
endif
CA65 ?= ca65
LD65 ?= ld65
PYTHON ?= python3
PEDDLE := third_party/peddle/Peddle
CORE := $(wildcard $(PEDDLE)/*.cpp)
CORE_DIR ?= build
CORE_MODULES := reu.o dot.o matrix.o scale.o embedding.o wide.o vector.o network.o cache.o attention_exp.o attention.o
CORE_OBJECTS := $(addprefix $(CORE_DIR)/,$(CORE_MODULES))
REU_READ_PAGE_CHUNKS ?= 0

.PHONY: all test model reference
all: $(CORE_DIR)/core.bin build/peddle.so

build:
	mkdir -p $@

build/exp_table.inc: tools/exp_table.py tools/oracle.py | build
	$(PYTHON) -m tools.exp_table > $@

$(CORE_DIR)/attention_exp.o: src/attention_exp.s build/exp_table.inc
	mkdir -p $(@D)
	$(CA65) -I build -g -o $@ $<

$(CORE_DIR)/reu.o: src/reu.s
	mkdir -p $(@D)
	$(CA65) -D REU_READ_PAGE_CHUNKS=$(REU_READ_PAGE_CHUNKS) -g -o $@ $<

$(CORE_DIR)/%.o: src/%.s
	mkdir -p $(@D)
	$(CA65) -g -o $@ $<

$(CORE_DIR)/core.bin: $(CORE_OBJECTS) src/core.cfg
	$(LD65) -C src/core.cfg -o $@ -Ln $(@D)/core.lbl -m $(@D)/core.map $(filter %.o,$^)

build/group4-matrix/matrix.o: src/matrix.s
	mkdir -p $(@D)
	$(CA65) -D GROUP4_BENCHMARK=1 -g -o $@ $<

GROUP4_BENCH_OBJECTS := $(foreach obj,$(CORE_MODULES),$(if $(filter matrix.o,$(obj)),build/group4-matrix/$(obj),build/$(obj)))
build/group4-matrix/core.bin: $(GROUP4_BENCH_OBJECTS) build/group4/dot_group4.o src/core.cfg
	$(LD65) -C src/core.cfg -o $@ -Ln $(@D)/core.lbl -m $(@D)/core.map $(filter %.o,$^)

build/group4/%.o: src/%.s
	mkdir -p $(@D)
	$(CA65) -D GROUP4_EXPERIMENT=1 -g -o $@ $<

build/group4/attention_exp.o: src/attention_exp.s build/exp_table.inc
	mkdir -p $(@D)
	$(CA65) -I build -g -o $@ $<

GROUP4_OBJECTS := $(addprefix build/group4/,$(CORE_MODULES) dot_group4.o)
build/group4/core.bin: $(GROUP4_OBJECTS) src/core.cfg
	$(LD65) -C src/core.cfg -o $@ -Ln $(@D)/core.lbl -m $(@D)/core.map $(filter %.o,$^)

build/peddle.so: tests/peddle.cpp $(CORE) $(wildcard $(PEDDLE)/*.h) | build
	$(CXX) -std=c++20 -O3 -fPIC -shared -I$(PEDDLE) -o $@ tests/peddle.cpp $(CORE)

reference:
	$(PYTHON) -m tools.fetch_reference

model: | build
	$(PYTHON) tools/model.py reference/TINY.BIN build/model.reu

test: all
	$(PYTHON) -m unittest discover -s tests -v

build/group8-bench/dot_group8.o: src/dot_group8.s
	mkdir -p $(@D)
	$(CA65) -g -o $@ $<

build/group8-bench/core.bin: $(GROUP4_OBJECTS) build/group8-bench/dot_group8.o src/core.cfg
	$(LD65) -C src/core.cfg -o $@ -Ln $(@D)/core.lbl -m $(@D)/core.map $(filter %.o,$^)

GROUP8_DEFINES := -D GROUP4_EXPERIMENT=1 -D GROUP8_EXPERIMENT=1
GROUP8_OBJECTS := $(addprefix build/group8/,$(CORE_MODULES) dot_group4.o dot_group8.o)
build/group8/%.o: src/%.s
	mkdir -p $(@D)
	$(CA65) $(GROUP8_DEFINES) -g -o $@ $<

build/group8/attention_exp.o: src/attention_exp.s build/exp_table.inc
	mkdir -p $(@D)
	$(CA65) -I build -g -o $@ $<

build/group8/core.bin: $(GROUP8_OBJECTS) src/core.cfg
	$(LD65) -C src/core.cfg -o $@ -Ln $(@D)/core.lbl -m $(@D)/core.map $(filter %.o,$^)
