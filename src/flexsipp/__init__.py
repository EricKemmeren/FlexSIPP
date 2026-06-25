try:
    from _flexsipp import search
except ImportError:
    import os
    boost_path = os.environ.get('BOOST_PATH_DLL', r"C:\Boost\lib64-msvc-14.3")
    # This could maybe be automatically detected
    os.add_dll_directory(boost_path)
    from _flexsipp import search
