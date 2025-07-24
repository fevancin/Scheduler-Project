from src.common.custom_types import FatSubproblemInstance, SlimSubproblemInstance, OperatorName
from src.common.custom_types import FatSubproblemResult, SlimSubproblemResult, PatientName

def analyze_subproblem_result(
        instance: FatSubproblemInstance | SlimSubproblemInstance,
        result: FatSubproblemResult | SlimSubproblemResult) -> dict[str, int | float]:
    
    total_scheduled_request_number = len(result.scheduled)

    scheduled_request_duration = [instance.services[request.service_name].duration for request in result.scheduled]
    total_scheduled_request_duration = sum(scheduled_request_duration)

    patient_names = set(request.patient_name for request in result.scheduled)
    patient_number = len(patient_names)

    care_units_used_per_patient = [len(set(instance.services[request.service_name].care_unit_name for request in result.scheduled if request.patient_name == patient_name)) for patient_name in patient_names]

    request_number_per_patient: list[int] = [len([request for request in result.scheduled if request.patient_name == patient_name]) for patient_name in patient_names]
    request_duration_per_patient: list[int] = [sum(instance.services[request.service_name].duration for request in result.scheduled if request.patient_name == patient_name) for patient_name in patient_names]

    operator_used_per_patient: dict[PatientName, int] = {}
    patient_served_per_operator: dict[OperatorName, int] = {}
    
    for request in result.scheduled:
        
        patient_name = request.patient_name
        if patient_name not in operator_used_per_patient:
            operator_used_per_patient[patient_name] = 0
        operator_used_per_patient[patient_name] += 1
        
        operator_name = request.operator_name
        if operator_name not in patient_served_per_operator:
            patient_served_per_operator[operator_name] = 0
        patient_served_per_operator[operator_name] += 1

    return {
        'patient_number': patient_number,

        'total_scheduled_request_number': total_scheduled_request_number,
        'total_scheduled_request_duration': total_scheduled_request_duration,
        
        'rejected_request_number': len(result.rejected),
        'rejected_request_duration': sum(instance.services[request.service_name].duration for request in result.rejected),
        
        'min_care_units_used_per_patient': min(care_units_used_per_patient),
        'max_care_units_used_per_patient': max(care_units_used_per_patient),
        'average_care_units_used_per_patient': sum(care_units_used_per_patient) / len(care_units_used_per_patient),
        
        'min_scheduled_request_duration': min(scheduled_request_duration),
        'max_scheduled_request_duration': max(scheduled_request_duration),
        'average_scheduled_request_duration': total_scheduled_request_duration / len(scheduled_request_duration),
        
        'min_request_number_per_patient': min(request_number_per_patient),
        'max_request_number_per_patient': max(request_number_per_patient),
        'average_request_number_per_patient': sum(request_number_per_patient) / len(request_number_per_patient),
        
        'min_request_duration_per_patient': min(request_duration_per_patient),
        'max_request_duration_per_patient': max(request_duration_per_patient),
        'average_request_duration_per_patient': sum(request_duration_per_patient) / len(request_duration_per_patient),
    
        'min_operator_used_per_patient': min(operator_used_per_patient.values()),
        'max_operator_used_per_patient': max(operator_used_per_patient.values()),
        'average_operator_used_per_patient': sum(operator_used_per_patient.values()) / len(operator_used_per_patient),
        
        'min_patient_served_per_operator': min(patient_served_per_operator.values()),
        'max_patient_served_per_operator': max(patient_served_per_operator.values()),
        'average_patient_served_per_operator': sum(patient_served_per_operator.values()) / len(patient_served_per_operator)
    }