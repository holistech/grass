MODULE_TOPDIR = ../../..

include $(MODULE_TOPDIR)/include/Make/Other.make
include $(MODULE_TOPDIR)/include/Make/Python.make

PYDIR = $(ETC)/python
GDIR = $(PYDIR)/grass
DSTDIR = $(GDIR)/temporal
DSTDIRPLY = $(DSTDIR)/ply
DSTDIRTESTING = $(DSTDIR)/testing

MODULES = ply/__init__ ply/lex ply/yacc state rows base db schema core kinds series_limits batches tool_steps abstract_dataset abstract_map_dataset abstract_space_time_dataset stds_map_register stds_time_edit granule_sampling datasets space_time_datasets open_stds factory gui_support list_stds register sampling metadata spatial_extent temporal_extent datetime_math temporal_granularity topology spatio_temporal_relationships aggregation stds_export stds_import extract mapcalc univar_statistics c_libraries_interface temporal_algebra temporal_vector_algebra temporal_raster_base_algebra temporal_raster_algebra temporal_raster3d_algebra temporal_operator testing/__init__ testing/session testing/data testing/readback testing/io_cache testing/recordings testing/database_image testing/postgresql testing/versions testing/manual_examples testing/manual_coverage testing/nc_dataset

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

$(DSTDIRTESTING): | $(DSTDIR)
	$(MKDIR) $@

$(DSTDIR)/%: % | $(DSTDIR) $(DSTDIRPLY) $(DSTDIRTESTING)
	$(INSTALL_DATA) $< $@
