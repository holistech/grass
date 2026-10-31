MODULE_TOPDIR = ../../..

include $(MODULE_TOPDIR)/include/Make/Other.make
include $(MODULE_TOPDIR)/include/Make/Python.make

PYDIR = $(ETC)/python
GDIR = $(PYDIR)/grass
DSTDIR = $(GDIR)/temporal
DSTDIRPLY = $(DSTDIR)/ply
DSTDIRALGEBRA = $(DSTDIR)/algebra
DSTDIRCLASSIC = $(DSTDIR)/classic
DSTDIRPARSER = $(DSTDIRALGEBRA)/parser
DSTDIRTESTING = $(DSTDIR)/testing
DSTDIRCORPUS = $(DSTDIRTESTING)/corpus

MODULES = ply/__init__ ply/lex ply/yacc state rows base db schema core abstract_dataset abstract_map_dataset abstract_space_time_dataset stds_map_register stds_time_edit granule_sampling datasets space_time_datasets open_stds factory gui_support list_stds register sampling metadata spatial_extent temporal_extent datetime_math temporal_granularity topology aggregation aggregation_core stds_export stds_import batches extract mapcalc related_maps univar_statistics c_libraries_interface classic/__init__ classic/temporal_algebra classic/temporal_vector_algebra classic/temporal_raster_base_algebra classic/temporal_raster_algebra classic/temporal_raster3d_algebra classic/temporal_operator algebra/__init__ algebra/content algebra/series algebra/adapters algebra/relations algebra/maptypes algebra/reducers algebra/operations algebra/time_functions algebra/backends algebra/materialize algebra/profile algebra/sources algebra/_checks algebra/variants algebra/parser/__init__ algebra/parser/operators algebra/parser/lexer algebra/parser/ast algebra/parser/grammar algebra/parser/classic_productions algebra/parser/classic_grammar algebra/parser/classic_maps algebra/parser/classic_numbers algebra/parser/classic algebra/parser/shared algebra/parser/translate algebra/parser/switch algebra/parser/granularity algebra/parser/facade kinds tool_steps testing/__init__ testing/session testing/data testing/readback testing/io_cache testing/reference testing/expressions_data testing/expressions_generator testing/differential testing/expressions testing/algebra_cases testing/corpus testing/corpus_orphans testing/recordings testing/database_image testing/postgresql

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

$(DSTDIRCLASSIC): | $(DSTDIR)
	$(MKDIR) $@

$(DSTDIRTESTING): | $(DSTDIR)
	$(MKDIR) $@

$(DSTDIRCORPUS): | $(DSTDIRTESTING)
	$(MKDIR) $@

$(DSTDIRCORPUS)/%: testing/corpus/% | $(DSTDIRCORPUS)
	$(INSTALL_DATA) $< $@

$(DSTDIR)/%: % | $(DSTDIR) $(DSTDIRPLY) $(DSTDIRALGEBRA) $(DSTDIRPARSER) $(DSTDIRCLASSIC) $(DSTDIRTESTING)
	$(INSTALL_DATA) $< $@
