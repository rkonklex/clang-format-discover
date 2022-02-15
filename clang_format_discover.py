import concurrent.futures
import glob
import itertools
import os
import os.path
import subprocess
import sys
import time
import xml.sax
import xml.sax.handler
from typing import Callable, Dict, Iterable, List, Optional, Set, TextIO, Tuple, TypeVar, Union

import flatdict
import yaml


BOOLEAN_OPTION_TYPE = ['false', 'true']

# Extracted from the documentation of clang-format version 13
# https://releases.llvm.org/13.0.0/tools/clang/docs/ClangFormatStyleOptions.html
ALL_TUNEABLE_OPTIONS = {
    'AccessModifierOffset': ['-4', '-3', '-2', '-1', '0'],
    'AlignAfterOpenBracket': ['Align', 'DontAlign', 'AlwaysBreak'],
    'AlignArrayOfStructures': ['Left', 'Right', 'None'],
    'AlignConsecutiveAssignments': ['None', 'Consecutive', 'AcrossEmptyLines', 'AcrossComments', 'AcrossEmptyLinesAndComments'],
    'AlignConsecutiveBitFields': ['None', 'Consecutive', 'AcrossEmptyLines', 'AcrossComments', 'AcrossEmptyLinesAndComments'],
    'AlignConsecutiveDeclarations': ['None', 'Consecutive', 'AcrossEmptyLines', 'AcrossComments', 'AcrossEmptyLinesAndComments'],
    'AlignConsecutiveMacros': ['None', 'Consecutive', 'AcrossEmptyLines', 'AcrossComments', 'AcrossEmptyLinesAndComments'],
    'AlignEscapedNewlines': ['DontAlign', 'Left', 'Right'],
    'AlignOperands': ['DontAlign', 'Align', 'AlignAfterOperator'],
    'AlignTrailingComments': BOOLEAN_OPTION_TYPE,
    'AllowAllArgumentsOnNextLine': BOOLEAN_OPTION_TYPE,
    'AllowAllConstructorInitializersOnNextLine': BOOLEAN_OPTION_TYPE,
    'AllowAllParametersOfDeclarationOnNextLine': BOOLEAN_OPTION_TYPE,
    'AllowShortBlocksOnASingleLine': ['Never', 'Empty', 'Always'],
    'AllowShortCaseLabelsOnASingleLine': BOOLEAN_OPTION_TYPE,
    'AllowShortEnumsOnASingleLine': BOOLEAN_OPTION_TYPE,
    'AllowShortFunctionsOnASingleLine': ['None', 'InlineOnly', 'Empty', 'Inline', 'All'],
    'AllowShortIfStatementsOnASingleLine': ['Never', 'WithoutElse', 'OnlyFirstIf', 'AllIfsAndElse'],
    'AllowShortLambdasOnASingleLine': ['None', 'Empty', 'Inline', 'All'],
    'AllowShortLoopsOnASingleLine': BOOLEAN_OPTION_TYPE,
    'AlwaysBreakAfterDefinitionReturnType': ['None', 'All', 'TopLevel'],
    'AlwaysBreakAfterReturnType': ['None', 'All', 'TopLevel', 'AllDefinitions', 'TopLevelDefinitions'],
    'AlwaysBreakBeforeMultilineStrings': BOOLEAN_OPTION_TYPE,
    'AlwaysBreakTemplateDeclarations': ['No', 'MultiLine', 'Yes'],
    'BasedOnStyle': ['LLVM', 'Google', 'Chromium', 'Mozilla', 'WebKit', 'Microsoft', 'GNU'],
    'BinPackArguments': BOOLEAN_OPTION_TYPE,
    'BinPackParameters': BOOLEAN_OPTION_TYPE,
    'BitFieldColonSpacing': ['Both', 'None', 'Before', 'After'],
    'BraceWrapping:AfterCaseLabel': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:AfterClass': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:AfterControlStatement': ['Never', 'MultiLine', 'Always'],
    'BraceWrapping:AfterEnum': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:AfterFunction': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:AfterNamespace': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:AfterStruct': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:AfterUnion': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:AfterExternBlock': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:BeforeCatch': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:BeforeElse': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:BeforeLambdaBody': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:BeforeWhile': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:IndentBraces': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:SplitEmptyFunction': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:SplitEmptyRecord': BOOLEAN_OPTION_TYPE,
    'BraceWrapping:SplitEmptyNamespace': BOOLEAN_OPTION_TYPE,
    'BreakBeforeBinaryOperators': ['None', 'NonAssignment', 'All'],
    'BreakBeforeConceptDeclarations': BOOLEAN_OPTION_TYPE,
    'BreakBeforeInheritanceComma': BOOLEAN_OPTION_TYPE,
    'BreakBeforeTernaryOperators': BOOLEAN_OPTION_TYPE,
    'BreakConstructorInitializersBeforeComma': BOOLEAN_OPTION_TYPE,
    'BreakConstructorInitializers': ['BeforeColon', 'BeforeComma', 'AfterColon'],
    'BreakInheritanceList': ['BeforeColon', 'BeforeComma', 'AfterColon', 'AfterComma'],
    'BreakStringLiterals': BOOLEAN_OPTION_TYPE,
    'ColumnLimit': ['80', '120', '0'],
    'CompactNamespaces': BOOLEAN_OPTION_TYPE,
    'ConstructorInitializerAllOnOneLineOrOnePerLine': BOOLEAN_OPTION_TYPE,
    'ConstructorInitializerIndentWidth': ['0', '2', '3', '4', '6', '8'],
    'ContinuationIndentWidth': ['0', '2', '3', '4', '6', '8'],
    'Cpp11BracedListStyle': BOOLEAN_OPTION_TYPE,
    'EmptyLineAfterAccessModifier': ['Never', 'Leave', 'Always'],
    'EmptyLineBeforeAccessModifier': ['Never', 'Leave', 'LogicalBlock', 'Always'],
    'FixNamespaceComments': BOOLEAN_OPTION_TYPE,
    'IncludeBlocks': ['Preserve', 'Merge', 'Regroup'],
    'IndentAccessModifiers': BOOLEAN_OPTION_TYPE,
    'IndentCaseBlocks': BOOLEAN_OPTION_TYPE,
    'IndentCaseLabels': BOOLEAN_OPTION_TYPE,
    'IndentExternBlock': ['AfterExternBlock', 'NoIndent', 'Indent'],
    'IndentGotoLabels': BOOLEAN_OPTION_TYPE,
    'IndentPPDirectives': ['None', 'AfterHash', 'BeforeHash'],
    'IndentRequires': BOOLEAN_OPTION_TYPE,
    'IndentWidth': ['2', '3', '4', '8'],
    'IndentWrappedFunctionNames': BOOLEAN_OPTION_TYPE,
    'InsertTrailingCommas': ['None', 'Wrapped'],
    'KeepEmptyLinesAtTheStartOfBlocks': BOOLEAN_OPTION_TYPE,
    'LambdaBodyIndentation': ['Signature', 'OuterScope'],
    'MaxEmptyLinesToKeep': ['1', '2', '3'],
    'NamespaceIndentation': ['None', 'Inner', 'All'],
    'PenaltyBreakAssignment': ['2', '100', '1000'],
    'PenaltyBreakBeforeFirstCallParameter': ['1', '19', '100'],
    'PenaltyBreakComment': ['300'],
    'PenaltyBreakFirstLessLess': ['120'],
    'PenaltyBreakString': ['1000'],
    'PenaltyBreakTemplateDeclaration': ['10'],
    'PenaltyExcessCharacter': ['100', '1000000'],
    'PenaltyReturnTypeOnItsOwnLine': ['60', '200', '1000'],
    'PenaltyIndentedWhitespace': ['0', '1'],
    'PointerAlignment': ['Left', 'Right', 'Middle'],
    'ReferenceAlignment': ['Pointer', 'Left', 'Right', 'Middle'],
    'ReflowComments': BOOLEAN_OPTION_TYPE,
    'ShortNamespaceLines': ['0', '1'],
    'SortIncludes': ['Never', 'CaseSensitive', 'CaseInsensitive'],
    'SortUsingDeclarations': BOOLEAN_OPTION_TYPE,
    'SpaceAfterCStyleCast': BOOLEAN_OPTION_TYPE,
    'SpaceAfterLogicalNot': BOOLEAN_OPTION_TYPE,
    'SpaceAfterTemplateKeyword': BOOLEAN_OPTION_TYPE,
    'SpaceAroundPointerQualifiers': ['Default', 'Before', 'After', 'Both'],
    'SpaceBeforeAssignmentOperators': BOOLEAN_OPTION_TYPE,
    'SpaceBeforeCaseColon': BOOLEAN_OPTION_TYPE,
    'SpaceBeforeCpp11BracedList': BOOLEAN_OPTION_TYPE,
    'SpaceBeforeCtorInitializerColon': BOOLEAN_OPTION_TYPE,
    'SpaceBeforeInheritanceColon': BOOLEAN_OPTION_TYPE,
    'SpaceBeforeParens': ['Never', 'ControlStatements', 'ControlStatementsExceptControlMacros', 'NonEmptyParentheses', 'Always'],
    'SpaceBeforeRangeBasedForLoopColon': BOOLEAN_OPTION_TYPE,
    'SpaceInEmptyBlock': BOOLEAN_OPTION_TYPE,
    'SpaceInEmptyParentheses': BOOLEAN_OPTION_TYPE,
    'SpacesBeforeTrailingComments': ['0', '1'],
    'SpacesInAngles': ['Never', 'Always', 'Leave'],
    'SpacesInCStyleCastParentheses': BOOLEAN_OPTION_TYPE,
    'SpacesInConditionalStatement': BOOLEAN_OPTION_TYPE,
    'SpacesInContainerLiterals': BOOLEAN_OPTION_TYPE,
    'SpacesInParentheses': BOOLEAN_OPTION_TYPE,
    'SpacesInSquareBrackets': BOOLEAN_OPTION_TYPE,
    'SpaceBeforeSquareBrackets': BOOLEAN_OPTION_TYPE,
    'Standard': ['c++03', 'c++11', 'c++14', 'c++17', 'c++20', 'Latest'],
    'UseTab': ['Never', 'ForIndentation', 'ForContinuationAndIndentation', 'AlignWithSpaces', 'Always'],
}
PRIORITY_OPTIONS = ['BasedOnStyle', 'IndentWidth', 'UseTab', 'SortIncludes', 'IncludeBlocks']

CLANG_FORMAT_CONFIG_FILE = '.clang-format'
CXX_EXTENSIONS = ['.cpp', '.cxx', '.cc', '.c', '.hpp', '.hxx', '.hh', '.h', '.ipp']
FILE_BATCH_SIZE = 10

_T, _U = TypeVar('T'), TypeVar('U')
StyleSettings = flatdict.FlatDict
StyleObjectiveFun = Callable[[StyleSettings], int]
ProcessDispatcherFun = Callable[[Iterable[_T]], Iterable[_U]]
ValueCostMap = Dict[str, int]


class ClangFormatLoader(yaml.SafeLoader):
    # reset implicit type handlers - treat all scalars as strings
    yaml_implicit_resolvers = {}

def load_clang_format_config(file: Union[TextIO, str]) -> StyleSettings:
    return StyleSettings(yaml.load(file, Loader=ClangFormatLoader))


class ClangFormatDumper(yaml.SafeDumper):
    # reset implicit type handlers - treat all scalars as strings
    yaml_implicit_resolvers = {}

def save_clang_format_config(config: StyleSettings):
    with open(CLANG_FORMAT_CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(config.as_dict(), f, Dumper=ClangFormatDumper, explicit_start=True, explicit_end=True, sort_keys=False)


class ReplacementsXmlHandler(xml.sax.handler.ContentHandler):
    _started: bool = False
    _num_remove: int
    _num_insert: int
    _replacements: List[Tuple[int, int]]

    def __init__(self) -> None:
        super().__init__()
        self._replacements = []

    def startElement(self, name: str, attrs: Dict[str, str]):
        if name == 'replacement':
            self._started = True
            self._num_remove = int(attrs.get('length', 0))
            self._num_insert = 0

    def characters(self, content: str):
        if self._started:
            self._num_insert += len(content)

    def endElement(self, name: str):
        if self._started:
            self._replacements.append((self._num_remove, self._num_insert))
            self._started = False

    def get_total_cost(self):
        return sum(ninsert + nremove for ninsert, nremove in self._replacements)


def eval_clang_format_config_cost(config: StyleSettings, file_list: List[str], dispatcher: ProcessDispatcherFun[List[str], Iterable[str]]) -> int:
    def make_clang_format_args(files: Iterable[str]) -> List[str]:
        return ['clang-format', '--style=file', '--output-replacements-xml', *files]

    # based on https://stackoverflow.com/a/22045226
    def chunkify(it: Iterable[_T], size: int) -> Iterable[Tuple[_T]]:
        it = iter(it)
        return iter(lambda: tuple(itertools.islice(it, size)), ())

    save_clang_format_config(config)
    handler = ReplacementsXmlHandler()
    parser = xml.sax.make_parser(['xml.sax.IncrementalParser'])
    parser.setContentHandler(handler)
    file_list_chunks = chunkify(file_list, FILE_BATCH_SIZE)
    for output_xml in dispatcher(map(make_clang_format_args, file_list_chunks)):
        for line in output_xml:
            if line.startswith("<?xml version='1.0'?>"):
                parser.close()
                parser.reset()
            parser.feed(line)
    return handler.get_total_cost()


def capture_process_output(args: List[str], timeout: int=10) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout).stdout


def get_safe_option_values(key: str, current_config: StyleSettings) -> List[str]:
    safe_values = ALL_TUNEABLE_OPTIONS[key]
    if key in ['BinPackParameters', 'InsertTrailingCommas']:
        def get_effective_config() -> StyleSettings:
            save_clang_format_config(current_config)
            output_txt = capture_process_output(['clang-format', '--style=file', '--dump-config'])
            return load_clang_format_config(output_txt)
        effective_config = get_effective_config()
        safe_values = safe_values.copy()
        if key == 'InsertTrailingCommas' and effective_config['BinPackParameters'] == 'true':
            safe_values.remove('Wrapped')
        elif key == 'BinPackParameters' and effective_config['InsertTrailingCommas'] == 'Wrapped':
            safe_values.remove('true')
    return safe_values


def optimize_configuration(
        rw_config: StyleSettings,
        cost_fun: StyleObjectiveFun,
        include_opts: Optional[Iterable[str]] = None,
        exclude_opts: Optional[Iterable[str]] = None):
    if include_opts is None:
        include_opts = ALL_TUNEABLE_OPTIONS.keys()
    if exclude_opts is None:
        exclude_opts = rw_config.keys()
    tuneable_options = ordered_diff(include_opts, exclude_opts)
    if not tuneable_options:
        return

    def calc_values_costs(baseline: StyleSettings, key: str) -> ValueCostMap:
        config = baseline.copy()
        costs: ValueCostMap = {}
        for val in get_safe_option_values(key, baseline):
            if baseline.get(key) == val:
                continue # skip baseline cost calculation
            try:
                config[key] = val
                costs[val] = cost_fun(config)
            except subprocess.CalledProcessError as ex:
                print('\nclang-format error:\n', ex.stderr, sep='', file=sys.stderr)
        return costs

    def costs_to_string(costs: ValueCostMap) -> str:
        sorted_costs = sorted(costs.items(), key=lambda kv: kv[1])
        formatted_costs = [f'{val}:{cost}' for val, cost in sorted_costs]
        return '{' + ' '.join(formatted_costs) + '}'

    current_cost = cost_fun(rw_config)
    visited_keys: Set[str] = set()
    print(f'Trying to optimize {len(tuneable_options)} variables...')
    for key in itertools.cycle(tuneable_options):
        if key in visited_keys:
            break
        all_costs = calc_values_costs(rw_config, key)
        best_val, best_cost = min(all_costs.items(), key=lambda kv: kv[1])

        if best_cost < current_cost:
            if len(visited_keys) > 1:
                print()
            if key in rw_config:
                # include the baseline cost
                all_costs[rw_config[key]] = current_cost
            print(f'Set {key}={best_val} cost {current_cost}=>{best_cost} {costs_to_string(all_costs)}')
            rw_config[key] = best_val
            current_cost = best_cost
            visited_keys.clear()
        else:
            print('.', end='', flush=True)
        visited_keys.add(key)
    print('\nDone!\n')


def minimize_configuration(
        rw_config: StyleSettings,
        cost_fun: StyleObjectiveFun,
        frozen_options: Iterable[str]):
    tuneable_keys = ordered_diff(rw_config.keys(), frozen_options)
    if not tuneable_keys:
        return

    def calc_defaulted_value_cost(baseline: StyleSettings, key: str) -> int:
        config = baseline.copy()
        del config[key]
        return cost_fun(config)

    current_cost = cost_fun(rw_config)
    visited_keys: Set[str] = set()
    print('Trying to minimize the configuration...')
    for key in itertools.cycle(tuneable_keys):
        if key in visited_keys:
            break

        try:
            new_cost = calc_defaulted_value_cost(rw_config, key)
        except KeyError:
            continue
        except subprocess.CalledProcessError as ex:
            print('\nclang-format error:\n', ex.stderr, sep='', file=sys.stderr)
            continue

        if new_cost < current_cost:
            if len(visited_keys) > 1:
                print()
            print(f'Removed {key} cost {current_cost} => {new_cost}')
            del rw_config[key]
            current_cost = new_cost
            visited_keys.clear()
        else:
            print('.', end='', flush=True)
        visited_keys.add(key)
    print('\nDone!\n')


def ordered_diff(first: Iterable[_T], second: Iterable[_T]) -> List[_T]:
    return [k for k in first if k not in second]


def verify_clang_version():
    try:
        clang_version = capture_process_output(['clang-format', '--version'])
    except FileNotFoundError:
        sys.exit('clang-format not found!')
    if not clang_version.startswith('clang-format version 13.0.0'):
        sys.exit('clang-format version 13.0.0 is required')


def collect_source_files(args: List[str]) -> List[str]:
    def is_cxx_file(filename: str) -> bool:
        _, ext = os.path.splitext(filename)
        return ext.lower() in CXX_EXTENSIONS

    def walk_files(dirpath: str) -> Iterable[str]:
        return [os.path.join(root, name) for root, _, files in os.walk(dirpath) for name in files]

    expanded_args = list(path for globspec in args for path in glob.glob(globspec, recursive=True))
    file_list = list(path for path in expanded_args if os.path.isfile(path))
    for files in [walk_files(path) for path in expanded_args if os.path.isdir(path)]:
        file_list.extend(files)
    return list(path for path in file_list if is_cxx_file(path))


class ThreadPoolProcessDispatcher(object):
    _executor: concurrent.futures.Executor

    def __init__(self, max_workers:int=5) -> None:
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def __enter__(self):
        self._executor.__enter__()
        return self

    def __exit__(self, *exc):
        return self._executor.__exit__(*exc)

    def map(self, args_list: Iterable[List[str]]) -> Iterable[Iterable[str]]:
        def dispatch_one(args: List[str]) -> Iterable[str]:
            return capture_process_output(args).splitlines()
        return self._executor.map(dispatch_one, args_list)


def main():
    verify_clang_version()
    try:
        with open(CLANG_FORMAT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            baseline_config = load_clang_format_config(f)
    except FileNotFoundError:
        baseline_config = StyleSettings({'Language':'Cpp'})
        print(f'{CLANG_FORMAT_CONFIG_FILE} not found: will create it for you')

    file_list = collect_source_files(sys.argv[1:] if len(sys.argv) > 1 else ['.'])
    print(f'Source files ({len(file_list)}):', ' '.join(file_list), '\n')

    current_config = baseline_config.copy()
    exclude_options: List[str] = list(baseline_config.keys())
    if current_config.setdefault('BreakBeforeBraces', 'Custom') != 'Custom':
        # do not optimize brace wrapping when a preset has been set
        exclude_options.extend(filter(lambda k: k.startswith('BraceWrapping:'), ALL_TUNEABLE_OPTIONS))
    t_start = time.monotonic()
    try:
        with ThreadPoolProcessDispatcher(max_workers=5) as dispatcher:
            def cost_func(config: StyleSettings) -> int:
                return eval_clang_format_config_cost(config, file_list, dispatcher.map)
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
