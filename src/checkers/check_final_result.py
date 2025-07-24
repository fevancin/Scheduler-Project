from src.common.custom_types import MasterInstance, FinalResult
from src.checkers.check_master_result import check_fat_master_result
from src.checkers.check_subproblem_result import check_overlaps

def check_final_result(instance: MasterInstance, result: FinalResult) -> list[str]:

    errors: list[str] = check_fat_master_result(instance, result)

    for day_name, requests in result.scheduled.items():

        daily_errors = check_overlaps(instance, requests)
        for error in daily_errors:
            errors.append(f'[day {day_name}]: {error}')

        for request in requests:

            patient_name = request.patient_name
            service_name = request.service_name
            operator_name = request.operator_name
            time_slot = request.time_slot
            
            care_unit_name = instance.services[service_name].care_unit_name
            service_duration = instance.services[service_name].duration
            operator = instance.days[day_name].care_units[care_unit_name][operator_name]
            if time_slot < operator.start or time_slot + service_duration > operator.end:
                errors.append(f'service {service_name} of patient {patient_name} doen not respect operator {operator_name} time of activity')

    return errors