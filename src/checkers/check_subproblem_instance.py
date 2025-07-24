from src.common.custom_types import FatSubproblemInstance, SlimSubproblemInstance
from src.common.custom_types import OperatorName, TimeSlot, PatientName, CareUnitName

def check_common_subproblem_parts(instance: FatSubproblemInstance | SlimSubproblemInstance) -> list[str]:

    errors: list[str] = []

    if len(instance.day.care_units) == 0:
        errors.append('instance has no care unit')
    if len(instance.services) == 0:
        errors.append('instance has no services')
    if len(instance.patients) == 0:
        errors.append('instance has no patients')

    for care_unit_name, care_unit in instance.day.care_units.items():
        
        if len(care_unit) == 0:
            errors.append(f'care unit {care_unit_name} has no operators')
    
        for operator_name, operator in care_unit.items():
            if operator.start < 0 or operator.duration <= 0:
                errors.append(f'operator {operator_name} of care unit {care_unit_name} has wrong parameters')

    for service_name, service in instance.services.items():
        if service.care_unit_name not in instance.day.care_units.keys():
            errors.append(f'service {service_name} has a non existent care unit ({service.care_unit_name})')
        if service.duration <= 0:
            errors.append(f'service {service_name} has an invalid duration ({service.duration})')

    return errors

def check_fat_subproblem_instance(instance: FatSubproblemInstance) -> list[str]:

    errors: list[str] = check_common_subproblem_parts(instance)

    for patient_name, patient in instance.patients.items():
        
        if patient.priority <= 0:
            errors.append(f'priority of patient {patient_name} is invalid')
        
        if len(patient.requests) == 0:
            errors.append(f'patient {patient_name} has no requests')
        
        for request in patient.requests:

            service_name = request.service_name
            operator_name = request.operator_name
            care_unit_name = instance.services[service_name].care_unit_name
            
            if service_name not in instance.services.keys():
                errors.append(f'patient {patient_name} requests a non existent service ({service_name})')
            if care_unit_name not in instance.day.care_units.keys():
                errors.append(f'patient {patient_name} request a non existent care unit ({care_unit_name})')
            if operator_name not in instance.day.care_units[care_unit_name]:
                errors.append(f'patient {patient_name} request a non existent operator ({operator_name})')

    operator_remaining_duration: dict[OperatorName, TimeSlot] = {}
    for operator_name, operator in instance.day.operators.items():
        operator_remaining_duration[operator_name] = operator.duration
    
    first_time_slot = min(o.start for o in instance.day.operators.values())
    last_time_slot = max(o.start + o.duration for o in instance.day.operators.values())
    max_time_slot_span = last_time_slot - first_time_slot

    patient_remaining_duration: dict[PatientName, TimeSlot] = {pat: max_time_slot_span for pat in instance.patients.keys()}

    for patient_name, patient in instance.patients.items():
        
        if len(set(patient.requests)) != len(patient.requests):
            errors.append(f'patient {patient_name} has some duplicate requests')

        for request in patient.requests:
            
            operator_name = request.operator_name
            service_duration = instance.services[request.service_name].duration
            
            patient_remaining_duration[patient_name] -= service_duration
            operator_remaining_duration[operator_name] -= service_duration

            if patient_remaining_duration[patient_name] < 0:
                errors.append(f'patient {patient_name} is overloaded')
            if operator_remaining_duration[operator_name] < 0:
                errors.append(f'operator {operator_name} is overloaded')

    return errors

def check_slim_subproblem_instance(instance: SlimSubproblemInstance) -> list[str]:

    errors: list[str] = check_common_subproblem_parts(instance)

    for patient_name, patient in instance.patients.items():
        
        if patient.priority <= 0:
            errors.append(f'priority of patient {patient_name} is invalid')
        
        if len(patient.requests) == 0:
            errors.append(f'patient {patient_name} has no requests')
        
        for service_name in patient.requests:

            care_unit_name = instance.services[service_name].care_unit_name
            
            if service_name not in instance.services.keys():
                errors.append(f'patient {patient_name} requests a non existent service ({service_name})')
            if care_unit_name not in instance.day.care_units.keys():
                errors.append(f'patient {patient_name} request a non existent care unit ({care_unit_name})')

    care_unit_remaining_duration: dict[CareUnitName, TimeSlot] = {}
    for care_unit_name, care_unit in instance.day.care_units.items():
        care_unit_remaining_duration[care_unit_name] = sum(o.duration for o in care_unit.values())
    
    first_time_slot = min(o.start for o in instance.day.operators.values())
    last_time_slot = max(o.start + o.duration for o in instance.day.operators.values())
    max_time_slot_span = last_time_slot - first_time_slot

    patient_remaining_duration: dict[PatientName, TimeSlot] = {pat: max_time_slot_span for pat in instance.patients.keys()}

    for patient_name, patient in instance.patients.items():

        if len(set(patient.requests)) != len(patient.requests):
            errors.append(f'patient {patient_name} has some duplicate requests')

        for service_name in patient.requests:
            
            care_unit_name = instance.services[service_name].care_unit_name
            service_duration = instance.services[service_name].duration
            
            patient_remaining_duration[patient_name] -= service_duration
            care_unit_remaining_duration[care_unit_name] -= service_duration

            if patient_remaining_duration[patient_name] < 0:
                errors.append(f'patient {patient_name} is overloaded')
            if care_unit_remaining_duration[care_unit_name] < 0:
                errors.append(f'care unit {care_unit_name} is overloaded')

    return errors