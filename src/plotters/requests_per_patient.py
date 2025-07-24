import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from src.common.tools import is_combination_to_do

def plot_requests_per_patient(master_result_df: pd.DataFrame, results_path: Path, config):

    data = master_result_df[[
        'config', 'group', 'instance', 'iteration',
        'master_average_request_number_per_patient_same_day', 'master_min_request_number_per_patient_same_day', 'master_max_request_number_per_patient_same_day',
        'final_average_request_number_per_patient_same_day', 'final_min_request_number_per_patient_same_day', 'final_max_request_number_per_patient_same_day',
        'master_average_care_unit_used_per_patient_same_day', 'master_min_care_unit_used_per_patient_same_day', 'master_max_care_unit_used_per_patient_same_day',
        'final_average_care_unit_used_per_patient_same_day', 'final_min_care_unit_used_per_patient_same_day', 'final_max_care_unit_used_per_patient_same_day',
    ]]

    if 'total_operator_used_per_patient' in master_result_df and 'min_operator_used_per_patient' in master_result_df and 'max_operator_used_per_patient' in master_result_df:
        fat_data = master_result_df[[
            'config', 'group', 'instance', 'iteration',
            'master_total_operator_used_per_patient', 'master_min_operator_used_per_patient', 'master_max_operator_used_per_patient',
            'final_total_operator_used_per_patient', 'final_min_operator_used_per_patient', 'final_max_operator_used_per_patient'
        ]]
    else:
        fat_data = None

    for key, iteration_data in data.groupby(['config', 'group', 'instance']):

        iteration_data = iteration_data.sort_values('iteration')

        if not is_combination_to_do(key[0], key[1], key[2], config):
            continue

        fig, axs = plt.subplots(2, 2)

        axs[0, 0].plot(iteration_data['iteration'], iteration_data['master_average_request_number_per_patient_same_day'], 'o-', color='red')
        axs[0, 0].fill_between(iteration_data['iteration'], iteration_data['master_min_request_number_per_patient_same_day'], iteration_data['master_max_request_number_per_patient_same_day'], alpha=0.25, linewidth=0, color='red')
        axs[0, 1].plot(iteration_data['iteration'], iteration_data['final_average_request_number_per_patient_same_day'], 'o-', color='green')
        axs[0, 1].fill_between(iteration_data['iteration'], iteration_data['final_min_request_number_per_patient_same_day'], iteration_data['final_max_request_number_per_patient_same_day'], alpha=0.25, linewidth=0, color='green')
        
        axs[1, 0].plot(iteration_data['iteration'], iteration_data['master_average_care_unit_used_per_patient_same_day'], 'o-', color='red', label='care units')
        axs[1, 0].fill_between(iteration_data['iteration'], iteration_data['master_min_care_unit_used_per_patient_same_day'], iteration_data['master_max_care_unit_used_per_patient_same_day'], alpha=0.25, linewidth=0, color='red')
        axs[1, 1].plot(iteration_data['iteration'], iteration_data['final_average_care_unit_used_per_patient_same_day'], 'o-', color='green', label='care units')
        axs[1, 1].fill_between(iteration_data['iteration'], iteration_data['final_min_care_unit_used_per_patient_same_day'], iteration_data['final_max_care_unit_used_per_patient_same_day'], alpha=0.25, linewidth=0, color='green')

        if fat_data is not None:
            
            fat_iteration_data = fat_data[
                (master_result_df['config'] == key[0]) &
                (master_result_df['group'] == key[1]) &
                (master_result_df['instance'] == key[2])
            ]

            fat_iteration_data = fat_iteration_data.sort_values('iteration')
            
            axs[1, 0].plot(fat_iteration_data['iteration'], fat_iteration_data['master_average_care_unit_used_per_patient_same_day'], color='red', label='operators')
            axs[1, 0].fill_between(fat_iteration_data['iteration'], fat_iteration_data['master_min_care_unit_used_per_patient_same_day'], fat_iteration_data['master_max_care_unit_used_per_patient_same_day'], alpha=0.25, linewidth=0, color='red')
            axs[1, 1].plot(fat_iteration_data['iteration'], fat_iteration_data['final_average_care_unit_used_per_patient_same_day'], color='green', label='operators')
            axs[1, 1].fill_between(fat_iteration_data['iteration'], fat_iteration_data['final_min_care_unit_used_per_patient_same_day'], fat_iteration_data['final_max_care_unit_used_per_patient_same_day'], alpha=0.25, linewidth=0, color='green')

        axs[0, 0].set_xticks(iteration_data['iteration'], labels=iteration_data['iteration'])
        axs[0, 1].set_xticks(iteration_data['iteration'], labels=iteration_data['iteration'])
        axs[1, 0].set_xticks(iteration_data['iteration'], labels=iteration_data['iteration'])
        axs[1, 1].set_xticks(iteration_data['iteration'], labels=iteration_data['iteration'])
        
        axs[0, 0].set_title('Master requests')
        axs[0, 1].set_title('Subproblem requests')
        axs[1, 0].set_title('Master patient resources')
        axs[1, 1].set_title('Subproblem patient resources')
        axs[0, 0].set_ylabel('Request number')
        axs[1, 0].set_xlabel('Iteration')
        axs[1, 1].set_xlabel('Iteration')
        axs[1, 0].set_ylabel('Resource used')
        axs[1, 0].legend()
        axs[1, 1].legend()
        fig.suptitle(f'Requests per patient from config \'{key[0]}\'\ngroup \'{key[1]}\' instance \'{key[2]}\'')
        fig.tight_layout()

        save_path = results_path.joinpath(f'{key[0]}__{key[1]}__{key[2]}', 'plots')
        save_path.mkdir(exist_ok=True)

        fig.savefig(save_path.joinpath('requests_per_patient.png'))
        plt.close('all')