import concurrent.futures, subprocess
import itertools
import os, os.path, sys, time, glob
import yaml
import xml.sax, xml.sax.handler
from typing import Callable, Iterable, Dict, List, Tuple, TypeVar

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
    'AlignTrailingComments': ['false', 'true'],
    'AllowAllArgumentsOnNextLine': ['false', 'true'],
    'AllowAllConstructorInitializersOnNextLine': ['false', 'true'],
    'AllowAllParametersOfDeclarationOnNextLine': ['false', 'true'],
    'AllowShortBlocksOnASingleLine': ['Never', 'Empty', 'Always'],
    'AllowShortCaseLabelsOnASingleLine': ['false', 'true'],
    'AllowShortEnumsOnASingleLine': ['false', 'true'],
    'AllowShortFunctionsOnASingleLine': ['None', 'InlineOnly', 'Empty', 'Inline', 'All'],
    'AllowShortIfStatementsOnASingleLine': ['Never', 'WithoutElse', 'OnlyFirstIf', 'AllIfsAndElse'],
    'AllowShortLambdasOnASingleLine': ['None', 'Empty', 'Inline', 'All'],
    'AllowShortLoopsOnASingleLine': ['false', 'true'],
    'AlwaysBreakAfterDefinitionReturnType': ['None', 'All', 'TopLevel'],
    'AlwaysBreakAfterReturnType': ['None', 'All', 'TopLevel', 'AllDefinitions', 'TopLevelDefinitions'],
    'AlwaysBreakBeforeMultilineStrings': ['false', 'true'],
    'AlwaysBreakTemplateDeclarations': ['No', 'MultiLine', 'Yes'],
    'BasedOnStyle': ['LLVM', 'Google', 'Chromium', 'Mozilla', 'WebKit', 'Microsoft', 'GNU'],
    'BinPackArguments': ['true', 'false'],
    'BinPackParameters': ['true', 'false'],
    'BitFieldColonSpacing': ['Both', 'None', 'Before', 'After'],
    'BreakBeforeBinaryOperators': ['None', 'NonAssignment', 'All'],
    'BreakBeforeConceptDeclarations': ['false', 'true'],
    'BreakBeforeBraces': ['Attach', 'Linux', 'Mozilla', 'Stroustrup', 'Allman', 'Whitesmiths', 'GNU', 'WebKit'],
    'BreakBeforeInheritanceComma': ['false', 'true'],
    'BreakBeforeTernaryOperators': ['false', 'true'],
    'BreakConstructorInitializersBeforeComma': ['false', 'true'],
    'BreakConstructorInitializers': ['BeforeColon', 'BeforeComma', 'AfterColon'],
    'BreakInheritanceList': ['BeforeColon', 'BeforeComma', 'AfterColon', 'AfterComma'],
    'BreakStringLiterals': ['false', 'true'],
    'ColumnLimit': ['80', '120', '0'],
    'CompactNamespaces': ['false', 'true'],
    'ConstructorInitializerAllOnOneLineOrOnePerLine': ['false', 'true'],
    'ConstructorInitializerIndentWidth': ['0', '2', '3', '4', '6', '8'],
    'ContinuationIndentWidth': ['0', '2', '3', '4', '6', '8'],
    'Cpp11BracedListStyle': ['false', 'true'],
    'EmptyLineAfterAccessModifier': ['Never', 'Leave', 'Always'],
    'EmptyLineBeforeAccessModifier': ['Never', 'Leave', 'LogicalBlock', 'Always'],
    'FixNamespaceComments': ['false', 'true'],
    'IncludeBlocks': ['Preserve', 'Merge', 'Regroup'],
    'IndentAccessModifiers': ['false', 'true'],
    'IndentCaseLabels': ['false', 'true'],
    'IndentCaseBlocks': ['false', 'true'],
    'IndentExternBlock': ['AfterExternBlock', 'NoIndent', 'Indent'],
    'IndentGotoLabels': ['false', 'true'],
    'IndentPPDirectives': ['None', 'AfterHash', 'BeforeHash'],
    'IndentRequires': ['false', 'true'],
    'IndentWidth': ['2', '3', '4', '8'],
    'IndentWrappedFunctionNames': ['false', 'true'],
    'InsertTrailingCommas': ['None', 'Wrapped'],
    'KeepEmptyLinesAtTheStartOfBlocks': ['false', 'true'],
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
    'ReflowComments': ['false', 'true'],
    'ShortNamespaceLines': ['0', '1'],
    'SortIncludes': ['Never', 'CaseSensitive', 'CaseInsensitive'],
    'SortUsingDeclarations': ['false', 'true'],
    'SpaceAfterCStyleCast': ['false', 'true'],
    'SpaceAfterLogicalNot': ['false', 'true'],
    'SpaceAfterTemplateKeyword': ['false', 'true'],
    'SpaceAroundPointerQualifiers': ['Default', 'Before', 'After', 'Both'],
    'SpaceBeforeAssignmentOperators': ['false', 'true'],
    'SpaceBeforeCaseColon': ['false', 'true'],
    'SpaceBeforeCpp11BracedList': ['false', 'true'],
    'SpaceBeforeCtorInitializerColon': ['false', 'true'],
    'SpaceBeforeInheritanceColon': ['false', 'true'],
    'SpaceBeforeParens': ['Never', 'ControlStatements', 'ControlStatementsExceptControlMacros', 'NonEmptyParentheses', 'Always'],
    'SpaceBeforeRangeBasedForLoopColon': ['false', 'true'],
    'SpaceInEmptyBlock': ['false', 'true'],
    'SpaceInEmptyParentheses': ['false', 'true'],
    'SpacesBeforeTrailingComments': ['0', '1'],
    'SpacesInAngles': ['Never', 'Always', 'Leave'],
    'SpacesInCStyleCastParentheses': ['false', 'true'],
    'SpacesInConditionalStatement': ['false', 'true'],
    'SpacesInContainerLiterals': ['false', 'true'],
    'SpacesInParentheses': ['false', 'true'],
    'SpacesInSquareBrackets': ['false', 'true'],
    'SpaceBeforeSquareBrackets': ['false', 'true'],
    'Standard': ['c++03', 'c++11', 'c++14', 'c++17', 'c++20', 'Latest'],
    'UseTab': ['Never', 'ForIndentation', 'ForContinuationAndIndentation', 'AlignWithSpaces', 'Always'],
}
PRIORITY_OPTIONS = ['BasedOnStyle', 'BreakBeforeBraces', 'IndentWidth', 'UseTab', 'SortIncludes', 'IncludeBlocks']
EMPTY_VAL = ''

CLANG_FORMAT_CONFIG_FILE = '.clang-format'
CXX_EXTENSIONS = ['.cpp', '.cxx', '.cc', '.c', '.hpp', '.hxx', '.hh', '.h', '.ipp']

_T, _U = TypeVar('T'), TypeVar('U')
StyleSettings = Dict[str, str]
StyleObjectiveFun = Callable[[StyleSettings], int]
MapDispatcherFun = Callable[[Callable[[_T], _U], Iterable[_T]], Iterable[_U]]
ValueCostMap = Dict[str, int]


def save_clang_format_config(config: StyleSettings):
    with open(CLANG_FORMAT_CONFIG_FILE, 'w') as f:
        yaml.dump(config, f, Dumper=yaml.SafeDumper, explicit_start=True, explicit_end=True, sort_keys=False)


class ReplacementsXmlHandler(xml.sax.handler.ContentHandler):
    _started: bool = False
    _num_remove: int
    _num_insert: int
    _replacements: List[Tuple[int, int]]

    def __init__(self) -> None:
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


def eval_clang_format_config_cost(config: StyleSettings, file_list: List[str], mapper: MapDispatcherFun[Iterable[str], str]) -> int:
    def run_clang_format(files: Iterable[str]) -> str:
        clang_args = ['clang-format', '--style=file', '--output-replacements-xml', *files]
        return subprocess.run(clang_args, check=True, capture_output=True, text=True).stdout

    def chunkify(it: Iterable[str], size: int) -> Iterable[Tuple[str]]:
        it = iter(it)
        return iter(lambda: tuple(itertools.islice(it, size)), ())

    save_clang_format_config(config)
    handler = ReplacementsXmlHandler()
    parser = xml.sax.make_parser(['xml.sax.IncrementalParser'])
    parser.setContentHandler(handler)
    for output_xml in mapper(run_clang_format, chunkify(file_list, 10)):
        for line in output_xml.splitlines():
            if line.startswith("<?xml version='1.0'?>"):
                parser.close()
                parser.reset()
            parser.feed(line)
    return handler.get_total_cost()


def optimize_configuration(rw_config: StyleSettings, tuneable_options: Iterable[str], cost_fun: StyleObjectiveFun):
    effective_tuneable_options = [k for k in tuneable_options if not k in rw_config]
    if not effective_tuneable_options:
        return

    def calc_values_costs(baseline: StyleSettings, key: str) -> ValueCostMap:
        config = baseline.copy()
        costs: ValueCostMap = {}
        if key in config and key in effective_tuneable_options:
            del config[key]
            # prefer defaulted values
            costs[EMPTY_VAL] = cost_fun(config) - 1
        for val in ALL_TUNEABLE_OPTIONS[key]:
            try:
                config[key] = val
                costs[val] = cost_fun(config)
            except subprocess.CalledProcessError:
                print('!', end='', flush=True)
        return costs

    def costs_to_string(costs: ValueCostMap) -> str:
        sorted_costs = sorted(costs.items(), key=lambda kv: kv[1])
        formatted_costs = [f'{val}:{cost}' for val, cost in sorted_costs]
        return '{' + ' '.join(formatted_costs) + '}'

    current_cost = cost_fun(rw_config)
    noop_sentinel = None
    print(f'Trying to optimize {len(effective_tuneable_options)} variables...')
    t_start = time.monotonic()
    for key in itertools.cycle(effective_tuneable_options):
        if key == noop_sentinel:
            break
        all_costs = calc_values_costs(rw_config, key)
        best_val, best_cost = min(all_costs.items(), key=lambda kv: kv[1])

        if best_cost < current_cost:
            if noop_sentinel:
                print()
                noop_sentinel = None
            print(f'{key}={best_val} cost {current_cost} => {best_cost} {costs_to_string(all_costs)}')
            if best_val == EMPTY_VAL:
                del rw_config[key]
            else:
                rw_config[key] = best_val
            current_cost = best_cost
        else:
            if not noop_sentinel:
                noop_sentinel = key
            print('.', end='', flush=True)
    t_end = time.monotonic()
    print(f'\nDone! Processing time: {t_end-t_start} seconds\n')


def verify_clang_version():
    try:
        clang_version = subprocess.run(['clang-format', '--version'], check=True, capture_output=True).stdout
    except FileNotFoundError:
        sys.exit('clang-format not found!')
    if not clang_version.startswith(b'clang-format version 13.0.0'):
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


def main():
    verify_clang_version()
    try:
        with open(CLANG_FORMAT_CONFIG_FILE, 'r') as f:
            baseline_config: StyleSettings = yaml.load(f, Loader=yaml.BaseLoader)
    except FileNotFoundError:
        baseline_config: StyleSettings = {'Language':'Cpp'}
        print(f'{CLANG_FORMAT_CONFIG_FILE} not found: will create it for you')

    file_list = collect_source_files(sys.argv[1:] if len(sys.argv) > 1 else ['.'])
    print('Source files:', ' '.join(file_list), '\n')

    current_config = baseline_config.copy()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            cost_func: StyleObjectiveFun = lambda config: eval_clang_format_config_cost(config, file_list, executor.map)
            # start with most impactful options
            optimize_configuration(current_config, PRIORITY_OPTIONS, cost_func)
            # then continue with the rest
            optimize_configuration(current_config, ALL_TUNEABLE_OPTIONS.keys(), cost_func)
    except KeyboardInterrupt:
        print('\nInterrupted')

    print(f'Saving best configuration to {CLANG_FORMAT_CONFIG_FILE}')
    save_clang_format_config(current_config)

if __name__ == '__main__':
    main()
