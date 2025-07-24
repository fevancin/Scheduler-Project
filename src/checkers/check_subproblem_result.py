from src.common.custom_types import FatSubproblemInstance, SlimSubproblemInstance, FatSubproblemResult, SlimSubproblemResult
from src.common.custom_types import PatientServiceOperatorTimeSlot, MasterInstance

def check_overlaps(instance: MasterInstance | FatSubproblemInstance | SlimSubproblemInstance, requests: list[PatientServiceOperatorTimeSlot]) -> list[str]:
    
    errors: list[str] = []
    
    for i in range(len(requests) - 1):
        
        request = requests[i]
        service_duration = instance.services[request.service_name].duration
        
        for j in range(i + 1, len(requests)):
        
            other_request = requests[j]
            other_service_duration = instance.services[other_request.service_name].duration

            same_patient = (request.patient_name == other_request.patient_name)
            same_service = (request.service_name == other_request.service_name)

            if same_patient and same_service:
                errors.append(f'patient {request.patient_name} requests service {request.service_name} multiple times')

            same_operator = (request.operator_name == other_request.service_name)
            if same_patient or same_operator:
                if ((request.time_slot <= other_request.time_slot and request.time_slot + service_duration > other_request.time_slot) or
                    (other_request.time_slot <= request.time_slot and other_request.time_slot + other_service_duration > request.time_slot)):
                    errors.append(f'requests {request} and {other_request} overlap in time')

    return errors

def check_subproblem_result(instance: FatSubproblemInstance | SlimSubproblemInstance, result: FatSubproblemResult | SlimSubproblemResult) -> list[str]:

    errors: list[str] = []

    for request in result.scheduled:

        patient_name = request.patient_name
        service_name = request.service_name
        operator_name = request.operator_name
        time_slot = request.time_slot
        
        if patient_name not in instance.patients.keys():
            errors.append(f'patient {patient_name} does not exists')
        if service_name not in instance.services.keys():
            errors.append(f'service {service_name} does not exists')

        care_unit_name = instance.services[service_name].care_unit_name
        if care_unit_name not in instance.day.care_units.keys():
            errors.append(f'care unit {care_unit_name} does not exists')
        if operator_name not in instance.day.care_units[care_unit_name]:
            errors.append(f'operator {operator_name} does not exists')
        
        service_duration = instance.services[service_name].duration
        operator = instance.day.care_units[care_unit_name][operator_name]
        if time_slot < operator.start or time_slot + service_duration > operator.end:
            errors.append(f'service {service_name} of patient {patient_name} doen not respect operator {operator_name} time of activity')

    if isinstance(instance, FatSubproblemInstance):
        for patient_name, patient in instance.patients.items():
            for request in patient.requests:
                service_name = request.service_name
                request_found = False
                for rejected_request in result.rejected:
                    if patient_name == rejected_request.patient_name and service_name == rejected_request.service_name:
                        request_found = True
                        break
                if not request_found:
                    for scheduled_request in result.scheduled:
                        if patient_name == scheduled_request.patient_name and service_name == scheduled_request.service_name:
                            request_found = True
                            break
                if not request_found:
                    errors.append(f'patient {patient_name} do not have service {service_name} in the result')
    else:
        for patient_name, patient in instance.patients.items():
            for service_name in patient.requests:
                request_found = False
                for rejected_request in result.rejected:
                    if patient_name == rejected_request.patient_name and service_name == rejected_request.service_name:
                        request_found = True
                        break
                if not request_found:
                    for scheduled_request in result.scheduled:
                        if patient_name == scheduled_request.patient_name and service_name == scheduled_request.service_name:
                            request_found = True
                            break
                if not request_found:
                    errors.append(f'patient {patient_name} do not have service {service_name} in the result')

    for request in result.rejected:

        patient_name = request.patient_name
        service_name = request.service_name

        if patient_name not in instance.patients.keys():
            errors.append(f'rejected patient {patient_name} does not exists')
        if service_name not in instance.services.keys():
            errors.append(f'rejected service {service_name} does not exists')
        
        for scheduled_request in result.scheduled:
            if patient_name == scheduled_request.patient_name and service_name == scheduled_request.service_name:
                errors.append(f'patient {patient_name} has service {service_name} both satisfied and rejected')

    errors.extend(check_overlaps(instance, result.scheduled))

    return errors