from src.common.custom_types import FatCore, PatientServiceOperator, ServiceName
from src.common.custom_types import Service, SlimCore, PatientService

def get_reduced_fat_cores(basic_cores: list[FatCore]) -> list[FatCore]:
    """Come i core basici, ma rimuove ogni unità di cura e paziente che non ha
    una catena di collegamenti con la ragione di esistenza del core."""

    cores = basic_cores

    # Ogni core effettua una visita delle sue componenti a partire dalla
    # richiesta che causa il core: ogni altra richiesta che condivide paziente
    # o operatore (anche a catena) viene aggiunta
    for core in cores:

        if len(core.components) == 0:
            continue

        requests_to_visit: set[PatientServiceOperator] = set()
        requests_visited: set[PatientServiceOperator] = set()

        # Richiesta di partenza
        requests_to_visit.add(core.reason[0])

        while len(requests_to_visit) > 0:

            # Estrai una richiesta e segnala come visitata
            request = requests_to_visit.pop()
            requests_visited.add(request)

            patient_name = request.patient_name
            operator_name = request.operator_name

            # Cerca ogni altra richiesta a lei collegata
            for other_request in core.components:
                if other_request in requests_visited:
                    continue
                if other_request in requests_to_visit:
                    continue
                
                # Se il paziente o l'unità di cura sono gli stessi
                if (patient_name == other_request.patient_name or
                    operator_name == other_request.operator_name):

                    requests_to_visit.add(other_request)
        
        # Le componenti non visitate vengono scartate in quanto non sono 
        # collegate con la richiesta che scatena il core
        core.components = list(requests_visited)
    
    return cores

def get_reduced_slim_cores(
        services: dict[ServiceName, Service],
        basic_cores: list[SlimCore]) -> list[SlimCore]:
    """Come i core basici, ma rimuove ogni unità di cura e paziente che non ha
    una catena di collegamenti con la ragione di esistenza del core."""

    cores = basic_cores

    # Ogni core effettua una visita delle sue componenti a partire dalla
    # richiesta che causa il core: ogni altra richiesta che condivide paziente
    # o unità di cura (anche a catena) viene aggiunta
    for core in cores:

        if len(core.components) == 0:
            continue

        requests_to_visit: set[PatientService] = set()
        requests_visited: set[PatientService] = set()

        # Richiesta di partenza
        requests_to_visit.add(core.reason[0])

        while len(requests_to_visit) > 0:

            # Estrai una richiesta e segnala come visitata
            request = requests_to_visit.pop()
            requests_visited.add(request)

            patient_name = request.patient_name
            care_unit_name = services[request.service_name].care_unit_name

            # Cerca ogni altra richiesta a lei collegata
            for other_request in core.components:
                if other_request in requests_visited:
                    continue
                if other_request in requests_to_visit:
                    continue
                
                other_care_unit_name = services[other_request.service_name].care_unit_name
                
                # Se il paziente o l'unità di cura sono gli stessi
                if (patient_name == other_request.patient_name or
                    care_unit_name == other_care_unit_name):

                    requests_to_visit.add(other_request)

        # Le componenti non visitate vengono scartate in quanto non sono 
        # collegate con la richiesta che scatena il core
        core.components = list(requests_visited)
    
    return cores