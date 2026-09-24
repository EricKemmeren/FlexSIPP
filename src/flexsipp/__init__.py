try:
    from _flexsipp import search
except ImportError as e:
    import os
    import platform
    
    # On Linux/SLURM clusters: ensure Boost libraries are in LD_LIBRARY_PATH
    if platform.system() == 'Linux':
        boost_root = os.environ.get('BOOST_ROOT', '')
        ld_lib_path = os.environ.get('LD_LIBRARY_PATH', '')
        if boost_root and boost_root not in ld_lib_path:
            raise ImportError(
                f"Failed to import _flexsipp.search: {e}\n"
                f"On Linux/SLURM clusters, ensure LD_LIBRARY_PATH includes Boost libraries:\n"
                f"  export BOOST_ROOT=/path/to/boost\n"
                f"  export LD_LIBRARY_PATH=$BOOST_ROOT/lib:$LD_LIBRARY_PATH\n"
                f"Then try again."
            ) from e
    else:
        boost_path = os.environ.get('BOOST_PATH_DLL', r"C:\Boost\lib64-msvc-14.3")
        os.add_dll_directory(boost_path)
        from _flexsipp import search
    
    # Generic fallback
    raise ImportError(
        f"Failed to import _flexsipp.search: {e}\n"
        f"Please ensure Boost libraries are properly installed and linked."
    ) from e
