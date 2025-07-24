from src.common.custom_types import MasterInstance, FatMasterResult, SlimMasterResult, FinalResult
from src.common.custom_types import TimeSlot, PatientName, OperatorName, PatientServiceWindow, CareUnitName

def check_rejected_requests(instance: MasterInstance, result: FatMasterResult | SlimMasterResult | FinalResult) -> list[str]:

    errors: list[str] = []

    for request in result.rejected:

        patient_name = request.patient_name
        service_name = request.service_name

        if patient_name not in instance.patients.keys():
            errors.append(f'rejected patient {patient_name} does not exists')
        if service_name not in instance.services.keys():
            errors.append(f'rejected service {service_name} does not exists')

    return errors

def check_windows_respect(instance: MasterInstance, result: FatMasterResult | SlimMasterResult | FinalResult) -> list[str]:

    errors: list[str] = []

    all_instance_requests: list[PatientServiceWindow] = list()
    for patient_name, patient in instance.patients.items():
        for service_name, windows in patient.requests.items():
            for window in windows:
                all_instance_requests.append(PatientServiceWindow(patient_name, service_name, window))

    for request in result.rejected:
        if request not in all_instance_requests:
            errors.append(f'rejected request ({request.patient_name}, {request.service_name}, {request.window}) is not present in the instance (or duplicated)')
        else:
            while request in all_instance_requests:
                all_instance_requests.remove(request)

    for day_name, scheduled_requests in result.scheduled.items():
        for scheduled_request in scheduled_requests:
            
            instance_requests_containing_day_name = []
            
            for instance_request in all_instance_requests:
                if instance_request.patient_name != scheduled_request.patient_name or instance_request.service_name != scheduled_request.service_name:
                    continue
                if instance_request.window.start <= day_name and instance_request.window.end >= day_name:
                    instance_requests_containing_day_name.append(instance_request)
            
            if len(instance_requests_containing_day_name) == 0:
                errors.append(f'request {scheduled_request} is not requested by anyone in the instance (or already requested in the same window)')
            
            for instance_request in instance_requests_containing_day_name:
                while instance_request in all_instance_requests:
                    all_instance_requests.remove(instance_request)

    if len(all_instance_requests) != 0:
        errors.append(f'{len(all_instance_requests)} requests are not in the result (first is {all_instance_requests.pop()})')

    return errors

def check_fat_master_result(instance: MasterInstance, result: FatMasterResult | FinalResult) -> list[str]:

    errors: list[str] = []

    for day_name, requests in result.scheduled.items():
        
        for request in requests:

            patient_name = request.patient_name
            service_name = request.service_name
            operator_name = request.operator_name
            
            if patient_name not in instance.patients.keys():
                errors.append(f'patient {patient_name} in day {day_name} does not exists')
            if service_name not in instance.services.keys():
                errors.append(f'service {service_name} in day {day_name} does not exists')
            
            care_unit_name = instance.services[service_name].care_unit_name
            if care_unit_name not in instance.days[day_name].care_units.keys():
                errors.append(f'care unit {care_unit_name} in day {day_name} does not exists')
            if operator_name not in instance.days[day_name].care_units[care_unit_name]:
                errors.append(f'operator {operator_name} in day {day_name} does not exists')
    
    errors.extend(check_rejected_requests(instance, result))

    for day_name, requests in result.scheduled.items():

        day = instance.days[day_name]
        
        patient_remaining_duration: dict[PatientName, TimeSlot] = {}

        operator_remaining_duration: dict[OperatorName, TimeSlot] = {}
        for operator_name, operator in day.operators.items():
            operator_remaining_duration[operator_name] = operator.duration
        
        first_time_slot = min(o.start for o in day.operators.values())
        last_time_slot = max(o.start + o.duration for o in day.operators.values())
        max_time_slot_span = last_time_slot - first_time_slot
        
        for request in requests:
            
            patient_name = request.patient_name
            service_duration = instance.services[request.service_name].duration
            operator_name = request.operator_name
            
            if patient_name not in patient_remaining_duration:
                patient_remaining_duration[patient_name] = max_time_slot_span
            
            patient_remaining_duration[patient_name] -= service_duration
            operator_remaining_duration[operator_name] -= service_duration

            if patient_remaining_duration[patient_name] < 0:
                errors.append(f'patient {patient_name} is overloaded in day {day_name}')
            if operator_remaining_duration[operator_name] < 0:
                errors.append(f'operator {operator_name} is overloaded in day {day_name}')

    errors.extend(check_windows_respect(instance, result))

    return errors


def check_slim_master_result(instance: MasterInstance, result: SlimMasterResult) -> list[str]:

    errors: list[str] = []

    for day_name, requests in result.scheduled.items():
        
        if len(requests) == 0:
            errors.append(f'day {day_name} has no requests')
        
        for request in requests:

            patient_name = request.patient_name
            service_name = request.service_name
            
            if patient_name not in instance.patients.keys():
                errors.append(f'patient {patient_name} in day {day_name} does not exists')
            if service_name not in instance.services.keys():
                errors.append(f'service {service_name} in day {day_name} does not exists')
            
            care_unit_name = instance.services[service_name].care_unit_name
            
            if care_unit_name not in instance.days[day_name].care_units.keys():
                errors.append(f'care unit {care_unit_name} in day {day_name} does not exists')
    
    errors.extend(check_rejected_requests(instance, result))

    for day_name, requests in result.scheduled.items():

        day = instance.days[day_name]
        
        patient_remaining_duration: dict[PatientName, TimeSlot] = {}

        care_unit_remaining_duration: dict[CareUnitName, TimeSlot] = {}
        for care_unit_name, care_unit in day.care_units.items():
            care_unit_remaining_duration[care_unit_name] = sum(o.duration for o in care_unit.values())
        
        first_time_slot = min(o.start for o in day.operators.values())
        last_time_slot = max(o.start + o.duration for o in day.operators.values())
        max_time_slot_span = last_time_slot - first_time_slot
        
        for request in requests:
            
            patient_name = request.patient_name
            service_duration = instance.services[request.service_name].duration
            care_unit_name = instance.services[request.service_name].care_unit_name
            
            if patient_name not in patient_remaining_duration:
                patient_remaining_duration[patient_name] = max_time_slot_span
            
            patient_remaining_duration[patient_name] -= service_duration
            care_unit_remaining_duration[care_unit_name] -= service_duration

            if patient_remaining_duration[patient_name] < 0:
                errors.append(f'patient {patient_name} is overloaded in day {day_name}')
            if care_unit_remaining_duration[care_unit_name] < 0:
                errors.append(f'care unit {care_unit_name} is overloaded in day {day_name}')

    errors.extend(check_windows_respect(instance, result))

    return errors