py_mod = import('python')
python = py_mod.find_installation(
    pure: false)

python.install_sources(['__init__.py', 'generate.py', 'agent.py'], subdir: 'flexsipp')
python.install_sources(['graphs/__init__.py', 'graphs/fsipp.py', 'graphs/graph.py'], subdir: 'flexsipp/graphs')
python.install_sources(['railways/__init__.py', 'railways/block_graph.py', 'railways/track_graph.py', 'railways/scenario.py', 'railways/train_agent.py'], subdir: 'flexsipp/railways')
python.install_sources(['railways/train_agents/__init__.py', 'railways/train_agents/train_agent_acceleration.py', 'railways/train_agents/train_agent_limited_flexibility.py'], subdir: 'flexsipp/railways/train_agents')
python.install_sources(['util/__init__.py', 'util/intervals.py', 'util/plotting_info.py', 'util/results.py', 'util/timing.py', 'util/types.py', 'util/util.py'], subdir: 'flexsipp/util')