import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from src.common.tools import is_combination_to_do

def plot_solving_times_by_day(
        subproblem_result_df: pd.DataFrame,
        results_path: Path, config):
    
    for key, subproblem_iterations in subproblem_result_df.groupby(['config', 'group', 'instance']):

        if not is_combination_to_do(key[0], key[1], key[2], config):
            continue

        subproblem_iterations = subproblem_iterations[['iteration', 'day', 'time', 'rejected_request_number']]
        image = subproblem_iterations.pivot(index='day', columns='iteration', values='time')
        not_sat = subproblem_iterations[subproblem_iterations['rejected_request_number'] > 0][['iteration', 'day']]

        fig, ax = plt.subplots()
        plt.subplots_adjust(left=0.2, right=0.68)

        img = ax.imshow(image, cmap='Spectral_r')
        cbar = fig.colorbar(img, ax=ax, shrink=0.7)
        cbar.set_label('Time (s)')

        ax.scatter(not_sat['iteration'] - 1, not_sat['day'], marker='x', color='black', s=5)
        
        ax.set_yticks(image.index, labels=image.index)
        ax.set_ylabel('Day')
        
        ax.set_xticks(image.columns - 1, labels=image.columns)
        ax.set_xlabel('Iteration')
        
        ax.set_title(f'Solving times per day of config \'{key[0]}\'\ngroup \'{key[1]}\' instance \'{key[2]}\'')

        save_path = results_path.joinpath(f'{key[0]}__{key[1]}__{key[2]}', 'plots')
        save_path.mkdir(exist_ok=True)

        fig.savefig(save_path.joinpath('solving_times_by_day.png'))
        plt.close('all')