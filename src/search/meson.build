# ---- Python ----
python = import('python').find_installation(
    required : true,
    pure: false,
)

# ---- Boost dependency ----
boost_dep = dependency(
    'boost',
    modules : ['python3', 'program_options', 'random', 'iostreams'],
    required : true,
)

python.extension_module(
    'search',
    ['bindentry.cpp', 'graph.cpp', 'segment.cpp', 'augmentedsipp.hpp', 'repeat.cpp'],
    install: true,
    dependencies: [boost_dep],
    subdir: '_flexsipp'
)