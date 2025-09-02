import json

from src.common.custom_types import MasterInstance, FatMasterResult, SlimMasterResult
from src.common.custom_types import FatSubproblemInstance, SlimSubproblemInstance
from src.common.custom_types import FatSubproblemResult, SlimSubproblemResult, PatientServiceWindow
from src.common.custom_types import FinalResult, FatCore, SlimCore, CacheMatch
from src.common.custom_types import FatSubproblemPatient, SlimSubproblemPatient
from src.common.custom_types import PatientServiceOperator, Service, ServiceOperator
from src.common.custom_types import MasterPatient, Window, Day, Operator, PatientService
from src.common.custom_types import ServiceName, PatientName, OperatorName, CareUnitName, DayName
from src.common.custom_types import PatientServiceOperatorTimeSlot


MASTER_INSTANCE = 0
FAT_MASTER_RESULT = 1
SLIM_MASTER_RESULT = 2
FAT_SUBPROBLEM_INSTANCE = 3
SLIM_SUBPROBLEM_INSTANCE = 4
FAT_SUBPROBLEM_RESULT = 5
SLIM_SUBPROBLEM_RESULT = 6
FINAL_RESULT = 7
FAT_CORES = 8
SLIM_CORES = 9


MASTER_INSTANCE_DAYS_ALL_EQUAL = 1
MASTER_INSTANCE_DAYS_NOT_EQUAL = 2


def write_binary_file(b: list[int], file_name: str):

    # Inserisci all'inizio il numero di byte del file (int_16)
    b_len = len(b)
    b.insert(0, b_len & 0xff)
    b.insert(0, (b_len >> 8) & 0xff)

    with open(file_name, 'wb') as file:
        file.write(bytearray(b))


def read_binary_file(file_name: str):

    with open(file_name, 'rb') as file:
        b = bytearray(file.read())
    
    return b


def reverse_code(code) -> dict[int, str]:

    reverse_code: dict[int, str] = {}

    for key, value in code.items():
        reverse_code[value] = key
    
    return reverse_code


def are_days_all_equal(days: dict[DayName, Day]) -> bool:

    day_to_compare = None
    
    for day in days.values():
        
        if day_to_compare is None:
            day_to_compare = day
            continue

        if len(day.care_units) != len(day_to_compare.care_units):
            return False
        
        for care_unit_name, care_unit in day.care_units.items():
            
            if care_unit_name not in day_to_compare.care_units:
                return False
            
            care_unit_to_compare = day_to_compare.care_units[care_unit_name]
            if len(care_unit) != len(care_unit_to_compare):
                return False
            
            for operator_name, operator in care_unit.items():
            
                if operator_name not in care_unit_to_compare:
                    return False
                operator_to_compare = care_unit_to_compare[operator_name]
            
                if operator.start != operator_to_compare.start or operator.duration != operator_to_compare.duration:
                    return False
        
    return True
            

def compress_services(b: list[int], services: dict[ServiceName, Service], codes: dict):

    b.append(len(services))
    for service_name, service in services.items():
        
        care_unit_name = service.care_unit_name
        duration = service.duration
        
        # Aggiunta ai codici dei servizi, se non ancora presente
        if service_name not in codes['services']:
            codes['services'][service_name] = len(codes['services'])

        # Aggiunta ai codici dell'unità di cura, se non ancora presente
        if care_unit_name not in codes['care_units']:
            codes['care_units'][care_unit_name] = len(codes['care_units'])

        b.append(codes['services'][service_name])
        b.append(codes['care_units'][service.care_unit_name])
        b.append(duration)


def compress_day(day: Day, day_name: DayName | None, b: list[int], codes: dict):
    
    operator_code = 0

    # Scrittura delle unità di cura
    b.append(len(day.care_units))
    for care_unit_name, care_unit in day.care_units.items():

        # Aggiunta ai codici dell'unità di cura, se non ancora presente
        if care_unit_name not in codes['care_units']:
            codes['care_units'][care_unit_name] = len(codes['care_units'])

        b.append(codes['care_units'][care_unit_name])
        
        # Scrittura degli operatori
        b.append(len(care_unit))
        for operator_name, operator in care_unit.items():

            if day_name is None:
                key = operator_name
            else:
                key = f'{day_name}__{operator_name}'
            
            codes['operators'][key] = operator_code
            operator_code += 1

            b.append(codes['operators'][key])
            b.append(operator.start)
            b.append(operator.end)


def compress_master_instance(instance: MasterInstance, file_name: str):

    # Dizionari che permettono di risalire ai nomi delle entità dai loro codici
    codes: dict[str, dict[str | int, int]] = {
        'days': {},
        'care_units': {},
        'operators': {},
        'services': {},
        'patients': {}
    }
    
    # Lista di byte
    b = []

    # Primo byte che identifica il tipo di file
    b.append(MASTER_INSTANCE)

    # Scrittura dei servizi
    compress_services(b, instance.services, codes)
    
    # Scrittura dei pazienti
    b.append(len(instance.patients))
    for patient_name, patient in instance.patients.items():

        codes['patients'][patient_name] = len(codes['patients'])

        b.append(codes['patients'][patient_name])
        b.append(patient.priority)

        # Scrittura del numero totale di finestre richieste (int_16)
        request_number = sum(len(windows) for windows in patient.requests.values())
        b.append(request_number & 0xff)
        b.append((request_number >> 8) & 0xff)

        # Scrittura delle finestre
        for service_name, windows in patient.requests.items():
            for window in windows:
                b.append(codes['services'][service_name])
                b.append(window.start)
                b.append(window.end)
    
    # Scrittura dei giorni
    b.append(len(instance.days))
    if are_days_all_equal(instance.days):
        b.append(MASTER_INSTANCE_DAYS_ALL_EQUAL)
        
        for day_name, day in instance.days.items():
            codes['days'][day_name] = len(codes['days'])
        
        day = next(iter(instance.days.values()))
        compress_day(day, None, b, codes)
    
    else:
        b.append(MASTER_INSTANCE_DAYS_NOT_EQUAL)

        for day_name, day in instance.days.items():
            
            codes['days'][day_name] = len(codes['days'])
            b.append(codes['days'][day_name])

            compress_day(day, day_name, b, codes)
    
    write_binary_file(b, file_name)
    
    with open('codes.json', 'w') as file:
        json.dump(codes, file, indent=4)


def decompress_day(b: bytearray, cursor: int, day_name: DayName | None, reverse_codes: dict) -> tuple[Day, int]:

    care_unit_number = b[cursor]
    cursor += 1

    day = Day()

    for _ in range(care_unit_number):

        care_unit_name = reverse_codes['care_units'][b[cursor]]
        operator_number = b[cursor + 1]
        cursor += 2

        for _ in range(operator_number):

            if day_name is None:
                operator_name = reverse_codes['operators'][b[cursor]]
            else:
                operator_name = reverse_codes['operators'][day_name][b[cursor]]

            start_time_slot = b[cursor + 1]
            end_time_slot = b[cursor + 2]
            cursor += 3

            operator = Operator(care_unit_name, start_time_slot, end_time_slot)

            day.add_operator(operator_name, operator)
    
    return day, cursor

def get_reverse_codes(codes: dict) -> dict:

    reverse_codes = {
        'patients': reverse_code(codes['patients']),
        'services': reverse_code(codes['services']),
        'days': reverse_code(codes['days']),
        'care_units': reverse_code(codes['care_units']),
        'operators': {}
    }
    
    for key, operator_code in codes['operators'].items():
        if '__' in key:
            day_name, operator_name = key.split('__')
            if day_name not in reverse_codes['operators']:
                reverse_codes['operators'][day_name] = {}
            reverse_codes['operators'][day_name][operator_code] = operator_name
        else:
            operator_name = key
            reverse_codes['operators'][operator_code] = operator_name
    
    return reverse_codes


def decompress_master_instance(file_name: str, codes: dict) -> MasterInstance | None:

    b = read_binary_file(file_name)

    cursor = 2
    if b[cursor] != MASTER_INSTANCE:
        return None
    cursor += 1
    
    reverse_codes = get_reverse_codes(codes)
    
    services: dict[ServiceName, Service] = {}
    service_number = b[cursor]
    cursor += 1

    for _ in range(service_number):

        service_name = reverse_codes['services'][b[cursor]]
        care_unit_name = reverse_codes['care_units'][b[cursor + 1]]
        duration = b[cursor + 2]
        cursor += 3

        services[service_name] = Service(care_unit_name, duration)
    
    patients: dict[PatientName, MasterPatient] = {}
    patient_number = b[cursor]
    cursor += 1

    for _ in range(patient_number):

        patient_name = reverse_codes['patients'][b[cursor]]
        patient_priority = b[cursor + 1]
        request_number = b[cursor + 2]
        request_number |= (b[cursor + 3] >> 8)
        cursor += 4

        patient = MasterPatient(priority=patient_priority)

        for _ in range(request_number):
            
            service_name = reverse_codes['services'][b[cursor]]
            window_start = b[cursor + 1]
            window_end = b[cursor + 2]
            cursor += 3

            if service_name not in patient.requests:
                patient.requests[service_name] = []
            patient.requests[service_name].append(Window(window_start, window_end))

        patients[patient_name] = patient

    days: dict[DayName, Day] = {}
    day_number = b[cursor]
    compression_type = b[cursor + 1]
    cursor += 2

    if compression_type == MASTER_INSTANCE_DAYS_ALL_EQUAL:
        
        day_to_clone, cursor = decompress_day(b, cursor, None, reverse_codes)
        for day_name in reverse_codes['days'].values():
            days[day_name] = day_to_clone
    
    else:

        for _ in range(day_number):

            day_name = reverse_codes['days'][b[cursor]]
            cursor += 1

            day, cursor = decompress_day(b, cursor, day_name, reverse_codes)
            days[day_name] = day

    return MasterInstance(days, services, patients)        


def compress_master_result(result: FatMasterResult | SlimMasterResult, file_name: str, codes: dict):
    
    # Lista di byte
    b = []

    # Primo byte che identifica il tipo di file
    if isinstance(result, FatMasterResult):
        b.append(FAT_MASTER_RESULT)
    else:
        b.append(SLIM_MASTER_RESULT)

    # Scrittura delle richieste di ogni giorno
    b.append(len(result.scheduled))
    for day_name, requests in result.scheduled.items():

        b.append(codes['days'][day_name])

        b.append(len(requests))
        for request in requests:
            b.append(codes['patients'][request.patient_name])
            b.append(codes['services'][request.service_name])

            if isinstance(request, PatientServiceOperator):
                b.append(codes['operators'][f'{day_name}__{request.operator_name}'])
    
    # Scrittura delle finestre rifiutate
    rejected_request_number = len(result.rejected)
    b.append(rejected_request_number & 0xff)
    b.append((rejected_request_number >> 8) & 0xff)
    
    for request in result.rejected:

        b.append(codes['patients'][request.patient_name])
        b.append(codes['services'][request.service_name])
        b.append(request.window.start)
        b.append(request.window.end)
    
    write_binary_file(b, file_name)


def decompress_master_result(file_name: str, codes: dict) -> FatMasterResult | SlimMasterResult | None:

    b = read_binary_file(file_name)

    cursor = 2
    if b[cursor] == FAT_MASTER_RESULT:
        result = FatMasterResult()
    elif b[cursor] == SLIM_MASTER_RESULT:
        result = SlimMasterResult()
    else:
        return None
    cursor += 1
    
    reverse_codes = get_reverse_codes(codes)

    day_number = b[cursor]
    cursor += 1

    for _ in range(day_number):

        day_name = reverse_codes['days'][b[cursor]]
        request_number = b[cursor + 1]
        cursor += 2

        result.scheduled[day_name] = []

        for _ in range(request_number):

            patient_name = reverse_codes['patients'][b[cursor]]
            service_name = reverse_codes['services'][b[cursor + 1]]
            cursor += 2

            if isinstance(result, FatMasterResult):
                
                operator_name = reverse_codes['operators'][b[cursor + 2]]
                cursor += 1
                
                request = PatientServiceOperator(patient_name, service_name, operator_name)
            
            else:
                request = PatientService(patient_name, service_name)
            
            result.scheduled[day_name].append(request) # type: ignore

    request_number = b[cursor] | (b[cursor + 1] << 8)
    cursor += 2

    for _ in range(request_number):
        
        patient_name = reverse_codes['patients'][b[cursor]]
        service_name = reverse_codes['services'][b[cursor + 1]]
        window_start = b[cursor + 2]
        window_end = b[cursor + 3]
        cursor += 4

        result.rejected.append(PatientServiceWindow(patient_name, service_name, Window(window_start, window_end)))
        
    return result


def compress_subproblem_instance(instance: FatSubproblemInstance | SlimSubproblemInstance, day_name: DayName | None, file_name: str, codes: dict):

    # Lista di byte
    b = []

    # Primo byte che identifica il tipo di file
    if isinstance(instance, FatSubproblemInstance):
        b.append(FAT_SUBPROBLEM_INSTANCE)
    else:
        b.append(SLIM_SUBPROBLEM_INSTANCE)

    # Scrittura dei servizi
    compress_services(b, instance.services, codes)

    # Scrittura dei pazienti
    b.append(len(instance.patients))
    for patient_name, patient in instance.patients.items():

        b.append(codes['patients'][patient_name])
        b.append(patient.priority)

        b.append(len(patient.requests))
        for request in patient.requests:
            
            if isinstance(request, ServiceOperator):
                b.append(codes['services'][request.service_name])
                if day_name is None:
                    b.append(codes['operators'][request.operator_name])
                else:
                    b.append(codes['operators'][f'{day_name}__{request.operator_name}'])
            else:
                b.append(codes['services'][request])

    # Scrittura del giorno
    b.append(len(instance.day.care_units))
    for care_unit_name, care_unit in instance.day.care_units.items():

        b.append(codes['care_units'][care_unit_name])

        b.append(len(care_unit))
        for operator_name, operator in care_unit.items():

            if day_name is None:
                b.append(codes['operators'][operator_name])
            else:
                b.append(codes['operators'][f'{day_name}__{operator_name}'])
            b.append(operator.start)
            b.append(operator.end)

    write_binary_file(b, file_name)


def decompress_subproblem_instance(day_name: str | None, file_name: str, codes: dict) -> FatSubproblemInstance | SlimSubproblemInstance | None:

    b = read_binary_file(file_name)

    cursor = 2
    if b[cursor] == FAT_SUBPROBLEM_INSTANCE:
        instance = FatSubproblemInstance()
        is_fat = True
    elif b[cursor] == SLIM_SUBPROBLEM_INSTANCE:
        instance = SlimSubproblemInstance()
        is_fat = False
    else:
        return None
    cursor += 1
    
    reverse_codes = get_reverse_codes(codes)

    service_number = b[cursor]
    cursor += 1
    for _ in range(service_number):
    
        service_name = reverse_codes['services'][b[cursor]]
        care_unit_name = reverse_codes['care_units'][b[cursor + 1]]
        duration = b[cursor + 2]
        cursor += 3

        instance.services[service_name] = Service(care_unit_name, duration)

    patient_number = b[cursor]
    cursor += 1
    for _ in range(patient_number):

        patient_name = reverse_codes['patients'][b[cursor]]
        priority = b[cursor + 1]
        request_number = b[cursor + 2]
        cursor += 3

        if is_fat:
            patient = FatSubproblemPatient(priority)
        else:
            patient = SlimSubproblemPatient(priority)
        
        for _ in range(request_number):

            if is_fat:
                service_name = reverse_codes['services'][b[cursor]]
                if day_name is None:
                    operator_name = reverse_codes['operators'][b[cursor + 1]]
                else:
                    operator_name = reverse_codes['operators'][day_name][b[cursor + 1]]
                cursor += 2

                patient.requests.append(ServiceOperator(service_name, operator_name)) # type: ignore
            
            else:
                service_name = reverse_codes['services'][b[cursor]]
                cursor += 1

                patient.requests.append(service_name) # type: ignore
            
        instance.patients[patient_name] = patient # type: ignore

    care_unit_number = b[cursor]
    cursor += 1
    for _ in range(care_unit_number):

        care_unit_name = reverse_codes['care_units'][b[cursor]]
        operator_number = b[cursor + 1]
        cursor += 2

        for _ in range(operator_number):

            if day_name is None:
                operator_name = reverse_codes['operators'][b[cursor]]
            else:
                operator_name = reverse_codes['operators'][day_name][b[cursor]]
            start = b[cursor + 1]
            duration = b[cursor + 2]
            cursor += 3

            instance.day.add_operator(operator_name, Operator(care_unit_name, start, duration))

    return instance


def compress_subproblem_result(result: FatSubproblemResult | SlimSubproblemResult, day_name: str | None, file_name: str, codes: dict):

    # Lista di byte
    b = []

    # Primo byte che identifica il tipo di file
    if isinstance(result, FatSubproblemResult):
        b.append(FAT_SUBPROBLEM_RESULT)
    else:
        b.append(SLIM_SUBPROBLEM_RESULT)
    
    b.append(len(result.scheduled))
    for request in result.scheduled:
        
        b.append(codes['patients'][request.patient_name])
        b.append(codes['services'][request.service_name])
        
        if day_name is None:
            b.append(codes['operators'][request.operator_name])
        else:
            b.append(codes['operators'][f'{day_name}__{request.operator_name}'])
        
        b.append(request.time_slot)
    
    b.append(len(result.rejected))
    for request in result.rejected:
        
        b.append(codes['patients'][request.patient_name])
        b.append(codes['services'][request.service_name])
        
        if isinstance(request, PatientServiceOperator):
            if day_name is None:
                b.append(codes['operators'][request.operator_name])
            else:
                b.append(codes['operators'][f'{day_name}__{request.operator_name}'])

    write_binary_file(b, file_name)


def decompress_subproblem_result(day_name: str | None, file_name: str, codes: dict) -> FatSubproblemResult | SlimSubproblemResult | None:

    b = read_binary_file(file_name)

    cursor = 2
    if b[cursor] == FAT_SUBPROBLEM_RESULT:
        result = FatSubproblemResult()
        is_fat = True
    elif b[cursor] == SLIM_SUBPROBLEM_RESULT:
        result = SlimSubproblemResult()
        is_fat = False
    else:
        return None
    cursor += 1
    
    reverse_codes = get_reverse_codes(codes)

    scheduled_request_number = b[cursor]
    cursor += 1
    for _ in range(scheduled_request_number):

        patient_name = reverse_codes['patients'][b[cursor]]
        service_name = reverse_codes['services'][b[cursor + 1]]
        if day_name is None:
            operator_name = reverse_codes['operators'][b[cursor + 2]]
        else:
            operator_name = reverse_codes['operators'][day_name][b[cursor + 2]]
        time_slot = b[cursor + 3]
        cursor += 4

        result.scheduled.append(PatientServiceOperatorTimeSlot(
            patient_name, service_name, operator_name, time_slot))
    
    rejected_request_number = b[cursor]
    cursor += 1
    for _ in range(rejected_request_number):

        patient_name = reverse_codes['patients'][b[cursor]]
        service_name = reverse_codes['services'][b[cursor + 1]]
        if is_fat:
            operator_name = reverse_codes['operators'][b[cursor + 2]]
            result.rejected.append(PatientServiceOperator(patient_name, service_name, operator_name))
        else:
            result.rejected.append(PatientService(patient_name, service_name)) # type: ignore
        cursor += 3

    return result


def compress_final_result(days_are_all_equal: bool, result: FinalResult, file_name: str, codes: dict):

    # Lista di byte
    b = []

    # Primo byte che identifica il tipo di file
    b.append(FINAL_RESULT)

    # Scrittura delle richieste di ogni giorno
    b.append(len(result.scheduled))
    for day_name, requests in result.scheduled.items():

        b.append(codes['days'][day_name])

        b.append(len(requests))
        for request in requests:

            b.append(codes['patients'][request.patient_name])
            b.append(codes['services'][request.service_name])
            if days_are_all_equal:
                b.append(codes['operators'][request.operator_name])
            else:
                b.append(codes['operators'][f'{day_name}__{request.operator_name}'])
            b.append(request.time_slot)
    
    rejected_request_number = len(result.rejected)
    b.append(rejected_request_number & 0xff)
    b.append((rejected_request_number >> 8) & 0xff)

    for request in result.rejected:

        b.append(codes['patients'][request.patient_name])
        b.append(codes['services'][request.service_name])
        b.append(request.window.start)
        b.append(request.window.duration)

    write_binary_file(b, file_name)


def decompress_final_result(days_are_all_equal: bool, file_name: str, codes: dict) -> FinalResult | None:

    b = read_binary_file(file_name)

    cursor = 2
    if b[cursor] != FINAL_RESULT:
        return None
    cursor += 1
    
    result = FinalResult()
    
    reverse_codes = get_reverse_codes(codes)

    day_number = b[cursor]
    cursor += 1
    for _ in range(day_number):

        day_name = reverse_codes['days'][b[cursor]]
        request_number = b[cursor + 1]
        cursor += 2

        result.scheduled[day_name] = []

        for _ in range(request_number):

            patient_name = reverse_codes['patients'][b[cursor]]
            service_name = reverse_codes['services'][b[cursor + 1]]
            if days_are_all_equal:
                operator_name = reverse_codes['operators'][b[cursor + 2]]
            else:
                operator_name = reverse_codes['operators'][day_name][b[cursor + 2]]
            time_slot = b[cursor + 3]
            cursor += 4

            result.scheduled[day_name].append(PatientServiceOperatorTimeSlot(patient_name, service_name, operator_name, time_slot))

    rejected_request_number = b[cursor] | (b[cursor + 1] << 8)
    cursor += 2

    for _ in range(rejected_request_number):

        patient_name = reverse_codes['patients'][b[cursor]]
        service_name = reverse_codes['services'][b[cursor + 1]]
        start = b[cursor + 2]
        duration = b[cursor + 3]
        cursor += 4

        result.rejected.append(PatientServiceWindow(patient_name, service_name, Window(start, start + duration)))

    return result


def compress_cores(cores: list[FatCore] | list[SlimCore], file_name: str, codes: dict):

    # Lista di byte
    b = []

    # Primo byte che identifica il tipo di file
    if isinstance(cores[0], FatCore):
        b.append(FAT_CORES)
    else:
        b.append(SLIM_CORES)

    # Scrittura del numero totale di core (int_16)
    core_number = len(cores)
    b.append(core_number & 0xff)
    b.append((core_number >> 8) & 0xff)

    # Scrittura dei core
    for core in cores:

        b.append(codes['days'][core.day])

        # Scrittura del motivo del core corrente
        b.append(len(core.reason))
        for reason in core.reason:

            b.append(codes['patients'][reason.patient_name])
            b.append(codes['services'][reason.service_name])

            if isinstance(reason, PatientServiceOperator):
                b.append(codes['operators'][f'{core.day}__{reason.operator_name}'])
        
        # Scrittura delle componenti del core corrente
        b.append(len(core.components))
        for component in core.components:

            b.append(codes['patients'][component.patient_name])
            b.append(codes['services'][component.service_name])

            if isinstance(component, PatientServiceOperator):
                b.append(codes['operators'][f'{core.day}__{component.operator_name}'])

    write_binary_file(b, file_name)


def decompress_cores(days_are_all_equal: bool, file_name: str, codes: dict) -> list[FatCore] | list[SlimCore] | None:

    b = read_binary_file(file_name)

    cursor = 2
    if b[cursor] == FAT_CORES:
        is_fat = True
    elif b[cursor] == SLIM_CORES:
        is_fat = False
    else:
        return None
    cursor += 1

    cores: list[FatCore] | list[SlimCore] = []
    
    reverse_codes = get_reverse_codes(codes)

    core_number = b[cursor] | (b[cursor + 1] << 8)
    cursor += 2

    for _ in range(core_number):

        day_name = reverse_codes['days'][b[cursor]]
        cursor += 1

        if is_fat:
            core = FatCore(day_name)
        else:
            core = SlimCore(day_name)
        
        reason_number = b[cursor]
        cursor += 1
        for _ in range(reason_number):

            patient_name = reverse_codes['patients'][b[cursor]]
            service_name = reverse_codes['services'][b[cursor + 1]]
            cursor += 2

            if is_fat:
                if days_are_all_equal:
                    operator_name = reverse_codes['operators'][b[cursor]]
                else:
                    operator_name = reverse_codes['operators'][day_name][b[cursor]]
                cursor += 1
                core.reason.append(PatientServiceOperator(patient_name, service_name, operator_name))
            else:
                core.reason.append(PatientService(patient_name, service_name)) # type: ignore
        
        component_number = b[cursor]
        cursor += 1
        for _ in range(component_number):

            patient_name = reverse_codes['patients'][b[cursor]]
            service_name = reverse_codes['services'][b[cursor + 1]]
            cursor += 2

            if is_fat:
                if days_are_all_equal:
                    operator_name = reverse_codes['operators'][b[cursor]]
                else:
                    operator_name = reverse_codes['operators'][day_name][b[cursor]]
                cursor += 1
                core.components.append(PatientServiceOperator(patient_name, service_name, operator_name))
            else:
                core.components.append(PatientService(patient_name, service_name)) # type: ignore
        
        cores.append(core) # type: ignore

    return cores