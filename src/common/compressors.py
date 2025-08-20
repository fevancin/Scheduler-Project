import json

from src.common.custom_types import MasterInstance, FatMasterResult, SlimMasterResult
from src.common.custom_types import FatSubproblemInstance, SlimSubproblemInstance
from src.common.custom_types import FatSubproblemResult, SlimSubproblemResult
from src.common.custom_types import FinalResult, FatCore, SlimCore, CacheMatch
from src.common.custom_types import PatientServiceOperator, Service, ServiceOperator
from src.common.custom_types import ServiceName, PatientName, OperatorName, CareUnitName, DayName


MASTER_INSTANCE = 0
FAT_MASTER_RESULT = 1
SLIM_MASTER_RESULT = 2
FAT_SUBPROBLEM_INSTANCE = 3
SLIM_SUBPROBLEM_INSTANCE = 4
FINAL_RESULT = 5
FAT_CORES = 6
SLIM_CORES = 7


def write_binary_file(b: list[int], file_name: str):

    # Inserisci all'inizio il numero di byte del file (int_16)
    b_len = len(b)
    b.insert(0, b_len & 0xff)
    b.insert(0, (b_len >> 8) & 0xff)

    with open(file_name, 'wb') as file:
        file.write(bytearray(b))


def compress_services(b: list[int], services: dict[ServiceName, Service], codes: dict):

    b.append(len(services))
    for service_name, service in services.items():
        
        care_unit_name = service.care_unit_name
        duration = service.duration
        
        if service_name not in codes['services']:
            codes['services'][service_name] = len(codes['services'])

        # Aggiunta ai codici dell'unità di cura, se non ancora presente
        if care_unit_name not in codes['care_units']:
            codes['care_units'][care_unit_name] = len(codes['care_units'])

        b.append(codes['care_units'][service.care_unit_name])
        b.append(duration)


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
    for day_name, day in instance.days.items():
        codes['days'][day_name] = len(codes['days'])

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

                codes['operators'][f'{day_name}__{operator_name}'] = operator_code
                operator_code += 1

                b.append(codes['operators'][f'{day_name}__{operator_name}'])
                b.append(operator.start)
                b.append(operator.end)
    
    write_binary_file(b, file_name)
    
    with open('codes.json', 'w') as file:
        json.dump(codes, file, indent=4)


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
    
    write_binary_file(b, file_name)


def compress_subproblem_instance(instance: FatSubproblemInstance | SlimSubproblemInstance, day_name: DayName, file_name: str, codes: dict):

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
                b.append(codes['operators'][f'{day_name}__{request.operator_name}'])
            else:
                b.append(codes['services'][request])

    # Scrittura del giorno
    b.append(len(instance.day.care_units))
    for care_unit_name, care_unit in instance.day.care_units.items():

        b.append(codes['care_units'][care_unit_name])

        b.append(len(care_unit))
        for operator_name, operator in care_unit.items():

            b.append(codes['operators'][f'{day_name}__{operator_name}'])
            b.append(operator.start)
            b.append(operator.end)

    write_binary_file(b, file_name)


def compress_final_result(result: FinalResult, file_name: str, codes: dict):

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
            b.append(codes['operators'][f'{day_name}__{request.operator_name}'])
            b.append(request.time_slot)

    write_binary_file(b, file_name)


def compress_cores(cores: list[FatCore] | list[SlimCore], file_name: str, codes: dict):

    if len(cores) == 0:
        return

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

        b.append(core.day)

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