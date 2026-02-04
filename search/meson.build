project('flexsipp', 'cpp',
  version : '0.1',
  default_options : ['warning_level=3', 'cpp_std=c++20', 'b_ndebug=if-release'])

# ---- Python ----
python = import('python').find_installation(
    'C:\Users\erick\AppData\Local\Programs\Python\Python313\python.exe',
    required : true,
)

python_dep = python.dependency(
    embed : true,
    required : true
)

pybind11 = dependency(
    'pybind11',
    required : true
)

# ---- Boost dependency ----
boost_dep = dependency(
    'boost',
    modules : ['python313', 'program_options', 'random', 'iostreams'],
    required : true,
    static: true,
)

flexsipp_lib = shared_library(
    'flexsipp_lib',
    ['bindentry.cpp', 'graph.cpp', 'segment.cpp', 'augmentedsipp.cpp', 'repeat.cpp'],
    install: true,
    dependencies: [boost_dep, pybind11, python_dep],
)

executable('flexsipp',
           ['main.cpp', 'graph.cpp', 'segment.cpp', 'augmentedsipp.cpp', 'repeat.cpp'],
           install : true,
           dependencies : [boost_dep],
)
