import matplotlib.pyplot as plt
from pathlib import Path
import json

from src.common.custom_types import PatientServiceOperator
from src.common.file_load_and_dump import decode_master_result, decode_final_result
from src.common.tools import is_combination_to_do

def plot_equal_requests_between_iterations(input_path: Path, config):
    
    for result_directory in input_path.iterdir():
        if not result_directory.is_dir():
            continue
        if result_directory.name in ['analysis', 'plots']:
            continue

        tokens = result_directory.name.split('__')
        if len(tokens) != 3:
            continue

        config_name = tokens[0]
        group_name = tokens[1]
        instance_name = tokens[2]

        if not is_combination_to_do(config_name, group_name, instance_name, config):
            continue

        iteration_index = 1
        iteration_result_directory = result_directory.joinpath(f'iter_{iteration_index}')

        prev_master_result = None
        prev_final_result = None

        master_data: tuple[list[int], list[int], list[int]] = ([], [], [])
        final_data: tuple[list[int], list[int], list[int]] = ([], [], [])

        while iteration_result_directory.exists():

            master_result_path = iteration_result_directory.joinpath('master_result.json')
            if not master_result_path.exists():
                continue
            with open(master_result_path, 'r') as file:
                master_result = decode_master_result(json.load(file))
            
            final_result_path = iteration_result_directory.joinpath('final_result.json')
            if not final_result_path.exists():
                continue
            with open(final_result_path, 'r') as file:
                final_result = decode_final_result(json.load(file))

            iteration_index += 1
            iteration_result_directory = result_directory.joinpath(f'iter_{iteration_index}')

            if prev_master_result is None or prev_final_result is None:
                prev_master_result = master_result
                prev_final_result = final_result
                continue

            master_data[0].append(iteration_index - 1)
            final_data[0].append(iteration_index - 1)
            
            master_data[1].append(sum(len(requests) for requests in master_result.scheduled.values()))
            final_data[1].append(sum(len(requests) for requests in final_result.scheduled.values()))

            equal_master_requests = 0
            for day_name, requests in master_result.scheduled.items():
                
                prev_requests = prev_master_result.scheduled[day_name]
                
                for request in requests:
                    for prev_request in prev_requests:
                
                        if request.patient_name != prev_request.patient_name or request.service_name != prev_request.service_name:
                            continue
                        if isinstance(request, PatientServiceOperator) and request.operator_name != prev_request.operator_name: # type: ignore
                            continue
                
                        equal_master_requests += 1
                        break
            
            master_data[2].append(equal_master_requests)

            equal_final_requests = 0
            for day_name, requests in final_result.scheduled.items():
                
                prev_requests = prev_final_result.scheduled[day_name]
                
                for request in requests:
                    for prev_request in prev_requests:
                
                        if request.patient_name != prev_request.patient_name or request.service_name != prev_request.service_name:
                            continue
                        if isinstance(request, PatientServiceOperator) and request.operator_name != prev_request.operator_name:
                            continue
                
                        equal_final_requests += 1
                        break
            
            final_data[2].append(equal_final_requests)

        if len(master_data[0]) == 0:
            return

        fig, ax = plt.subplots()

        ax.plot(master_data[0], master_data[1], '-', color='blue', label='master requests')
        ax.plot(master_data[0], master_data[2], 'x', color='blue', label='equal master requests')
        ax.plot(final_data[0], final_data[1], '-', color='red', label='subproblem requests')
        ax.plot(final_data[0], final_data[2], 'x', color='red', label='equal subproblem requests')

        ax.legend()
        ax.set_ylim(bottom=0)
        ax.set_title(f'Equal requests of config \'{config_name}\'\ngroup \'{config_name}\' instance \'{config_name}\'')
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Request number')

        save_path = result_directory.joinpath('plots')
        save_path.mkdir(exist_ok=True)

        fig.savefig(save_path.joinpath('equal_requests_between_iterations.png'))
        plt.close('all')