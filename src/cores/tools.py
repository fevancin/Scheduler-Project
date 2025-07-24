from src.common.custom_types import FatCore, SlimCore

def get_core_hash(core: FatCore | SlimCore) -> str:
    """Stringa che codifica in maniera non univoca uno specifico core.
    Funzione utilizzata per ottimizzare il lookup dei core."""

    return f'core_{core.reason[0].patient_name}_{core.reason[0].service_name}_{len(core.components)}'