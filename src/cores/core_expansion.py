import pyomo.environ as pyo
import time

from src.common.custom_types import FatCore, SlimCore, DayName
from src.common.custom_types import PatientService, PatientServiceOperator, SlimArc, FatArc
from src.milp_models.max_matching_model import get_max_matching_model, get_matching_from_max_matching_model, ban_matching_from_model

def get_expansion_arcs(
        core: FatCore | SlimCore,
        all_possible_master_requests: list[PatientServiceOperator] | list[PatientService],
        config) -> set[SlimArc] | set[FatArc]:
    """Funzione che ritorna l'elenco di tutte le coppie che rappresentano
    possibili rinomine fra componenti del core e possibili richieste del master.
    Questo elenco definisce un grafo bipartito. A seconda dei parametri di
    configurazione alcuni di questi archi non verrano inclusi."""

    is_fat = isinstance(core, FatCore)

    # Lista di tutti gli archi del grafo bipartito
    arcs: set[FatArc] | set[SlimArc] = set()

    # Ogni componente del core viene vista come un vertice di sinistra
    for component in core.components:

        # Ricerca dei vertici di destra a lui collegati
        for request in all_possible_master_requests:

            # Se il nome del paziente o servizio è differente e non li stiamo
            # anonimizzando, l'arco non va bene
            if ((not config['core_patient_expansion'] and component.patient_name != request.patient_name) or
                (not config['core_service_expansion'] and component.service_name != request.service_name)):
                continue

            # Se il nome dell'operatore è differente e non lo stiamo
            # anonimizzando, l'arco non va bene
            if is_fat and not config['core_operator_expansion'] and component.operator_name != request.operator_name: # type: ignore
                continue
            
            # Se i controlli sopra non si sono attivati, aggiungi l'arco nel
            # grafo
            if is_fat:
                arcs.add((
                    PatientServiceOperator(component.patient_name, component.service_name, component.operator_name), # type: ignore
                    PatientServiceOperator(request.patient_name, request.service_name, request.operator_name))) # type: ignore
            else:
                arcs.add((
                    PatientService(component.patient_name, component.service_name),
                    PatientService(request.patient_name, request.service_name)))

    return arcs


def get_core_from_matching(
        core: FatCore | SlimCore,
        matching: set[SlimArc] | set[FatArc]) -> FatCore | SlimCore:
    """Rinomina del core con i dati presenti nel matching. Eventuali nomi non
    presenti saranno copiati senza modifiche. Questa funzione non modifica il
    core di input."""

    if isinstance(core, FatCore):
        matched_core = FatCore(days=core.days)
    else:
        matched_core = SlimCore(days=core.days)

    # Ogni componente del core andrà rinominata, se esiste nel matching
    for component in core.components:

        matched_component = None
        for arc in matching:
            if arc[0] == component:
                matched_component = arc[1]
                break
        
        if matched_component is not None:
            matched_core.components.append(matched_component) # type: ignore
        else:
            matched_core.components.append(component) # type: ignore
    
    # Ogni motivo del core andrà rinominato, se esiste nel matching
    for component in core.reason:

        matched_component = None
        for arc in matching:
            if arc[0] == component:
                matched_component = arc[1]
                break
        
        if matched_component is not None:
            matched_core.reason.append(matched_component) # type: ignore
        else:
            matched_core.reason.append(component) # type: ignore
    
    return core
            

def expand_cores(
        cores: list[FatCore] | list[SlimCore],
        all_possible_master_requests: dict[DayName, list[PatientServiceOperator]] | dict[DayName, list[PatientService]],
        config) -> list[FatCore] | list[SlimCore]:

    expanded_cores: list[FatCore] | list[SlimCore] = []

    opt = pyo.SolverFactory('gurobi')
    opt.options['TimeLimit'] = config['core_expansion']['time_limit']
    opt.options['SoftMemLimit'] = config['core_expansion']['memory_limit']

    print(f'Expanding cores (of {len(cores)}):', end='')
    for core_index, core in enumerate(cores):
        print(f' {core_index}', end='')
        for day_name in core.days:

            arcs = get_expansion_arcs(core, all_possible_master_requests[day_name], config)
            matching_model = get_max_matching_model(arcs)
            if matching_model is None:
                print('(nomodel)', end='')
                continue

            matching_model.pprint()

            core_expansion_number = 0

            while core_expansion_number <= config['max_single_core_expansion']:

                start = time.perf_counter()
                result = opt.solve(matching_model, logfile=None)
                end = time.perf_counter()
                
                # matching_model.load(result)
                
                if end - start >= config['core_expansion']['time_limit']:
                    print('(tmlim)', end='')
                    break
                
                matching = get_matching_from_max_matching_model(matching_model, result)

                # print(matching)

                if len(matching) != len(core.components):
                    print('(no sol)', end='')
                    break

                print('(ok)', end='')

                expanded_cores.append(get_core_from_matching(core, matching)) # type: ignore
                ban_matching_from_model(matching_model, matching)

                core_expansion_number += 1
            
            if core_expansion_number >= config['max_single_core_expansion']:
                print('(maxcut)', end='')
    
    print('')

    return expanded_cores