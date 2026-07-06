# ---- Python ----
python = import('python').find_installation(
    required : true,
    pure: false,
)

# ---- Boost dependency ----
# Try pkg-config first, fallback to manual search if not found
boost_dep = dependency(
    'boost',
    modules : ['python3', 'program_options', 'random', 'iostreams'],
    required : false,
)

if not boost_dep.found()
    # Manual fallback: search for boost libraries directly
    boost_includedir = get_option('boost_includedir')
    boost_librarydir = get_option('boost_librarydir')
    
    if boost_includedir == ''
        boost_includedir = '/usr/include'
    endif
    if boost_librarydir == ''
        boost_librarydir = '/usr/lib'
    endif
    
    cc = meson.get_compiler('cpp')
    
    # Find individual boost libraries
    boost_python_lib = cc.find_library('boost_python313', dirs: boost_librarydir, required: false)
    if not boost_python_lib.found()
        boost_python_lib = cc.find_library('boost_python3', dirs: boost_librarydir, required: true)
    endif
    
    boost_program_options_lib = cc.find_library('boost_program_options', dirs: boost_librarydir, required: true)
    boost_random_lib = cc.find_library('boost_random', dirs: boost_librarydir, required: true)
    boost_iostreams_lib = cc.find_library('boost_iostreams', dirs: boost_librarydir, required: true)
    
    boost_dep = declare_dependency(
        include_directories: include_directories(boost_includedir),
        dependencies: [boost_python_lib, boost_program_options_lib, boost_random_lib, boost_iostreams_lib]
    )
endif

python.extension_module(
    'search',
    ['bindentry.cpp', 'graph.cpp', 'segment.cpp', 'augmentedsipp.cpp', 'repeat.cpp'],
    install: true,
    dependencies: [boost_dep],
    subdir: '_flexsipp'
)