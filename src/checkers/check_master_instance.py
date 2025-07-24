from src.common.custom_types import MasterInstance

def check_master_instance(instance: MasterInstance) -> list[str]:

    errors: list[str] = []

    if len(instance.days) == 0:
        errors.append('instance has no days')
    if len(instance.services) == 0:
        errors.append('instance has no services')
    if len(instance.patients) == 0:
        errors.append('instance has no patients')
    
    day_names = set(instance.days.keys())
    min_day = min(day_names)
    max_day = max(day_names)

    if len(day_names) != max_day - min_day + 1:
        errors.append('instance days have gaps')

    care_unit_names = set()
    for day in instance.days.values():
        care_unit_names.update(day.care_units.keys())

    for day_name, day in instance.days.items():
        
        if len(day.care_units) == 0:
            errors.append(f'day {day_name} has no care units')
        
        for care_unit_name, care_unit in day.care_units.items():
        
            if len(care_unit) == 0:
                errors.append(f'care unit {care_unit_name} of day {day_name} has no operators')
        
            for operator_name, operator in care_unit.items():
                if operator.start < 0 or operator.duration <= 0:
                    errors.append(f'operator {operator_name} of care unit {care_unit_name} of day {day_name} has wrong parameters')

    for service_name, service in instance.services.items():
        if service.care_unit_name not in care_unit_names:
            errors.append(f'service {service_name} has a non existent care unit ({service.care_unit_name})')
        if service.duration <= 0:
            errors.append(f'service {service_name} has an invalid duration ({service.duration})')

    for patient_name, patient in instance.patients.items():
        
        if patient.priority <= 0:
            errors.append(f'priority of patient {patient_name} is invalid')
        
        if len(patient.requests) == 0:
            errors.append(f'patient {patient_name} has no requests')
        
        for service_name, windows in patient.requests.items():
            
            if service_name not in instance.services.keys():
                errors.append(f'patient {patient_name} requests a non existent service ({service_name})')
            if len(windows) == 0:
                errors.append(f'patient {patient_name} requests service {service_name} with no windows')
            
            for window in windows:
                if window.start < min_day or window.end > max_day or window.start > window.end:
                    errors.append(f'patient {patient_name} requests service {service_name} with invalid window [{window.start}, {window.end}]')

    return errors