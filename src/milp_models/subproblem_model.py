import pyomo.environ as pyo
from src.common.custom_types import FatSubproblemInstance, SlimSubproblemInstance, FatSubproblemResult, SlimSubproblemResult
from src.common.custom_types import PatientServiceOperatorTimeSlot, PatientService, PatientServiceOperator

def get_fat_subproblem_model(
        instance: SlimSubproblemInstance,
        additional_info: list[str],
        fat_requests: list[PatientServiceOperator] | None=None) -> pyo.ConcreteModel:

    model: pyo.ConcreteModel = pyo.ConcreteModel() # type: ignore
    
    # INSIEMI ##################################################################
   
    model.care_units = pyo.Set(initialize=sorted(c for c in instance.day.care_units.keys())) # type: ignore
    model.operators = pyo.Set(initialize=sorted(o for o in instance.day.operators.keys())) # type: ignore

    # PARAMETRI ################################################################

    # max_time[c] è il massimo tempo di fine degli operatori in c
    @model.Param(model.care_units, domain=pyo.NonNegativeIntegers, mutable=False) # type: ignore
    def max_time(model, c):
        return max(o.start + o.duration for o in instance.day.care_units[c].values()) + 1

    # INDICI ###################################################################

    # Coppie (p, s) per ogni richiesta
    satisfy_index = set()

    # Triple (p, s, o) per ogni possibile assegnamento valido
    do_index = set()

    # Terne (p, s1, s2) per ogni coppia di richieste dello stesso paziente
    patient_overlap_index = set()

    # Tuple (p1, s1, p2, s2, o)
    operator_overlap_index = set()

    for p, patient in instance.patients.items():
        for s in patient.requests:
            satisfy_index.add((p, s))

            care_unit_name = instance.services[s].care_unit_name
            for o in instance.day.care_units[care_unit_name].keys():
                do_index.add((p, s, o))

    for p, patient in instance.patients.items():
        
        # Bisogna avere almeno due richieste
        request_number = len(patient.requests)
        if request_number < 2:
            continue
        
        # Itera tutte le coppie
        for i in range(request_number - 1):
            for j in range(i + 1, request_number):
                patient_overlap_index.add((p, patient.requests[i], patient.requests[j]))

    for p, s, o in do_index:
        for pp, ss, oo in do_index:
            
            # Deve essere lo stesso operatore
            if o != oo:
                continue
            
            # Controllo sulla simmetria
            if p >= pp or (p == pp and s >= ss):
                continue
            
            operator_overlap_index.add((p, s, pp, ss, o))

    model.satisfy_index = pyo.Set(initialize=sorted(satisfy_index)) # type: ignore
    model.do_index = pyo.Set(initialize=sorted(do_index)) # type: ignore
    model.patient_overlap_index = pyo.Set(initialize=sorted(patient_overlap_index)) # type: ignore
    model.operator_overlap_index = pyo.Set(initialize=sorted(operator_overlap_index)) # type: ignore
    
    del satisfy_index, do_index, patient_overlap_index, operator_overlap_index

    def get_time_bounds(model, p: str, s: str) -> tuple[int, int]:

        service_duration = instance.services[s].duration
        care_unit_name = instance.services[s].care_unit_name
        max_operator_end = max(o.start + o.duration for o in instance.day.care_units[care_unit_name].values())
        
        return (0, max_operator_end + 1 - service_duration)

    # VARIABILI ################################################################

    # Variabili decisionali che controllano quale richiesta è soddisfatta
    model.satisfy = pyo.Var(model.satisfy_index, domain=pyo.Binary) # type: ignore

    # Se una richiesta è sodisfatta le variabili 'time' assumono un valore
    # positivo che descrive il tempo di inizio
    model.time = pyo.Var(model.satisfy_index, domain=pyo.NonNegativeIntegers, bounds=get_time_bounds) # type: ignore

    # Variabili decisionali che descrivono che operatore svolge ogni richiesta
    model.do = pyo.Var(model.do_index, domain=pyo.Binary) # type: ignore

    # Variabili ausiliarie per la mutua esclusione delle richieste assegnate
    model.patient_overlap = pyo.Var(model.patient_overlap_index, domain=pyo.Binary) # type: ignore
    model.operator_overlap_1 = pyo.Var(model.operator_overlap_index, domain=pyo.Binary) # type: ignore
    model.operator_overlap_2 = pyo.Var(model.operator_overlap_index, domain=pyo.Binary) # type: ignore

    # VINCOLI ##################################################################

    # Vincoli che forzano 'time' ad essere un valore positivo se e solo se
    # 'satisfy' è maggiore di zero
    @model.Constraint(model.satisfy_index) # type: ignore
    def link_satisfy_to_time_variables(model, p, s):
        return model.satisfy[p, s] <= model.time[p, s]
    @model.Constraint(model.satisfy_index) # type: ignore
    def link_time_to_satisfy_variables(model, p, s):
        return model.time[p, s] <= model.satisfy[p, s] * get_time_bounds(model, p, s)[1]

    # Se una richiesta viene soddisfatta, viene assegnata una volta sola
    @model.Constraint(model.satisfy_index) # type: ignore
    def link_satisfy_to_do_variables(model, p, s):
        return model.satisfy[p, s] == pyo.quicksum(model.do[pp, ss, o] for pp, ss, o in model.do_index if p == pp and s == ss)
    
    # Rispetto dei tempi di attività degli operatori
    @model.Constraint(model.do_index) # type: ignore
    def respect_operator_start(model, p, s, o):
        return (instance.day.operators[o].start + 1) * model.do[p, s, o] <= model.time[p, s]
    @model.Constraint(model.do_index) # type: ignore
    def respect_operator_end(model, p, s, o):
        return model.time[p, s] + instance.services[s].duration <= instance.day.operators[o].end + 1 + (1 - model.do[p, s, o]) * model.max_time[instance.services[s].care_unit_name]

    # Disgiunzione dei servizi dello stesso paziente
    @model.Constraint(model.patient_overlap_index) # type: ignore
    def patient_not_overlap_1(model, p, s, ss):
        return model.time[p, s] + instance.services[s].duration * model.satisfy[p, s] <= model.time[p, ss] + (1 - model.patient_overlap[p, s, ss]) * model.max_time[instance.services[s].care_unit_name]
    @model.Constraint(model.patient_overlap_index) # type: ignore
    def patient_not_overlap_2(model, p, s, ss):
        return model.time[p, ss] + instance.services[ss].duration * model.satisfy[p, ss] <= model.time[p, s] + (model.patient_overlap[p, s, ss]) * model.max_time[instance.services[ss].care_unit_name]

    # Vincoli ausilari che regolano le variabili 'patient_overlap'
    # o-----------------------------------------o
    # | A | B | patient_overlap                 |
    # |---|---|---------------------------------|
    # | o | o | zero or one                     |
    # | o | x | zero                            |
    # | x | o | one                             |
    # | x | x | zero                            |
    # o-----------------------------------------o
    @model.Constraint(model.patient_overlap_index) # type: ignore
    def patient_overlap_auxiliary_constraint_1(model, p, s, ss):
        return model.patient_overlap[p, s, ss] <= model.satisfy[p, ss]
    @model.Constraint(model.patient_overlap_index) # type: ignore
    def patient_overlap_auxiliary_constraint_2(model, p, s, ss):
        return model.satisfy[p, ss] - model.satisfy[p, s] <= model.patient_overlap[p, s, ss]

    # Disgiunzione dei servizi dello stesso operatore
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_not_overlap_1(model, p, s, pp, ss, o):
        return model.time[p, s] + instance.services[s].duration * model.do[p, s, o] <= model.time[pp, ss] + (1 - model.operator_overlap_1[p, s, pp, ss, o]) * model.max_time[instance.day.operators[o].care_unit_name]
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_not_overlap_2(model, p, s, pp, ss, o):
        return model.time[pp, ss] + instance.services[ss].duration * model.do[pp, ss, o] <= model.time[p, s] + (1 - model.operator_overlap_2[p, s, pp, ss, o]) * model.max_time[instance.day.operators[o].care_unit_name]

    # Vincoli ausilari che regolano le variabili 'operator_overlap'
    # o-------------------------------------------------o
    # | A | B | operator_overlap_1 + operator_overlap_2 |
    # |---|---|-----------------------------------------|
    # | o | o | one                                     |
    # | o | x | zero                                    |
    # | x | o | zero                                    |
    # | x | x | zero                                    |
    # o-------------------------------------------------o
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_overlap_auxiliary_constraint_1(model, p, s, pp, ss, o):
        return model.do[p, s, o] + model.do[pp, ss, o] - 1 <= model.operator_overlap_1[p, s, pp, ss, o] + model.operator_overlap_2[p, s, pp, ss, o]
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_overlap_auxiliary_constraint_2(model, p, s, pp, ss, o):
        return model.do[p, s, o] >= model.operator_overlap_1[p, s, pp, ss, o] + model.operator_overlap_2[p, s, pp, ss, o]
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_overlap_auxiliary_constraint_3(model, p, s, pp, ss, o):
        return model.do[pp, ss, o] >= model.operator_overlap_1[p, s, pp, ss, o] + model.operator_overlap_2[p, s, pp, ss, o]

    # La durata totale dei servizi assegnati ad un operatore non può superare la
    # durata di attività di quest'ultimo
    if 'use_redundant_operator_cut' in additional_info:
        @model.Constraint(model.operators) # type: ignore
        def respect_operator_duration(model, o):
            
            tuples_affected = [(p, s) for p, s, oo in model.do_index if oo == o]
            if len(tuples_affected) == 0 or sum(instance.services[s].duration for _, s in tuples_affected) <= instance.day.operators[o].duration:
                return pyo.Constraint.Skip
            
            return pyo.quicksum(model.do[p, s, o] * instance.services[s].duration for p, s in tuples_affected) <= instance.day.operators[o].duration

    # FUNZIONE OBIETTIVO #######################################################

    # L'obiettivo è massimizzare la durata dei servizi svolti pesati per la
    # priorità dei pazienti. 
    if 'preemptive_forbidding' not in additional_info or fat_requests is None:
        @model.Objective(sense=pyo.maximize) # type: ignore
        def objective_function(model): # type: ignore
            return pyo.quicksum(model.satisfy[p, s] * instance.services[s].duration * instance.patients[p].priority for p, s in model.satisfy_index)
    
    else:
        model.e = pyo.Var(domain=pyo.Binary)

        request_tuples = [(request.patient_name, request.service_name, request.operator_name) for request in fat_requests]

        @model.Constraint(model.do_index) # type: ignore
        def is_exact_request(model, p, s, o):
            if (p, s, o) not in request_tuples:
                return pyo.Constraint.Skip
            return model.do[p, s, o] >= model.e
        
        @model.Objective(sense=pyo.maximize) # type: ignore
        def objective_function(model):
            return 1000 * model.e + pyo.quicksum(model.do[p, s, o] * instance.services[s].duration * instance.patients[p].priority for p, s, o in model.do_index)

    return model

def get_result_from_fat_subproblem_model(model: pyo.ConcreteModel) -> SlimSubproblemResult:

    result = SlimSubproblemResult()

    for p, s, o in model.do_index: # type: ignore
        if pyo.value(model.do[p, s, o]) < 0.5: # type: ignore
            continue
        t = int(pyo.value(model.time[p, s]) - 1) # type: ignore
        result.scheduled.append(PatientServiceOperatorTimeSlot(p, s, o, t))

    for p, s in model.satisfy_index: # type: ignore
        if pyo.value(model.satisfy[p, s]) < 0.5: # type: ignore
            result.rejected.append(PatientService(p, s))

    # Ordina le chiavi
    result.scheduled.sort(key=lambda r: (r.patient_name, r.service_name, r.operator_name, r.time_slot))
    result.rejected.sort(key=lambda r: (r.patient_name, r.service_name))

    return result

def get_slim_subproblem_model(instance: FatSubproblemInstance) -> pyo.ConcreteModel:

    model: pyo.ConcreteModel = pyo.ConcreteModel() # type: ignore
    
    # INSIEMI ##################################################################
   
    model.care_units = pyo.Set(initialize=sorted(c for c in instance.day.care_units.keys())) # type: ignore
    model.operators = pyo.Set(initialize=sorted(o for o in instance.day.operators.keys())) # type: ignore

    # PARAMETRI ################################################################

    # max_time[c] è il massimo tempo di fine degli operatori in c
    @model.Param(model.care_units, domain=pyo.NonNegativeIntegers, mutable=False) # type: ignore
    def max_time(model, c):
        return max(o.start + o.duration for o in instance.day.care_units[c].values()) + 1

    # INDICI ###################################################################

    # Triple (p, s, o) per ogni richiesta
    do_index = set()

    # Terne (p1, s1, o1, p2, s2, o2) per ogni coppia di richieste dello stesso
    # paziente o operatore
    overlap_index = set()

    for p, patient in instance.patients.items():
        for request in patient.requests:
            
            s = request.service_name
            o = request.operator_name
            
            do_index.add((p, s, o))

    do_index = sorted(do_index)

    for i in range(len(do_index) - 1):
        p, s, o = do_index[i]
        for j in range(i + 1, len(do_index)):
            pp, ss, oo = do_index[j]

            # Deve essere lo stesso paziente o lo stesso operatore
            if p == pp or o == oo:
                overlap_index.add((p, s, o, pp, ss, oo))

    model.do_index = pyo.Set(initialize=do_index) # type: ignore
    model.overlap_index = pyo.Set(initialize=sorted(overlap_index)) # type: ignore
    
    del do_index, overlap_index

    def get_time_bounds(model, p: str, s: str, o: str) -> tuple[int, int]:
        return (0, instance.day.operators[o].end + 1 - instance.services[s].duration)

    # VARIABILI ################################################################

    # Variabili decisionali che controllano quale richiesta è soddisfatta
    model.do = pyo.Var(model.do_index, domain=pyo.Binary) # type: ignore

    # Se una richiesta è sodisfatta le variabili 'time' assumono un valore
    # positivo che descrive il tempo di inizio
    model.time = pyo.Var(model.do_index, domain=pyo.NonNegativeIntegers, bounds=get_time_bounds) # type: ignore

    # Variabili ausiliarie per la mutua esclusione delle richieste assegnate
    model.overlap = pyo.Var(model.overlap_index, domain=pyo.Binary) # type: ignore

    # VINCOLI ##################################################################

    # Rispetto dei tempi di attività degli operatori
    @model.Constraint(model.do_index) # type: ignore
    def respect_operator_start(model, p, s, o):
        return (instance.day.operators[o].start + 1) * model.do[p, s, o] <= model.time[p, s, o]
    @model.Constraint(model.do_index) # type: ignore
    def respect_operator_end(model, p, s, o):
        return model.time[p, s, o] <= (instance.day.operators[o].end - instance.services[s].duration + 1) * model.do[p, s, o]

    # Disgiunzione dei servizi dello stesso paziente o operatore
    @model.Constraint(model.overlap_index) # type: ignore
    def not_overlap_1(model, p, s, o, pp, ss, oo):
        return model.time[p, s, o] + instance.services[s].duration * model.do[p, s, o] <= model.time[pp, ss, oo] + (1 - model.overlap[p, s, o, pp, ss, oo]) * model.max_time[instance.services[s].care_unit_name]
    @model.Constraint(model.overlap_index) # type: ignore
    def not_overlap_2(model, p, s, o, pp, ss, oo):
        return model.time[pp, ss, oo] + instance.services[ss].duration * model.do[pp, ss, oo] <= model.time[p, s, o] + (model.overlap[p, s, o, pp, ss, oo]) * model.max_time[instance.services[ss].care_unit_name]

    # Vincoli ausilari che regolano le variabili 'overlap'
    # o-----------------------------------------o
    # | A | B | patient_overlap                 |
    # |---|---|---------------------------------|
    # | o | o | zero or one                     |
    # | o | x | zero                            |
    # | x | o | one                             |
    # | x | x | zero                            |
    # o-----------------------------------------o
    @model.Constraint(model.overlap_index) # type: ignore
    def overlap_auxiliary_constraint_1(model, p, s, o, pp, ss, oo):
        return model.overlap[p, s, o, pp, ss, oo] <= model.do[pp, ss, oo]
    @model.Constraint(model.overlap_index) # type: ignore
    def overlap_auxiliary_constraint_2(model, p, s, o, pp, ss, oo):
        return model.do[pp, ss, oo] - model.do[p, s, o] <= model.overlap[p, s, o, pp, ss, oo]

    # FUNZIONE OBIETTIVO #######################################################

    # L'obiettivo è massimizzare la durata dei servizi svolti pesati per la
    # priorità dei pazienti. 
        
    @model.Objective(sense=pyo.maximize) # type: ignore
    def objective_function(model):
        return pyo.quicksum(model.do[p, s, o] * instance.services[s].duration * instance.patients[p].priority for p, s, o in model.do_index)

    return model

def get_result_from_slim_subproblem_model(model: pyo.ConcreteModel) -> FatSubproblemResult:

    result = FatSubproblemResult()

    for p, s, o in model.do_index: # type: ignore
        
        if pyo.value(model.do[p, s, o]) < 0.5: # type: ignore
            result.rejected.append(PatientServiceOperator(p, s, o))
        
        else:
            t = int(pyo.value(model.time[p, s, o]) - 1) # type: ignore
            result.scheduled.append(PatientServiceOperatorTimeSlot(p, s, o, t))

    # Ordina le chiavi
    result.scheduled.sort(key=lambda r: (r.patient_name, r.service_name, r.operator_name, r.time_slot))
    result.rejected.sort(key=lambda r: (r.patient_name, r.service_name))

    return result