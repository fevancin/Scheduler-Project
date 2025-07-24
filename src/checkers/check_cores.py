from src.common.custom_types import MasterInstance, FatCore, SlimCore, PatientServiceOperator

def check_cores(instance: MasterInstance, cores: list[FatCore] | list[SlimCore]) -> list[str]:

    errors: list[str] = []
    
    for core in cores:
        
        if len(core.reason) == 0:
            errors.append('a core has no reason')
        if len(core.days) == 0:
            errors.append('a core has no days')
        if len(core.components) == 0:
            errors.append('a core has no components')
        
        for day_name in core.days:
            if day_name not in instance.days:
                errors.append(f'day {day_name} is not present in the instance')
        
        for reason in core.reason:

            reason_found = False
            
            for component in core.components:
                if component.patient_name == reason.patient_name and component.service_name == reason.service_name:
                    if isinstance(component, PatientServiceOperator):
                        if component.operator_name == reason.operator_name: # type: ignore
                            reason_found = True
                            break
                    else:
                        reason_found = True
                        break
            
            if not reason_found:
                if isinstance(reason, PatientServiceOperator):
                    errors.append(f'reason {reason.patient_name}, {reason.service_name}, {reason.operator_name} not found in core components')
                else:
                    errors.append(f'reason {reason.patient_name}, {reason.service_name} not found in core components')


        for component in core.components:
            
            patient_name = component.patient_name
            service_name = component.service_name
            
            if patient_name not in instance.patients:
                errors.append(f'patient {patient_name} does not exists')
            if service_name not in instance.services:
                errors.append(f'service {service_name} does not exists')
            
            if service_name not in instance.patients[patient_name].requests:
                errors.append(f'service {service_name} is not requested by patient {patient_name}')
            
            for day_name in core.days:
                
                if isinstance(component, PatientServiceOperator):
                    operator_name = component.operator_name
                    if operator_name not in instance.days[day_name].operators:
                        errors.append(f'operator {operator_name} does not exists in day {day_name}')
                
                window_found = False
                for window in instance.patients[patient_name].requests[service_name]:
                    if window.start <= day_name and window.end >= day_name:
                        window_found = True
                        break
                if not window_found:
                    errors.append(f'patient {patient_name} has no window for service {service_name} in day {day_name}')

    return errors