set(PYDIRS
    benchmark
    exceptions
    experimental
    grassdb
    gunittest
    imaging
    jupyter
    pydispatch
    pygrass
    pygrass/gis
    pygrass/messages
    pygrass/modules
    pygrass/modules/grid
    pygrass/modules/interface
    pygrass/raster
    pygrass/rpc
    pygrass/shell
    pygrass/tests
    pygrass/vector
    script
    semantic_label
    temporal
    temporal/algebra
    temporal/algebra/parser
    temporal/classic
    temporal/ply
    temporal/testing
    tools
    utils
)

set(PYDIR_GRASS ${GRASS_INSTALL_PYDIR}/grass)

foreach(pydir ${PYDIRS})
    copy_python_files_in_subdir(${pydir} ${PYDIR_GRASS})
endforeach()
copy_python_files_in_subdir(app ${PYDIR_GRASS} EXCLUDE resource_paths.py)

configure_file(__init__.py ${OUTDIR}/${PYDIR_GRASS}/ COPYONLY)

file(TO_NATIVE_PATH ${CMAKE_BINARY_DIR}/bin BINARY_DIR)
set(CONFIG_PROJSHARE)
get_filename_component(PROJ_INSTALL_PREFIX ${PROJ_INCLUDE_DIRS} PATH)
if(DEFINED ENV{PROJSHARE})
    message(
        WARNING
        "External PROJ directory not specified; default will be used"
    )
    set(CONFIG_PROJSHARE "$ENV{PROJSHARE}")
else()
    set(CONFIG_PROJSHARE "${PROJ_INSTALL_PREFIX}/share/proj")
    if(EXISTS ${CONFIG_PROJSHARE}/epsg)
        message(STATUS "PROJ directory ${CONFIG_PROJSHARE}")
    endif()
endif()
file(TO_NATIVE_PATH "${PROJ_INSTALL_PREFIX}/share/proj" PROJ_LIB)
file(TO_NATIVE_PATH ${CONFIG_PROJSHARE} GRASS_PROJSHARE)

# configure and install resource_paths.py
set(GRASS_PREFIX ${OUTDIR})
set(GISBASE_INSTALL_PATH ${GISBASE_DIR})
set(START_UP ${PROJECT_NAME_LOWER})
configure_file(
    app/resource_paths.py
    ${OUTDIR}/${PYDIR_GRASS}/app/resource_paths.py
    @ONLY
)

set(GRASS_PREFIX ${CMAKE_INSTALL_PREFIX})
configure_file(
    app/resource_paths.py
    ${CMAKE_CURRENT_BINARY_DIR}/resource_paths.py
    @ONLY
)
unset(GISBASE_INSTALL_PATH)
unset(GRASS_PREFIX)
unset(START_UP)

set(pydir_targets ${PYDIRS} app)
list(TRANSFORM pydir_targets REPLACE "/" "_")
list(TRANSFORM pydir_targets PREPEND "python_")

# The recorded outcomes that grass.temporal.testing.corpus reads; there may be
# none, and cmake -E copy fails without a source file
file(
    GLOB TEMPORAL_CORPUS_FILES
    CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/temporal/testing/corpus/*.jsonl"
    "${CMAKE_CURRENT_SOURCE_DIR}/temporal/testing/corpus/*.jsonl.gz"
)
if(TEMPORAL_CORPUS_FILES)
    set(TEMPORAL_CORPUS_DIR "${OUTDIR}/${PYDIR_GRASS}/temporal/testing/corpus")
    add_custom_target(
        python_temporal_testing_corpus
        COMMAND ${CMAKE_COMMAND} -E make_directory "${TEMPORAL_CORPUS_DIR}"
        COMMAND
            ${CMAKE_COMMAND} -E copy ${TEMPORAL_CORPUS_FILES}
            "${TEMPORAL_CORPUS_DIR}"
    )
    set_target_properties(
        python_temporal_testing_corpus
        PROPERTIES FOLDER Python/API
    )
    list(APPEND pydir_targets python_temporal_testing_corpus)
endif()

add_custom_target(LIB_PYTHON VERBATIM DEPENDS ${pydir_targets})

set_target_properties(LIB_PYTHON PROPERTIES FOLDER Misc)

install(
    DIRECTORY ${OUTDIR}/${PYDIR_GRASS}
    DESTINATION ${GRASS_INSTALL_PYDIR}
    PATTERN "*/resource_paths.py" EXCLUDE
)
install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/resource_paths.py
    DESTINATION ${GRASS_INSTALL_PYDIR}/grass/app
)
