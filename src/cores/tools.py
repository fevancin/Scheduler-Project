from src.common.custom_types import FatCore, SlimCore

def get_core_hash(core: FatCore | SlimCore) -> str:
    """Stringa che codifica in maniera non univoca uno specifico core.
    Funzione utilizzata per ottimizzare il lookup dei core."""

    return f'core_{core.reason[0].patient_name}_{core.reason[0].service_name}_{len(core.components)}'


def is_core_included(core: FatCore | SlimCore, cores: list[FatCore] | list[SlimCore]) -> bool:
    """Funzione che stabilisce se un core è già presente all'interno di una
    lista di core."""

    for other_core in cores:
        
        # Controlli sulla dimensione degli attributi per una veloce cernita
        if len(core.components) != len(other_core.components):
            continue
        if len(core.days) != len(other_core.days):
            continue
        if len(core.reason) != len(other_core.reason):
            continue
        
        # I core, per essere uguali, devono valere sugli stessi giorni
        are_days_equal = True
        for day in core.days:
            if day not in other_core.days:
                are_days_equal = False
                break
        if not are_days_equal:
            continue

        # I core, per essere uguali, devono avere le stesse componenti
        # (anche in diverso ordine)
        are_all_component_present = True
        for component in core.components:
            if component not in other_core.components:
                are_all_component_present = False
                break
        if are_all_component_present:
            return True

    return False


def check_for_duplicate_cores(cores: list[FatCore] | list[SlimCore]) -> list[FatCore] | list[SlimCore]:
    """Funzione che rimuove eventuali core duplicati, anche se hanno le
    componenti in un differente ordine. Non modifica la lista di input."""

    # Lista dei soli core giudicati unici
    unique_cores: list[FatCore] | list[SlimCore] = []
    
    for core in cores:

        # Se dopo aver controllato il core corrente con tutti quelli
        # già unici non si è trovata nessuna copia, aggiungilo a sua volta nella
        # lista degli unici
        if is_core_included(core, unique_cores):
            unique_cores.append(core) # type: ignore

    return unique_cores


def aggregate_core_lists(
        cores: list[FatCore] | list[SlimCore],
        other_cores: list[FatCore] | list[SlimCore]) -> list[FatCore] | list[SlimCore]:
    """Funzione che combina due liste di core, rimuovendo eventuali duplicati.
    Le liste originarie non vengono modificate."""
    
    aggregate_list: list[FatCore] | list[SlimCore] = []

    # Aggiungi tutti i core unici della prima lista
    for core in cores:
        if not is_core_included(core, aggregate_list):
            aggregate_list.append(core) # type: ignore
    
    # Aggiungi tutti i core unici della seconda lista
    for other_core in other_cores:
        if not is_core_included(other_core, aggregate_list):
            aggregate_list.append(core) # type: ignore

    return aggregate_list