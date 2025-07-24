from pathlib import Path

from src.common.custom_types import MasterInstance, FatMasterResult, SlimMasterResult, FinalResult
from src.common.custom_types import PatientName, DayName

def analyze_log(log_path: Path) -> dict[str, int | float | str]:

    analysis: dict[str, int | float | str] = {}

    last_h_line: str | None = None

    with open(log_path, 'r') as file:
        for line in file:
            
            if line.startswith('Optimal solution found'):
                analysis['status'] = 'optimal'
            if line.startswith('Time limit reached'):
                analysis['status'] = 'time_limit'
            
            if line.startswith('Best objective'):
                tokens = line.split()
                analysis['objective_value'] = float(tokens[2][:-1])
                analysis['upper_bound'] = float(tokens[5][:-1])
                analysis['gap'] = float(tokens[-1][:-1])

            if line.startswith('Root relaxation'):
                tokens = line.split()
                analysis['root_relaxation'] = float(tokens[3][:-1])
            
            if line.startswith('Explored'):
                tokens = line.split()
                analysis['time'] = float(tokens[7])
            
            if line.startswith('Optimize a model with'):
                tokens = line.split()
                analysis['constraint_number'] = int(tokens[4])
                analysis['variable_number'] = int(tokens[6])
            
            if line.startswith('Presolved'):
                tokens = line.split()
                analysis['presolved_constraint_number'] = int(tokens[1])
                analysis['presolved_variable_number'] = int(tokens[3])

            if line.startswith('H') or line.startswith('*'):
                last_h_line = line
    
    if last_h_line is not None:
        tokens = last_h_line.split()
        analysis['best_solution_time'] = float(tokens[-1][:-1])

    return analysis

def get_days_number_used_by_patients(result: FatMasterResult | SlimMasterResult | FinalResult) -> int:

    day_used_by_patient: dict[PatientName, set[DayName]] = {}
    for day_name, requests in result.scheduled.items():
        for request in requests:
            if request.patient_name not in day_used_by_patient:
                day_used_by_patient[request.patient_name] = set()
            day_used_by_patient[request.patient_name].add(day_name)
    
    return sum(len(day_names) for day_names in day_used_by_patient.values())

def get_result_value(
        instance: MasterInstance,
        result: FatMasterResult | SlimMasterResult | FinalResult,
        additional_info: list[str],
        worst_case_day_number: int | None) -> float:

    value = 0
    for patient_name, patient in instance.patients.items():
        for service_name, windows in patient.requests.items():
            for window in windows:
                
                is_window_satisfied = False
                
                for day_index in range(window.start, window.end + 1):
                    for request in result.scheduled[day_index]:
                        if patient_name == request.patient_name and service_name == request.service_name:
                            is_window_satisfied = True
                            break
                    if is_window_satisfied:
                        break

                if is_window_satisfied:
                    value += instance.services[service_name].duration * instance.patients[patient_name].priority

    if 'minimize_hospital_accesses' in additional_info and worst_case_day_number is not None:
        value -= get_days_number_used_by_patients(result) / worst_case_day_number

    return value