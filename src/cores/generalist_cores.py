from src.common.custom_types import DayName, FatSubproblemResult, SlimSubproblemResult
from src.common.custom_types import DayName, FatCore, SlimCore, PatientService
from src.common.custom_types import PatientServiceOperator

def get_generalist_cores(
        results: dict[DayName, FatSubproblemResult] | dict[DayName, SlimSubproblemResult]) -> list[FatCore] | list[SlimCore]:
    """Ogni giorno che presenta almeno una richiesta non soddisfatta genera un
    core con tutte le richieste (soddisfatte e non) al suo interno."""

    # Lista dei core di ogni giorno
    cores: list[FatCore] | list[SlimCore] = []

    for day_name, result in results.items():

        # Deve esserci almeno una richiesta non soddisfatta
        if len(result.rejected) == 0:
            continue

        # Tutte le richieste non soddisfatte vengono inserite
        if isinstance(result, FatSubproblemResult):
            core = FatCore(
                components=result.rejected.copy(),
                days=[day_name],
                reason=result.rejected)
        else:
            core = SlimCore(
                components=result.rejected.copy(),
                days=[day_name],
                reason=result.rejected)

        # Ogni richiesta soddisfatta viene copiata
        if isinstance(core, FatCore):
            for scheduled_request in result.scheduled:
                core.components.append(PatientServiceOperator(
                    patient_name=scheduled_request.patient_name,
                    service_name=scheduled_request.service_name,
                    operator_name=scheduled_request.operator_name
                ))
        else:
            for scheduled_request in result.scheduled:
                core.components.append(PatientService(
                    patient_name=scheduled_request.patient_name,
                    service_name=scheduled_request.service_name
                ))

        # Ordinamento componenti e aggiunta alla lista complessiva
        core.components.sort(key=lambda r: (r.patient_name, r.service_name))
        cores.append(core) # type: ignore

    return cores