import pyomo.environ as pyo
from src.common.custom_types import Cache, PatientServiceWindow, MasterInstance
from src.common.custom_types import CacheMatch, Window, IterationName, FinalResult
from src.common.custom_types import DayName, IterationDay

def get_cache_model(instance: MasterInstance, cache: Cache) -> pyo.ConcreteModel:

    model = pyo.ConcreteModel()

    # INSIEMI ##################################################################
    
    day_names = set(iter_day.day_name for iter_days in cache.values() for iter_day in iter_days)
    model.day_names = pyo.Set(initialize=sorted(day_names)) # type: ignore

    # INDICI ###################################################################

    # Insieme di coppie (i, d)
    choice_index = set((iter_day.iteration_name, iter_day.day_name) for iter_days in cache.values() for iter_day in iter_days)

    # Tuple (p, s, start, end) per ogni richiesta
    window_index = set((r.patient_name, r.service_name, r.window.start, r.window.end) for r in cache.keys())

    model.choice_index = pyo.Set(initialize=sorted(choice_index)) # type: ignore
    model.window_index = pyo.Set(initialize=sorted(window_index)) # type: ignore

    del day_names, choice_index, window_index

    # VARIABILI ################################################################

    # Variabili decisionali che specificano che iterazione è scelta per ogni
    # giorno
    model.choose = pyo.Var(model.choice_index, domain=pyo.Binary) # type: ignore

    # Variabili che descrivono il soddisfacimento di una richiesta
    model.window = pyo.Var(model.window_index, domain=pyo.Binary) # type: ignore

    # VINCOLI ##################################################################

    # Se una richiesta è soddisfatta, è soddisfatta da almeno un giorno ed una
    # iterazione
    @model.Constraint(model.window_index) # type: ignore
    def link_choose_to_window_variables(model, p, s, start, end):
        
        request = PatientServiceWindow(p, s, Window(start, end))
        affected_tuples = [(iter_day.iteration_name, iter_day.day_name) for iter_day in cache[request]]
        
        return pyo.quicksum(model.choose[i, d] for i, d in affected_tuples) >= model.window[p, s, start, end]

    # Ogni giorno deve scegliere un'iterazione sola
    @model.Constraint(model.day_names) # type: ignore
    def iteration_chooses_one_day(model, d):
        return pyo.quicksum(model.choose[i, d] for i, dd in model.choice_index if d == dd) == 1

    # FUNZIONE OBIETTIVO #######################################################

    # L'obiettivo è massimizzare la durata delle richieste svolte, pesate per la
    # priorità dei pazienti
    @model.Objective(sense=pyo.maximize) # type: ignore
    def objective_function(model):
        return pyo.quicksum(model.window[p, s, start, end] * instance.services[s].duration * instance.patients[p].priority for p, s, start, end in model.window_index)
    
    return model # type: ignore

def get_result_from_cache_model(model: pyo.ConcreteModel) -> CacheMatch:

    matching: CacheMatch = {}

    for i, d in model.choice_index: # type: ignore
        if pyo.value(model.choose[i, d]) >= 0.5: # type: ignore
            matching[d] = i
    
    # Ordina le chiavi
    matching = dict(sorted([(d, i) for d, i in matching.items()], key=lambda v: v[0]))
    
    return matching