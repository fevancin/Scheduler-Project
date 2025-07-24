from src.common.custom_types import MasterInstance, FatMasterResult, SlimMasterResult
from src.common.custom_types import DayName, FatSubproblemInstance, SlimSubproblemInstance
from src.common.custom_types import FatSubproblemPatient, ServiceOperator, SlimSubproblemPatient
from src.common.custom_types import FatSubproblemResult, SlimSubproblemResult, FinalResult
from src.common.custom_types import PatientServiceWindow, PatientService, PatientServiceOperator


def is_combination_to_do(
        config_name: str | None,
        group_name: str | None,
        instance_name: str | None,
        config) -> bool:
    '''Funzione che stabilisce se la terna fornita rispetta la configurazione e
    l'istanza deve essere risolta o analizzata.'''

    # Il nome della configurazione deve essere in quelle da svolgere e non deve
    # essere in quelle da evitare
    if config_name is not None:
        if 'configs_to_avoid' in config and config_name in config['configs_to_avoid']:
            return False
        if 'configs_to_do' in config and 'all' not in config['configs_to_do'] and config_name not in config['configs_to_do']:
            return False
    
    # Il nome del gruppo deve essere in quelli da svolgere e non deve essere in
    # quelli da evitare
    if group_name is not None:
        if 'groups_to_avoid' in config and group_name in config['groups_to_avoid']:
            return False
        if 'groups_to_do' in config and 'all' not in config['groups_to_do'] and group_name not in config['groups_to_do']:
            return False
    
    # Il nome dell'istanza deve essere in quelle da svolgere e non deve essere
    # in quelle da evitare
    if instance_name is not None:
        if 'instances_to_avoid' in config and instance_name in config['instances_to_avoid']:
            return False
        if 'instances_to_do' in config and 'all' not in config['instances_to_do'] and instance_name not in config['instances_to_do']:
            return False
    
    return True


def get_subproblem_instance_from_master_result(
        master_instance: MasterInstance,
        master_result: FatMasterResult | SlimMasterResult,
        day_name: DayName) -> FatSubproblemInstance | SlimSubproblemInstance:
    '''Funzione che ritorna l'istanza del sottoproblema relativa al giorno
    specificato, con le richieste del risultato del master.'''
    
    if isinstance(master_result, FatMasterResult):
        subproblem_instance = FatSubproblemInstance(
            day=master_instance.days[day_name],
            services=master_instance.services)
    else:
        subproblem_instance = SlimSubproblemInstance(
            day=master_instance.days[day_name],
            services=master_instance.services)

    # Copia le richieste del master del giorno specificato
    for request in master_result.scheduled[day_name]:
        
        patient_name = request.patient_name
        service_name = request.service_name
        
        if isinstance(subproblem_instance, FatSubproblemInstance):
            operator_name = request.operator_name # type: ignore
            if patient_name not in subproblem_instance.patients:
                subproblem_instance.patients[patient_name] = FatSubproblemPatient(master_instance.patients[patient_name].priority)
            subproblem_instance.patients[patient_name].requests.append(ServiceOperator(service_name, operator_name))
        
        else:
            if patient_name not in subproblem_instance.patients:
                subproblem_instance.patients[patient_name] = SlimSubproblemPatient(master_instance.patients[patient_name].priority)
            subproblem_instance.patients[patient_name].requests.append(service_name)
    
    return subproblem_instance


def compose_final_result(
        master_instance: MasterInstance,
        master_result: FatMasterResult | SlimMasterResult,
        all_subproblem_result: dict[DayName, FatSubproblemResult] | dict[DayName, SlimSubproblemResult]) -> FinalResult:
    '''Funzione che aggrega i risultati dei sottoproblemi in un singolo
    risultato finale.'''
    
    final_result = FinalResult(rejected=master_result.rejected)

    # Aggregazione delle richieste soddisfatte
    for day_name, subproblem_result in all_subproblem_result.items():
        final_result.scheduled[day_name] = []
        for result in subproblem_result.scheduled:
            final_result.scheduled[day_name].append(result)
    
    # Per ogni finestra richiesta dall'istanza master, se non è soddisfatta
    # viene aggiunta alle richieste rifiutate
    for patient_name, patient in master_instance.patients.items():
        for service_name, windows in patient.requests.items():
            for window in windows:

                request = PatientServiceWindow(patient_name, service_name, window)
                
                # Nessuna finestra doppia
                if request in final_result.rejected:
                    continue
                
                # Se non esiste nessuna richiesta nei sottoproblemi relativi ai
                # giorni della finestra, la richiesta non è soddisfatta
                is_satisfied = False
                for day_name in range(window.start, window.end + 1):
                    for subproblem_request in all_subproblem_result[day_name].scheduled:
                        if patient_name == subproblem_request.patient_name and service_name == subproblem_request.service_name:
                            is_satisfied = True
                            break
                    if is_satisfied:
                        break
                
                if not is_satisfied:
                    final_result.rejected.append(request)

    return final_result


def get_worst_fat_case_scenario(instance: MasterInstance) -> FatMasterResult:
    '''Calcolo dell'elenco di tutte le richieste che potrebbero verificarsi,
    con l'operatore.'''

    worst_case_result = FatMasterResult()

    # Scorri tutte le finestre
    for patient_name, patient in instance.patients.items():
        for service_name, windows in patient.requests.items():

            care_unit_name = instance.services[service_name].care_unit_name
            
            for window in windows:

                # Scorri tutti i giorni della finestra corrente
                for day_name in range(window.start, window.end + 1):
                    
                    # Scorri tutti gli operatori del giorno corrente
                    for operator_name in instance.days[day_name].care_units[care_unit_name].keys():
                        
                        request = PatientServiceOperator(patient_name, service_name, operator_name)
                        
                        # Aggiungi la richiesta
                        if day_name not in worst_case_result.scheduled:
                            worst_case_result.scheduled[day_name] = []
                        if request not in worst_case_result.scheduled[day_name]:
                            worst_case_result.scheduled[day_name].append(request)

    return worst_case_result


def get_worst_slim_case_scenario(instance: MasterInstance) -> SlimMasterResult:
    '''Calcolo dell'elenco di tutte le richieste che potrebbero verificarsi,
    senza l'operatore.'''

    worst_case_result = SlimMasterResult()

    # Scorri tutte le finestre
    for patient_name, patient in instance.patients.items():
        for service_name, windows in patient.requests.items():
            
            request = PatientService(patient_name, service_name)
            
            # Scorri tutti i giorni della finestra corrente
            for window in windows:
                for day_name in range(window.start, window.end + 1):
                    
                    # Aggiungi la richiesta
                    if day_name not in worst_case_result.scheduled:
                        worst_case_result.scheduled[day_name] = []
                    if request not in worst_case_result.scheduled[day_name]:
                        worst_case_result.scheduled[day_name].append(request)

    return worst_case_result


def get_slim_subproblem_instance_from_final_result(
        master_instance: MasterInstance,
        result: FinalResult,
        day_name: DayName):
    '''Crea un'istanza del sottoproblema dai risultati finali con le richieste
    soddisfatte di un dato giorno (nessuna richiesta rifiutata).'''
    
    subproblem_instance = SlimSubproblemInstance(
        services=master_instance.services,
        day=master_instance.days[day_name])

    # Copia le richieste di quel giorno
    for request in result.scheduled[day_name]:
        
        patient_name = request.patient_name
        service_name = request.service_name
        
        if patient_name not in subproblem_instance.patients:
            subproblem_instance.patients[patient_name] = SlimSubproblemPatient(master_instance.patients[patient_name].priority)
        subproblem_instance.patients[patient_name].requests.append(service_name)

    return subproblem_instance


def get_slim_subproblem_instance_from_fat(instance: FatSubproblemInstance) -> SlimSubproblemInstance:
    '''Crea un'istanza 'slim' del sottoproblema (senza l'informazione degli
    operatori) a partire da un'istanza 'fat'.'''
    
    forgetful_subproblem_instance = SlimSubproblemInstance(day=instance.day, services=instance.services)
    for patient_name, patient in instance.patients.items():
        forgetful_subproblem_instance.patients[patient_name] = SlimSubproblemPatient(patient.priority)
        forgetful_subproblem_instance.patients[patient_name].requests = [request.service_name for request in patient.requests] # type: ignore
    
    return forgetful_subproblem_instance