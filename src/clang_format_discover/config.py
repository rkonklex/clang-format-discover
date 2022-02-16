from typing import TextIO, Union

import flatdict
import yaml

from .execution import capture_process_output


CLANG_FORMAT_CONFIG_FILE = '.clang-format'

StyleSettings = flatdict.FlatDict


class ClangFormatLoader(yaml.SafeLoader):
    # reset implicit type handlers - treat all scalars as strings
    yaml_implicit_resolvers = {}

def load_clang_format_config(file: Union[TextIO, str, None] = None) -> StyleSettings:
    if file is None:
        with open(CLANG_FORMAT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return load_clang_format_config(f)
    return StyleSettings(yaml.load(file, Loader=ClangFormatLoader))


class ClangFormatDumper(yaml.SafeDumper):
    # reset implicit type handlers - treat all scalars as strings
    yaml_implicit_resolvers = {}

def save_clang_format_config(config: StyleSettings):
    with open(CLANG_FORMAT_CONFIG_FILE, 'w', encoding='utf-8') as file:
        yaml.dump(config.as_dict(), file, Dumper=ClangFormatDumper,
            explicit_start=True, explicit_end=True,
            sort_keys=False
        )


def get_effective_clang_format_config(config: StyleSettings) -> StyleSettings:
    save_clang_format_config(config)
    output_txt = capture_process_output(['clang-format', '--style=file', '--dump-config'])
    return load_clang_format_config(output_txt)
