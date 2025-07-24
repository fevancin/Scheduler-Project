from src.analyzers.master_result_analyzer import analyze_master_result
from src.analyzers.tools import get_result_value
from src.common.custom_types import MasterInstance, FinalResult

def analyze_final_result(instance: MasterInstance, result: FinalResult) -> dict[str, int | float]:

    time_slots_remaining_per_day = []
    for day_name, requests in result.scheduled.items():
        total_time_slots = sum(operator.duration for care_unit in instance.days[day_name].care_units.values() for operator in care_unit.values())
        scheduled_time_slots = sum(instance.services[request.service_name].duration for request in requests)
        time_slots_remaining_per_day.append(total_time_slots - scheduled_time_slots)
    
    total_time_slots_remaining = sum(time_slots_remaining_per_day)

    analysis = analyze_master_result(instance, result)

    analysis.update({
        'objective_value': get_result_value(instance, result, [], None),
        'total_time_slots_remaining': total_time_slots_remaining,
        'min_time_slots_remaining_per_day': min(time_slots_remaining_per_day),
        'max_time_slots_remaining_per_day': max(time_slots_remaining_per_day),
        'average_time_slots_remaining_per_day': total_time_slots_remaining / len(time_slots_remaining_per_day)
    })

    return analysis