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

MODULES = ply/__init__ ply/lex ply/yacc state rows base db schema core abstract_dataset abstract_map_dataset abstract_space_time_dataset stds_map_register stds_time_edit granule_sampling datasets space_time_datasets open_stds factory gui_support list_stds register sampling metadata spatial_extent temporal_extent datetime_math temporal_granularity topology aggregation aggregation_core series_limits stds_export stds_import batches extract mapcalc related_maps univar_statistics c_libraries_interface algebra/__init__ algebra/content algebra/series algebra/adapters algebra/relations algebra/maptypes algebra/reducers algebra/operations algebra/time_functions algebra/backends algebra/materialize algebra/sources algebra/_checks algebra/_messages algebra/parser/__init__ algebra/parser/operators algebra/parser/lexer algebra/parser/ast algebra/parser/grammar algebra/parser/shared algebra/parser/translate algebra/parser/granularity algebra/parser/facade kinds tool_steps testing/__init__ testing/session testing/data testing/readback testing/io_cache testing/expressions_data testing/outcomes testing/algebra_cases testing/recordings testing/database_image testing/postgresql testing/versions testing/manual_examples testing/manual_coverage testing/nc_dataset testing/contract_trace

CLEAN_SUBDIRS = ply

PYFILES := $(patsubst %,$(DSTDIR)/%.py,$(MODULES) __init__)
PYCFILES := $(patsubst %,$(DSTDIR)/%.pyc,$(MODULES) __init__)

default: $(PYFILES) $(PYCFILES) $(GDIR)/__init__.py $(GDIR)/__init__.pyc

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

$(DSTDIR)/%: % | $(DSTDIR) $(DSTDIRPLY) $(DSTDIRALGEBRA) $(DSTDIRPARSER) $(DSTDIRTESTING)
	$(INSTALL_DATA) $< $@
