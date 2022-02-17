import sys
import time
from typing import List

from .config import CLANG_FORMAT_CONFIG_FILE
from .config import StyleSettings
from .config import load_clang_format_config, save_clang_format_config
from .execution import capture_process_output, ThreadPoolProcessDispatcher
from .optimizer import optimize_configuration, minimize_configuration
from .options import ALL_TUNEABLE_OPTIONS, PRIORITY_OPTIONS
from .scoring import eval_clang_format_cost
from .utils import search_files


CXX_EXTENSIONS = ['.cpp', '.cxx', '.cc', '.c', '.hpp', '.hxx', '.hh', '.h', '.ipp']
FILE_BATCH_SIZE = 10
FILE_LIST_PRINT_MAX = 10


def verify_clang_version():
    try:
        clang_version = capture_process_output(['clang-format', '--version'])
    except FileNotFoundError:
        sys.exit('clang-format not found!')
    if not clang_version.startswith('clang-format version 13.0.0'):
        sys.exit('clang-format version 13.0.0 is required')


def main():
    verify_clang_version()

    try:
        baseline_config = load_clang_format_config()
    except FileNotFoundError:
        baseline_config = StyleSettings({'Language':'Cpp'})
        print(f'{CLANG_FORMAT_CONFIG_FILE} not found: will create it for you')

    current_config = baseline_config.copy()
    exclude_options: List[str] = list(baseline_config.keys())
    if current_config.setdefault('BreakBeforeBraces', 'Custom') != 'Custom':
        # do not optimize brace wrapping when a preset has been set
        brace_wrapping_opts = filter(lambda k: k.startswith('BraceWrapping:'), ALL_TUNEABLE_OPTIONS)
        exclude_options.extend(brace_wrapping_opts)

    search_roots = sys.argv[1:] if len(sys.argv) > 1 else ['.']
    file_list = search_files(search_roots, CXX_EXTENSIONS)
    print(f'Source files ({len(file_list)}): ', end='')
    if len(file_list) <= FILE_LIST_PRINT_MAX:
        print(' '.join(file_list), '\n')
    else:
        print(' '.join(file_list[:FILE_LIST_PRINT_MAX]), '(...)', '\n')

    t_start = time.monotonic()
    try:
        with ThreadPoolProcessDispatcher(max_workers=5) as dispatcher:
            def cost_func(config: StyleSettings) -> int:
                return eval_clang_format_cost(
                    file_list,
                    dispatcher.map,
                    config=config,
                    batch_max=FILE_BATCH_SIZE
                )
            # start with most impactful options
            optimize_configuration(current_config, cost_func, include_opts=PRIORITY_OPTIONS, exclude_opts=exclude_options)
            # then continue with the rest
            optimize_configuration(current_config, cost_func, exclude_opts=exclude_options)
            # finally remove any redundant settings
            minimize_configuration(current_config, cost_func, baseline_config.keys())
    except KeyboardInterrupt:
        print('\nInterrupted')
    t_end = time.monotonic()
    print(f'Processing time: {t_end-t_start} seconds\n')

    print(f'Saving best configuration to {CLANG_FORMAT_CONFIG_FILE}')
    save_clang_format_config(current_config)


if __name__ == '__main__':
    main()
