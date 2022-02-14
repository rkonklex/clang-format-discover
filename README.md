# clang-format-discover
A simple tool for extracting clang-format style configuration from existing C++ code.

## Requirements
- python 3.7+
- pyyaml
- clang-format 13

## Installation
```sh
python3 -m pip install git+https://github.com/rkonklex/clang-format-discover.git
```

## Usage
Just point clang-format-discover to your source code. You can specify both directories and individual files:
```sh
clang-format-discover file1.cpp directory file2.cxx ...
```
The script also supports wildcards.
```sh
clang-format-discover basic_*.hpp detail/**/*.hpp impl/*.hpp ...
```

clang-format-discover will discover the clang-format style by trying to reformat the source code with different values of various clang-format options. The resulting configuration is one that makes clang-format do the least amount of changes to the source code. Please note that source files are not being changed - the script redirects clang-format output to memory.

If `.clang-format` file is found in the current directory, its going to be used as a seed configuration. Style options specified in it are not going to be changed - their values are treated as fixed.

## License
[MIT license](LICENSE)
