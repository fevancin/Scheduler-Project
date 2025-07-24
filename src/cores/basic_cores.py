from src.common.custom_types import DayName, FatSubproblemResult, FatCore, SlimCore
from src.common.custom_types import PatientServiceOperator, SlimSubproblemResult, PatientService

def get_basic_fat_cores(results: dict[DayName, FatSubproblemResult]) -> list[FatCore]:
    """Ogni singola richiesta non soddisfatta in un certo giorno genera un core
    con quella richiesta più tutte le richieste soddisfatte di quel giorno."""

    # Lista dei core di ogni giorno
    cores: list[FatCore] = []

    for day_name, result in results.items():

        # Deve esserci almeno una richiesta non soddisfatta
        if len(result.rejected) == 0:
            continue

        # Ogni richiesta non soddisfatta genera il suo core
        for rejected_request in result.rejected:
        
            core = FatCore(
                components=[rejected_request],
                days=[day_name],
                reason=[rejected_request])

            # Ogni richiesta soddisfatta viene copiata
            for scheduled_request in result.scheduled:
                core.components.append(PatientServiceOperator(
                    patient_name=scheduled_request.patient_name,
                    service_name=scheduled_request.service_name,
                    operator_name=scheduled_request.operator_name
                ))

            # Ordinamento componenti e aggiunta alla lista complessiva
            core.components.sort(key=lambda r: (r.patient_name, r.service_name))
            cores.append(core)

    return cores

def get_basic_slim_cores(results: dict[DayName, SlimSubproblemResult]) -> list[SlimCore]:
    """Ogni singola richiesta non soddisfatta in un certo giorno genera un core
    con quella richiesta più tutte le richieste soddisfatte di quel giorno."""

    # Lista dei core di ogni giorno
    cores: list[SlimCore] = []

    for day_name, result in results.items():

        # Deve esserci almeno una richiesta non soddisfatta
        if len(result.rejected) == 0:
            continue

        # Ogni richiesta non soddisfatta genera il suo core
        for rejected_request in result.rejected:
        
            core = SlimCore(
                components=[rejected_request],
                days=[day_name],
                reason=[rejected_request])

            # Ogni richiesta soddisfatta viene copiata
            for scheduled_request in result.scheduled:
                core.components.append(PatientService(
                    patient_name=scheduled_request.patient_name,
                    service_name=scheduled_request.service_name
                ))

            # Ordinamento componenti e aggiunta alla lista complessiva
            core.components.sort(key=lambda r: (r.patient_name, r.service_name))
            cores.append(core)

    return cores