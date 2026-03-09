py_mod = import('python')
python = py_mod.find_installation(
    pure: false)

python.install_sources(['__init__.py', 'agent.py'], subdir: 'flexsipp')
python.install_sources(['graphs/__init__.py', 'graphs/fsipp.py', 'graphs/graph.py'], subdir: 'flexsipp/graphs')
python.install_sources(['util/__init__.py', 'util/intervals.py', 'util/lines.py', 'util/plotting_info.py', 'util/results.py', 'util/timing.py', 'util/types.py', 'util/util.py'], subdir: 'flexsipp/util')