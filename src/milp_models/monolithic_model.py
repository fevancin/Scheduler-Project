import pyomo.environ as pyo
from src.common.custom_types import MasterInstance, PatientName, ServiceName, DayName, TimeSlot, CareUnitName, FinalResult
from src.common.custom_types import PatientServiceOperatorTimeSlot, PatientServiceWindow, PatientService, Window

def get_monolithic_model(instance: MasterInstance, additional_info) -> pyo.ConcreteModel:

    model = pyo.ConcreteModel()

    # INDICI ###################################################################

    # Indici nella forma (p, d)
    pat_days_index = set()

    max_span: dict[DayName, TimeSlot] = {}
    for day_name, day in instance.days.items():
        min_time_slot = min([o.start for o in day.operators.values()])
        max_time_slot = max([o.start + o.duration for o in day.operators.values()])
        max_span[day_name] = max_time_slot - min_time_slot
    
    max_time: dict[DayName, dict[CareUnitName, int]] = {}
    for day_name, day in instance.days.items():
        max_time[day_name] = {}
        for care_unit_name, care_unit in day.care_units.items():
            max_time[day_name][care_unit_name] = max(operator.end for operator in care_unit.values()) + 1

    # Insieme di quadruple (p, s, start, end) per ogni finestra
    window_index = set()

    # Tuple (p, s, d, o) per ogni giorno che può potenzialmente avere (p, s)
    do_index = set()

    for patient_name, patient in instance.patients.items():
        for service_name, windows in patient.requests.items():
            care_unit_name = instance.services[service_name].care_unit_name
            for window in windows:
                
                window_index.add((patient_name, service_name, window.start, window.end))
                
                for day_name in range(window.start, window.end + 1):
                    for operator_name in instance.days[day_name].care_units[care_unit_name].keys():
                        do_index.add((patient_name, service_name, day_name, operator_name))
                        pat_days_index.add((patient_name, day_name))

    window_index = list(window_index)

    patient_overlap_index = set()
    for i in range(len(window_index) - 1):

        p, s, ws, we = window_index[i]
        care_unit_name = instance.services[s].care_unit_name

        for j in range(i + 1, len(window_index)):

            pp, ss, wws, wwe = window_index[j]

            if p != pp:
                continue
            
            if (ws <= wws and we >= wws) or (wws <= ws and wwe >= ws):
                wwws = max(ws, wws)
                wwwe = min(we, wwe)

                for d in range(wwws, wwwe + 1):
                    patient_overlap_index.add((p, s, ws, we, ss, wws, wwe, d))

    operator_overlap_index = set()
    for i in range(len(window_index) - 1):

        p, s, ws, we = window_index[i]
        care_unit_name = instance.services[s].care_unit_name

        for j in range(i + 1, len(window_index)):

            pp, ss, wws, wwe = window_index[j]

            if care_unit_name != instance.services[ss].care_unit_name:
                continue

            if (ws <= wws and we >= wws) or (wws <= ws and wwe >= ws):
                wwws = max(ws, wws)
                wwwe = min(we, wwe)

                for d in range(wwws, wwwe + 1):
                    for o in instance.days[d].care_units[care_unit_name].keys():
                        operator_overlap_index.add((p, s, ws, we, pp, ss, wws, wwe, o, d))

    model.window_index = pyo.Set(initialize=sorted(window_index)) # type: ignore
    model.do_index = pyo.Set(initialize=sorted(do_index)) # type: ignore
    model.pat_days_index = pyo.Set(initialize=sorted(pat_days_index)) # type: ignore
    model.patient_overlap_index = pyo.Set(initialize=sorted(patient_overlap_index)) # type: ignore
    model.operator_overlap_index = pyo.Set(initialize=sorted(operator_overlap_index)) # type: ignore

    del window_index, do_index, patient_overlap_index, operator_overlap_index

    # VARIABILI ################################################################

    # Variabili decisionali che specificano quando ogni servizio è programmato

    model.time = pyo.Var(model.window_index, domain=pyo.NonNegativeIntegers) # type: ignore
    model.do = pyo.Var(model.do_index, domain=pyo.Binary) # type: ignore
    model.patient_overlap = pyo.Var(model.patient_overlap_index, domain=pyo.Binary) # type: ignore
    model.operator_overlap_1 = pyo.Var(model.operator_overlap_index, domain=pyo.Binary) # type: ignore
    model.operator_overlap_2 = pyo.Var(model.operator_overlap_index, domain=pyo.Binary) # type: ignore

    # VINCOLI ##################################################################

    # Se una finestra è soddisfatta, è soddisfatta in un unico giorno interno
    # alla sua finestra
    @model.Constraint(model.window_index) # type: ignore
    def respect_window(model, p, s, start, end):
        return pyo.quicksum(model.do[pp, ss, d, o] for pp, ss, d, o in model.do_index if p == pp and s == ss and d >= start and d <= end) <= 1

    # I tempi di inizio e fine di ogni richiesta inserita devono rispettare il
    # turno dell'operatore che la soddisfa
    @model.Constraint(model.window_index) # type: ignore
    def link_time_to_do_variables(model, p, s, start, end):
        care_unit_name = instance.services[s].care_unit_name
        return pyo.quicksum(model.do[pp, ss, d, o] * (instance.days[d].care_units[care_unit_name][o].start + 1) for pp, ss, d, o in model.do_index if p == pp and s == ss and d >= start and d <= end) <= model.time[p, s, start, end]
    @model.Constraint(model.window_index) # type: ignore
    def link_do_to_time_variables(model, p, s, start, end):
        care_unit_name = instance.services[s].care_unit_name
        return model.time[p, s, start, end] <= pyo.quicksum(model.do[pp, ss, d, o] * (instance.days[d].care_units[care_unit_name][o].start + instance.days[d].care_units[care_unit_name][o].duration - instance.services[s].duration + 1) for pp, ss, d, o in model.do_index if p == pp and s == ss and d >= start and d <= end)

    # Disgiunzione dei servizi dello stesso paziente
    @model.Constraint(model.patient_overlap_index) # type: ignore
    def patient_not_overlap_1(model, p, s, ws, we, ss, wws, wwe, d):
        return model.time[p, s, ws, we] + instance.services[s].duration * pyo.quicksum(model.do[ppp, sss, ddd, ooo] for ppp, sss, ddd, ooo in model.do_index if p == ppp and s == sss and ddd >= ws and ddd <= we) <= model.time[p, ss, wws, wwe] + (1 - model.patient_overlap[p, s, ws, we, ss, wws, wwe, d]) * max_time[d][instance.services[s].care_unit_name]
    @model.Constraint(model.patient_overlap_index) # type: ignore
    def patient_not_overlap_2(model, p, s, ws, we, ss, wws, wwe, d):
        return model.time[p, ss, wws, wwe] + instance.services[ss].duration * pyo.quicksum(model.do[ppp, sss, ddd, ooo] for ppp, sss, ddd, ooo in model.do_index if p == ppp and ss == sss and ddd >= wws and ddd <= wwe) <= model.time[p, s, ws, we] + (model.patient_overlap[p, s, ws, we, ss, wws, wwe, d]) * max_time[d][instance.services[ss].care_unit_name]

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
    def patient_overlap_auxiliary_constraint_1(model, p, s, ws, we, ss, wws, wwe, d):
        return model.patient_overlap[p, s, ws, we, ss, wws, wwe, d] <= pyo.quicksum(model.do[ppp, sss, ddd, ooo] for ppp, sss, ddd, ooo in model.do_index if p == ppp and ss == sss and ddd >= wws and ddd <= wwe)
    @model.Constraint(model.patient_overlap_index) # type: ignore
    def patient_overlap_auxiliary_constraint_2(model, p, s, ws, we, ss, wws, wwe, d):
        return pyo.quicksum(model.do[ppp, sss, ddd, ooo] for ppp, sss, ddd, ooo in model.do_index if p == ppp and ss == sss and ddd >= wws and ddd <= wwe) - pyo.quicksum(model.do[ppp, sss, ddd, ooo] for ppp, sss, ddd, ooo in model.do_index if p == ppp and s == sss and ddd >= ws and ddd <= we) <= model.patient_overlap[p, s, ws, we, ss, wws, wwe, d]

    # Disgiunzione dei servizi dello stesso operatore
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_not_overlap_1(model, p, s, ws, we, pp, ss, wws, wwe, o, d):
        return model.time[p, s, ws, we] + instance.services[s].duration * model.do[p, s, d, o] <= model.time[pp, ss, wws, wwe] + (1 - model.operator_overlap_1[p, s, ws, we, pp, ss, wws, wwe, o, d]) * max_time[d][instance.services[s].care_unit_name]
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_not_overlap_2(model, p, s, ws, we, pp, ss, wws, wwe, o, d):
        return model.time[pp, ss, wws, wwe] + instance.services[ss].duration * model.do[pp, ss, d, o] <= model.time[p, s, ws, we] + (1 - model.operator_overlap_2[p, s, ws, we, pp, ss, wws, wwe, o, d]) * max_time[d][instance.services[s].care_unit_name]

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
    def operator_overlap_auxiliary_constraint_1(model, p, s, ws, we, pp, ss, wws, wwe, o, d):
        return model.do[p, s, d, o] + model.do[pp, ss, d, o] - 1 <= model.operator_overlap_1[p, s, ws, we, pp, ss, wws, wwe, o, d] + model.operator_overlap_2[p, s, ws, we, pp, ss, wws, wwe, o, d]
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_overlap_auxiliary_constraint_2(model, p, s, ws, we, pp, ss, wws, wwe, o, d):
        return model.do[p, s, d, o] >= model.operator_overlap_1[p, s, ws, we, pp, ss, wws, wwe, o, d] + model.operator_overlap_2[p, s, ws, we, pp, ss, wws, wwe, o, d]
    @model.Constraint(model.operator_overlap_index) # type: ignore
    def operator_overlap_auxiliary_constraint_3(model, p, s, ws, we, pp, ss, wws, wwe, o, d):
        return model.do[pp, ss, d, o] >= model.operator_overlap_1[p, s, ws, we, pp, ss, wws, wwe, o, d] + model.operator_overlap_2[p, s, ws, we, pp, ss, wws, wwe, o, d]

    if 'use_redundant_operator_cut' in additional_info:

        # Tutte le coppie (day, operator)
        model.day_operators = pyo.Set(initialize=sorted((d, o) for d, day in instance.days.items() for o in day.operators.keys())) # type: ignore

        # La durata totale dei servizi programmati per ogni operatore non può
        # superare la durata di quest'ultimo
        @model.Constraint(model.day_operators) # type: ignore
        def respect_operator_duration(model, d, o):

            operator_duration = instance.days[d].operators[o].duration
            
            tuples_affected: list[tuple[PatientName, ServiceName]] = [(p, s) for p, s, dd, oo in model.do_index if d == dd and o == oo]
            if len(tuples_affected) == 0:
                return pyo.Constraint.Skip
            
            if sum(instance.services[s].duration for _, s in tuples_affected) <= operator_duration:
                return pyo.Constraint.Skip

            return pyo.quicksum(model.do[p, s, d, o] * instance.services[s].duration for p, s in tuples_affected) <= operator_duration

    if 'use_redundant_patient_cut' in additional_info:

        # Non è possibile inserire richieste dello stesso paziente la cui durata
        # totale eccede gli slot temporali di quel giorno
        @model.Constraint(model.pat_days_index) # type: ignore
        def patient_total_duration(model, p, d):
            
            tuples_affected = [(s, o) for pp, s, dd, o in model.do_index if pp == p and dd == d]
            if len(tuples_affected) == 0:
                return pyo.Constraint.Skip
            if sum(instance.services[s].duration for s, _ in tuples_affected) <= max_span[d]:
                return pyo.Constraint.Skip
            
            return pyo.quicksum(model.do[p, s, d, o] * instance.services[s].duration for s, o in tuples_affected) <= max_span[d]

    # FUNZIONE OBIETTIVO #######################################################

    # L'obiettivo è massimizzare la durata delle richieste svolte, pesate per la
    # priorità dei pazienti

    if 'minimize_hospital_accesses' in additional_info:
        
        model.pat_uses_day = pyo.Var(model.pat_days_index, domain=pyo.Binary) # type: ignore
        
        model.psd_index = pyo.Set(initialize=sorted((p, s, d) for p, s, d, _ in model.do_index)) # type: ignore

        @model.Constraint(model.psd_index) # type: ignore
        def link_do_to_pat_uses_day_variables(model, p, s, d):
            return pyo.quicksum(model.do[p, s, d, o] for pp, ss, dd, o in model.do_index if p == pp and s == ss and d == dd) <= model.pat_uses_day[p, d]
    
        @model.Objective(sense=pyo.maximize) # type: ignore
        def objective_function(model): # type: ignore
            return (pyo.quicksum(model.do[p, s, d, o] * instance.services[s].duration * instance.patients[p].priority for p, s, d, o in model.do_index)
                    - 1.0 / len(model.pat_days_index) * pyo.quicksum(model.pat_uses_day[p, d] for p, d in model.pat_days_index))
    else:
        @model.Objective(sense=pyo.maximize) # type: ignore
        def objective_function(model):
            return pyo.quicksum(model.do[p, s, d, o] * instance.services[s].duration * instance.patients[p].priority for p, s, d, o in model.do_index)

    return model # type: ignore


def get_result_from_monolithic_model(model) -> FinalResult:

    result = FinalResult()

    for p, s, d, o in model.do_index: # type: ignore
        if pyo.value(model.do[p, s, d, o]) < 0.5: # type: ignore
            continue

        if d not in result.scheduled:
            result.scheduled[d] = []

        t = None
        
        for pp, ss, ws, we in model.window_index:
            if p == pp and s == ss and ws <= d and we >= d:
                t = int(pyo.value(model.time[p, s, ws, we])) - 1 # type: ignore
                break
        
        if t is not None:
            result.scheduled[d].append(PatientServiceOperatorTimeSlot(p, s, o, t))

    for p, s, ws, we in model.window_index: # type: ignore
        if pyo.value(model.time[p, s, ws, we]) < 0.1: # type: ignore
            result.rejected.append(PatientServiceWindow(p, s, Window(ws, we)))

    # Ordina le chiavi
    for day_name in result.scheduled.keys():
        result.scheduled[day_name].sort(key=lambda r: (r.patient_name, r.service_name, r.operator_name, r.time_slot))
    result.rejected.sort(key=lambda r: (r.patient_name, r.service_name))

    return result