try:
    from _flexsipp import search
except ImportError:
    import os
    os.add_dll_directory(r"C:\Boost\lib64-msvc-14.3")  # TODO: maybe this can automatically be detected, I think only needed on windows
    from _flexsipp import search