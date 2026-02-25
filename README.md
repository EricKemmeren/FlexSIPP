# Replanning in Advance for Instant Delay Recovery

This project has the following directories:
- `generation`: Python module to generate the @SIPP search graph
- `search` (atSIPP): C++ module to search for any-start-time plans in the @SIPP search graph
- `data`: two dutch shunting yard layouts: Enkhuizen and Heerlen. This also includes code to generate new scenarios and explanation of how the real-life scenario was created.
- `experiments`: the notebook contains all the code to run experiments for our paper

Dependencies (version tested):
- gcc (13.2.1)
- boost (1.83)
- meson (1.2.3)

Compiling:
```bash
    cd /search
    meson setup --buildtype release build
    meson compile -C build
    meson setup --buildtype debug build_debug
    meson compile -C build_debug
    cd ..
```
An executable is now located in `./FlexSIPP/search/build/flexsipp`.

To create a package that can be installed from the FlexSIPP source code, run the following commands:
```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements
    pip install -e .
```
FlexSIPP can now be imported in python with `import flexsipp`.

To run a specific scenario on a matching location for a specific agent (id=`1`):
```
python src/flexsipp/main.py -s tests/scenario_test.json -l tests/location_test.json -t railway -a 1
```
Or for a MAPF scenario, you need to pass the agents paths:
```
python src/flexsipp/main.py -s data/mapf/corridor/corridor-2agents_paths.txt -l data/mapf/corridor/corridor.map -t mapf
```

To run the tests use:
```
python -m unittest
```

To cite, please use:

    Issa Hanou, Eric Kemmeren, Devin Wild Thomas, and Mathijs de Weerdt.Precomputing Multi-Agent Path Replanning using Temporal Flexibility: A Case Study on the Dutch Railway Network. (2026). [In Proceedings: International Conference on Automated Planning and Scheduling](https://arxiv.org/abs/2601.04884).

# Benchmarks

### MovingAI

The Moving AI benchmark set can be used with FlexSIPP, more information on the map format can be found [here](https://movingai.com/benchmarks/formats.html). FlexSIPP requires some initial solution for each instance, and the `scenario_file` provided to `src/flexsipp/main.py` should be a list of paths for each agent, formatted as follows:
```
Agent <id0>: {node1}->{node2}->{node2}->{node2}->{node3}->...->{nodeN}->
Agent <id1>: {node1}->{node2}->{node2}->{node2}->{node3}->...->{nodeN}->
...
```

### New Benchmark
To add a new benchmark with a different file structure, the `Graph` class must be implemented for this type of location and the `Agent`s must be initialized with their initial routes and predefined flexibility. See `generate_mapf.py` for an example with the Moving AI benchmarks.

### Railways
<TODO explain file structures>
