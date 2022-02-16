import itertools
import sys
from typing import Callable, Dict, Iterable, List, Optional, Set

from .config import StyleSettings
from .config import get_effective_clang_format_config
from .execution import ProcessRunError
from .options import ALL_TUNEABLE_OPTIONS
from .utils import ordered_diff

StyleObjectiveFun = Callable[[StyleSettings], int]
ValueCostMap = Dict[str, int]


def get_safe_option_values(key: str, current_config: StyleSettings) -> List[str]:
    safe_values = ALL_TUNEABLE_OPTIONS[key]
    if key in ['BinPackParameters', 'InsertTrailingCommas']:
        effective_config = get_effective_clang_format_config(current_config)
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
        exclude_opts: Optional[Iterable[str]] = None
        ):
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
            except ProcessRunError as ex:
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
        frozen_options: Iterable[str]
        ):
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
        except ProcessRunError as ex:
            print('\nclang-format error:\n', ex.stderr, sep='', file=sys.stderr)
            continue

        if new_cost <= current_cost:
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
