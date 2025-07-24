from src.common.custom_types import MasterInstance, FatMasterResult, SlimMasterResult
from src.common.custom_types import PatientName, FinalResult, OperatorName, CareUnitName

def analyze_master_result(instance: MasterInstance, result: FatMasterResult | SlimMasterResult | FinalResult) -> dict[str, int | float]:

    day_number = len(result.scheduled)

    scheduled_request_number_per_day = [len(results) for results in result.scheduled.values()]
    total_scheduled_request_number = sum(scheduled_request_number_per_day)

    scheduled_request_duration_per_day = [sum(instance.services[request.service_name].duration for request in requests) for requests in result.scheduled.values()]
    total_scheduled_request_duration = sum(scheduled_request_duration_per_day)

    patient_names = set(request.patient_name for requests in result.scheduled.values() for request in requests)
    patient_number = len(patient_names)

    patients_per_day = [len(set(request.patient_name for request in requests)) for requests in result.scheduled.values()]

    day_number_used_per_patient: list[int] = []
    for patient_name in patient_names:
        
        day_used = 0
        for requests in result.scheduled.values():
            if any(request.patient_name == patient_name for request in requests):
                day_used += 1
        
        day_number_used_per_patient.append(day_used)

    request_number_per_patient_same_day: list[int] = []
    request_duration_per_patient_same_day: list[int] = []
    care_unit_used_per_patient_same_day: list[int] = []

    for requests in result.scheduled.values():
        
        patient_request_numbers: dict[PatientName, int] = {}
        patient_request_total_durations: dict[PatientName, int] = {}
        patient_care_unit_used: dict[PatientName, set[CareUnitName]] = {}
        
        for request in requests:
            
            service_name = request.service_name
            patient_name = request.patient_name
            care_unit_name = instance.services[service_name].care_unit_name
            duration = instance.services[service_name].duration
            
            if patient_name not in patient_request_numbers:
                patient_request_numbers[patient_name] = 0
                patient_request_total_durations[patient_name] = 0
                patient_care_unit_used[patient_name] = set()
            
            patient_request_numbers[patient_name] += 1
            patient_request_total_durations[patient_name] += duration
            patient_care_unit_used[patient_name].add(care_unit_name)

        request_number_per_patient_same_day.extend(request_number for request_number in patient_request_numbers.values())
        request_duration_per_patient_same_day.extend(duration for duration in patient_request_total_durations.values())
        care_unit_used_per_patient_same_day.extend(len(care_unit_names) for care_unit_names in patient_care_unit_used.values())

    analysis = {
        'day_number': day_number,
        'patient_number': patient_number,

        'total_scheduled_request_number': total_scheduled_request_number,
        'total_scheduled_request_duration': total_scheduled_request_duration,
        
        'total_rejected_request_number': len(result.rejected),
        'total_rejected_request_duration': sum(instance.services[request.service_name].duration for request in result.rejected),
        
        'min_scheduled_request_number_per_day': min(scheduled_request_number_per_day),
        'max_scheduled_request_number_per_day': max(scheduled_request_number_per_day),
        'average_scheduled_request_number_per_day': total_scheduled_request_number / len(scheduled_request_number_per_day),
        
        'min_scheduled_request_duration_per_day': min(scheduled_request_duration_per_day),
        'max_scheduled_request_duration_per_day': max(scheduled_request_duration_per_day),
        'average_scheduled_request_duration_per_day': total_scheduled_request_duration / len(scheduled_request_duration_per_day),
        
        'min_patients_per_day': min(patients_per_day),
        'max_patients_per_day': max(patients_per_day),
        'average_patients_per_day': sum(patients_per_day) / len(patients_per_day),
        
        'min_day_number_used_per_patient': min(day_number_used_per_patient),
        'max_day_number_used_per_patient': max(day_number_used_per_patient),
        'average_day_number_used_per_patient': sum(day_number_used_per_patient) / len(day_number_used_per_patient),
        
        'min_request_number_per_patient_same_day': min(request_number_per_patient_same_day),
        'max_request_number_per_patient_same_day': max(request_number_per_patient_same_day),
        'average_request_number_per_patient_same_day': sum(request_number_per_patient_same_day) / len(request_number_per_patient_same_day),
        
        'min_request_duration_per_patient_same_day': min(request_duration_per_patient_same_day),
        'max_request_duration_per_patient_same_day': max(request_duration_per_patient_same_day),
        'average_request_duration_per_patient_same_day': sum(request_duration_per_patient_same_day) / len(request_duration_per_patient_same_day),
        
        'min_care_unit_used_per_patient_same_day': min(care_unit_used_per_patient_same_day),
        'max_care_unit_used_per_patient_same_day': max(care_unit_used_per_patient_same_day),
        'average_care_unit_used_per_patient_same_day': sum(care_unit_used_per_patient_same_day) / len(care_unit_used_per_patient_same_day)
    }

    if isinstance(result, SlimMasterResult):
        return analysis
        
    operator_used_per_patient: list[int] = []
    patient_served_per_operator: list[int] = []
    
    for requests in result.scheduled.values():
        
        operator_served: dict[PatientName, int] = {}
        patients_served: dict[OperatorName, int] = {}
        
        for request in requests:
            
            patient_name = request.patient_name
            if patient_name not in operator_served:
                operator_served[patient_name] = 0
            operator_served[patient_name] += 1
            
            operator_name = request.operator_name
            if operator_name not in patients_served:
                patients_served[operator_name] = 0
            patients_served[operator_name] += 1
        
        operator_used_per_patient.extend(operator_served.values())
        patient_served_per_operator.extend(patients_served.values())
            
    total_operator_used_per_patient = sum(operator_used_per_patient)
    total_patient_served_per_operator = sum(patient_served_per_operator)

    analysis.update({
        'total_operator_used_per_patient': total_operator_used_per_patient,
        'min_operator_used_per_patient': min(operator_used_per_patient),
        'max_operator_used_per_patient': max(operator_used_per_patient),
        'average_operator_used_per_patient': total_operator_used_per_patient / len(operator_used_per_patient),
        
        'total_patient_served_per_operator': total_patient_served_per_operator,
        'min_patient_served_per_operator': min(patient_served_per_operator),
        'max_patient_served_per_operator': max(patient_served_per_operator),
        'average_patient_served_per_operator': total_patient_served_per_operator / len(patient_served_per_operator)
    })

    return analysis