import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from src.common.tools import is_combination_to_do

def plot_result_value_vs_time(
        master_result_df: pd.DataFrame, subproblem_result_df: pd.DataFrame,
        results_path: Path, config):

    master_result_df = master_result_df[['config', 'group', 'instance', 'iteration',
        'master_time', 'master_objective_value', 'cache_time', 'cache_objective_value', 'final_objective_value']]
    master_result_df = master_result_df.fillna(0)
    
    for key, master_iterations in master_result_df.groupby(['config', 'group', 'instance']):

        if not is_combination_to_do(key[0], key[1], key[2], config):
            continue

        b = subproblem_result_df[
            (subproblem_result_df['config'] == key[0]) &
            (subproblem_result_df['group'] == key[1]) &
            (subproblem_result_df['instance'] == key[2])]
        
        b = b[['iteration', 'time']]
        a = master_iterations[['iteration', 'master_time', 'master_objective_value',
            'cache_time', 'cache_objective_value', 'final_objective_value']]
        
        b = b.rename(columns={'time': 'subproblem_time'})
        a = a.rename(columns={
            'master_objective_value': 'master_value',
            'cache_objective_value': 'cache_value',
            'final_objective_value': 'final_value'})

        k = pd.merge(a, b.groupby('iteration').sum(), on='iteration').set_index('iteration').sort_index()

        cache_cumsum = k['cache_time'].cumsum()
        master_cumsum = k['master_time'].cumsum()
        subproblem_cumsum = k['subproblem_time'].cumsum()

        cache_xs = master_cumsum + cache_cumsum.shift(1, fill_value=0) + subproblem_cumsum.shift(1, fill_value=0)
        master_xs = master_cumsum + cache_cumsum + subproblem_cumsum.shift(1, fill_value=0)
        subproblem_xs = master_cumsum + cache_cumsum + subproblem_cumsum

        fig, ax = plt.subplots()

        if len(cache_xs) > 2:
            ax.plot(cache_xs[2:], k['cache_value'][2:], color='red', marker='s', markeredgecolor='white', label='cache')
        ax.plot(master_xs, k['master_value'], color='blue', marker='o', markeredgecolor='white', label='master')
        ax.plot(subproblem_xs, k['final_value'], color='green', marker='^', markeredgecolor='white', label='subproblem')

        ax.legend()
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Result value')
        ax.set_title(f'Result values of config \'{key[0]}\'\ngroup \'{key[1]}\' instance \'{key[2]}\'')

        save_path = results_path.joinpath(f'{key[0]}__{key[1]}__{key[2]}', 'plots')
        save_path.mkdir(exist_ok=True)

        fig.savefig(save_path.joinpath('result_value_vs_time.png'))
        plt.close('all')