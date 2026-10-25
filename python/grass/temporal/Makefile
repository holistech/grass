MODULE_TOPDIR = ../../..

include $(MODULE_TOPDIR)/include/Make/Other.make
include $(MODULE_TOPDIR)/include/Make/Python.make

PYDIR = $(ETC)/python
GDIR = $(PYDIR)/grass
DSTDIR = $(GDIR)/temporal
DSTDIRPLY = $(DSTDIR)/ply
DSTDIRALGEBRA = $(DSTDIR)/algebra
DSTDIRPARSER = $(DSTDIRALGEBRA)/parser
DSTDIRTESTING = $(DSTDIR)/testing
DSTDIRCORPUS = $(DSTDIRTESTING)/corpus

MODULES = ply/__init__ ply/lex ply/yacc state base db schema core abstract_dataset abstract_map_dataset abstract_space_time_dataset space_time_datasets open_stds factory gui_support list_stds register sampling metadata spatial_extent temporal_extent datetime_math temporal_granularity spatio_temporal_relationships aggregation aggregation_core stds_export stds_import extract mapcalc related_maps univar_statistics temporal_topology_dataset_connector spatial_topology_dataset_connector c_libraries_interface temporal_algebra temporal_vector_algebra temporal_raster_base_algebra temporal_raster_algebra temporal_raster3d_algebra temporal_operator algebra/__init__ algebra/content algebra/series algebra/_adapters algebra/relations algebra/maptypes algebra/reducers algebra/operations algebra/time_functions algebra/backends algebra/materialize algebra/profile algebra/sources algebra/_checks algebra/parser/__init__ algebra/parser/operators algebra/parser/lexer algebra/parser/ast algebra/parser/grammar algebra/parser/classic_grammar algebra/parser/classic algebra/parser/translate algebra/parser/switch algebra/parser/granularity kinds testing/__init__ testing/session testing/data testing/readback testing/fakes testing/reference testing/expressions_data testing/expressions_generator testing/expressions testing/legacy_data testing/corpus testing/recordings

CLEAN_SUBDIRS = ply

PYFILES := $(patsubst %,$(DSTDIR)/%.py,$(MODULES) __init__)
PYCFILES := $(patsubst %,$(DSTDIR)/%.pyc,$(MODULES) __init__)
# The recorded outcomes that grass.temporal.testing.corpus reads; there may be
# none, and a kind may be plain or packed
CORPUSFILES := $(patsubst %,$(DSTDIR)/%,$(wildcard testing/corpus/*.jsonl testing/corpus/*.jsonl.gz))

default: $(PYFILES) $(PYCFILES) $(CORPUSFILES) $(GDIR)/__init__.py $(GDIR)/__init__.pyc

$(PYDIR):
	$(MKDIR) $@

$(GDIR): | $(PYDIR)
	$(MKDIR) $@

$(DSTDIR): | $(GDIR)
	$(MKDIR) $@

$(DSTDIRPLY): | $(DSTDIR)
	$(MKDIR) $@

$(DSTDIRALGEBRA): | $(DSTDIR)
	$(MKDIR) $@

$(DSTDIRPARSER): | $(DSTDIRALGEBRA)
	$(MKDIR) $@

$(DSTDIRTESTING): | $(DSTDIR)
	$(MKDIR) $@

$(DSTDIRCORPUS): | $(DSTDIRTESTING)
	$(MKDIR) $@

$(DSTDIRCORPUS)/%: testing/corpus/% | $(DSTDIRCORPUS)
	$(INSTALL_DATA) $< $@

$(DSTDIR)/%: % | $(DSTDIR) $(DSTDIRPLY) $(DSTDIRALGEBRA) $(DSTDIRPARSER) $(DSTDIRTESTING)
	$(INSTALL_DATA) $< $@
