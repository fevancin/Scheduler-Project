from src.common.custom_types import FatSubproblemInstance, SlimSubproblemInstance

def analyze_subproblem_instance(instance: FatSubproblemInstance | SlimSubproblemInstance) -> dict[str, int | float]:

    care_unit_number = len(instance.care_units)
    care_unit_durations = [sum(operator.duration for operator in care_unit.values()) for care_unit in instance.care_units.values()]

    operator_total_number = sum(len(care_unit) for care_unit in instance.care_units.values())
    operator_durations = [operator.duration for care_unit in instance.care_units.values() for operator in care_unit.values()]
    operator_total_duration = sum(operator_durations)

    service_durations = [service.duration for service in instance.services.values()]
    
    if isinstance(instance, FatSubproblemInstance):
        total_time_slots_requested = sum(instance.services[request.service_name].duration for patient in instance.patients.values() for request in patient.requests)
    else:
        total_time_slots_requested = sum(instance.services[service_name].duration for patient in instance.patients.values() for service_name in patient.requests)
    
    patient_number = len(instance.patients)
    patient_request_numbers = [len(patient.requests) for patient in instance.patients.values()]

    if isinstance(instance, FatSubproblemInstance):
        care_units_used_per_patient = [len(set(instance.services[request.service_name].care_unit_name for request in patient.requests)) for patient in instance.patients.values()]
    else:
        care_units_used_per_patient = [len(set(instance.services[service_name].care_unit_name for service_name in patient.requests)) for patient in instance.patients.values()]

    return {
        'care_unit_number': care_unit_number,
        'operator_total_number': operator_total_number,
        'patient_number': patient_number,
        'total_request_number': sum(patient_request_numbers),
        
        'min_care_unit_duration': min(care_unit_durations),
        'max_care_unit_duration': max(care_unit_durations),
        'average_care_unit_duration': sum(care_unit_durations) / care_unit_number,
        
        'min_operator_duration': min(operator_durations),
        'max_operator_duration': max(operator_durations),
        'average_operator_duration': operator_total_duration / operator_total_number,
        
        'min_service_duration': min(service_durations),
        'max_service_duration': max(service_durations),
        'average_service_duration': sum(service_durations) / len(instance.services),
        
        'operator_total_duration': operator_total_duration,
        'total_time_slots_requested': total_time_slots_requested,
        'request_over_disponibility_ratio': total_time_slots_requested / operator_total_duration,
        
        'min_patient_request_number': min(patient_request_numbers),
        'max_patient_request_number': max(patient_request_numbers),
        'average_patient_request_number': sum(patient_request_numbers) / patient_number,
        
        'min_care_units_used_per_patient': min(care_units_used_per_patient),
        'max_care_units_used_per_patient': max(care_units_used_per_patient),
        'average_care_units_used_per_patient': sum(care_units_used_per_patient) / patient_number
    }