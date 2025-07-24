from src.common.custom_types import Cache, PatientServiceWindow, DayName, IterationDay
from src.common.custom_types import MasterInstance, FinalResult, IterationName
from src.common.custom_types import PatientServiceOperatorTimeSlot

def is_request_already_present(
        cache: Cache,
        requests_to_add: set[PatientServiceWindow],
        day_name: DayName) -> bool:
    """Controlla se le richieste da aggiungere in cache sono già presenti tutte
    nello stesso giorno ma in un'altra iterazione."""
    
    # Elenco di (i, d) che possiedono tutte le richieste da aggiungere in
    # cache (diminuiranno di volta in volta)
    possible_values: set[IterationDay] | None = None
    
    # Ogni richiesta deve essere presente in una stessa iterazione
    for request in requests_to_add:

        # Se la cache non contiene ancora una delle richieste allora di sicuro
        # la combinazione di richieste non è presente
        if request not in cache:
            return False
        
        # La prima richiesta popola le iterazioni possibili con tutte quelle che
        # possiedono la richiesta
        if possible_values is None:
            possible_values = {id for id in cache[request] if id.day_name == day_name}
        
        # Dalla seconda richiesta scarteremo le iterazioni che non permettono
        # di mantenere soddisfatte tutte le richieste incontrate fino ad ora
        else:
            possible_values = {id for id in possible_values if id in cache[request]}
        
        # Se non si hanno più iterazioni possibili allora la combinazione di
        # richieste è nuova
        if len(possible_values) == 0:
            return False

    return True

def add_final_result_to_cache(
        cache: Cache, master_instance: MasterInstance,
        final_result: FinalResult,
        iteration_name: IterationName):
    """Incrementa la matrice di cache aggiungendo le informazioni delle
    soluzioni dell'iterazione specificata."""

    # Itera ogni richiesta soddisfatta di ogni giorno
    for day_name, requests in final_result.scheduled.items():
        
        requests_to_add: set[PatientServiceWindow] = set()
        
        for request in requests:

            patient_name = request.patient_name
            service_name = request.service_name

            # Itera ogni finestra del paziente del servizio corrente
            for window in master_instance.patients[patient_name].requests[service_name]:
                if window.contains(day_name):
                    requests_to_add.add(PatientServiceWindow(patient_name, service_name, window))
    
        # Si evita di aggiungere soluzioni già presenti
        if is_request_already_present(cache, requests_to_add, day_name):
            continue

        # Aggiungi la coppia (i, d) alla cache per ogni richiesta toccata
        for request in requests_to_add:
            if request not in cache:
                cache[request] = []
            cache[request].append(IterationDay(iteration_name, day_name))

def fix_cache_final_result(master_instance: MasterInstance, final_result: FinalResult):

    for patient_name, patient in master_instance.patients.items():
        for service_name, windows in patient.requests.items():
            for window in windows:
                
                is_satisfied = False
                requests_to_remove: dict[DayName, PatientServiceOperatorTimeSlot] = {}
                
                for day_name in range(window.start, window.end + 1):
                    
                    for request in final_result.scheduled[day_name]:
                        if patient_name == request.patient_name and service_name == request.service_name:
                            if is_satisfied:
                                requests_to_remove[day_name] = request
                            is_satisfied = True
                            
                for day_name, request in requests_to_remove.items():
                    final_result.scheduled[day_name].remove(request)

    for patient_name, patient in master_instance.patients.items():
        for service_name, windows in patient.requests.items():
            for window in windows:
                
                is_satisfied = False
                for day_name in range(window.start, window.end + 1):
                    for request in final_result.scheduled[day_name]:
                        if patient_name == request.patient_name and service_name == request.service_name:
                            is_satisfied = True
                            break
                    if is_satisfied:
                        break
                
                if not is_satisfied:
                    request = PatientServiceWindow(patient_name, service_name, window)
                    if request not in final_result.rejected:
                        final_result.rejected.append(PatientServiceWindow(patient_name, service_name, window))
