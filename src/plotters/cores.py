import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from src.common.tools import is_combination_to_do

def plot_cores(master_result_df: pd.DataFrame, results_path: Path, config):

    for key, master_iterations in master_result_df.groupby(['config', 'group', 'instance']):

        if not is_combination_to_do(key[0], key[1], key[2], config):
            continue

        cores_data: dict[str, pd.DataFrame] = {}

        for core_type in ['generalist', 'basic', 'reduced', 'pruned']:
            if f'{core_type}_core_number' not in master_iterations or f'{core_type}_average_core_size' not in master_iterations:
                continue
            
            cores_data[core_type] = master_iterations[['config', 'group', 'instance', 'iteration', f'{core_type}_core_number', f'{core_type}_average_core_size', f'{core_type}_min_core_size', f'{core_type}_max_core_size']]
            cores_data[core_type] = cores_data[core_type].rename(columns={f'{core_type}_core_number': 'core_number', f'{core_type}_average_core_size': 'average_core_size', f'{core_type}_min_core_size': 'min_core_size', f'{core_type}_max_core_size': 'max_core_size'})
            cores_data[core_type] = cores_data[core_type].sort_values(by='iteration')
        
        is_empty = True
        for core_data in cores_data.values():
            core_data = core_data.drop(columns=['config', 'group', 'instance', 'iteration']).dropna(how='all')
            if not core_data.empty:
                is_empty = False
                break
        if is_empty:
            continue

        min_core_size = 1000
        max_core_size = 0

        for core_type, value in cores_data.items():
            cores_data[core_type] = value.dropna(how='all')
            min_core_size = min(min_core_size, cores_data[core_type]['core_number'].min())
            max_core_size = max(max_core_size, cores_data[core_type]['core_number'].max())

        colors = {
            'generalist': 'black',
            'basic': 'blue',
            'reduced': 'green',
            'pruned': 'red'
        }

        fig, axs = plt.subplots(2)

        for core_type, value in cores_data.items():
            marker_sizes: pd.Series = (value['core_number'] - min_core_size) / (max_core_size - min_core_size) * 20 + 10
            axs[0].scatter(value['iteration'], value['average_core_size'], s=marker_sizes, marker='s', facecolors='none', linewidths=2.0, color=colors[core_type])
            axs[0].plot(value['iteration'], value['average_core_size'], color=colors[core_type], label=core_type)
            axs[0].fill_between(value['iteration'], value['min_core_size'], value['max_core_size'], alpha=0.25, linewidth=0, color=colors[core_type])
            axs[1].plot(value['iteration'], value['core_number'], color=colors[core_type], label=core_type)

        axs[0].legend()
        axs[0].set_ylabel('Core size')
        axs[0].set_title(f'Cores of config \'{key[0]}\'\ngroup \'{key[1]}\' instance \'{key[2]}\'')
        axs[1].set_xlabel('Iteration')
        axs[1].set_ylabel('Core number')

        save_path = results_path.joinpath(f'{key[0]}__{key[1]}__{key[2]}', 'plots')
        save_path.mkdir(exist_ok=True)

        fig.savefig(save_path.joinpath('cores.png'))
        plt.close('all')