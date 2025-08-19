import pyomo.environ as pyo

from src.common.custom_types import SlimArc, FatArc, PatientServiceOperator

def get_max_matching_model(arcs: set[SlimArc] | set[FatArc]) -> pyo.ConcreteModel | None:

    consistency_index = set()

    # Itera ogni coppia di archi cercando tutte le combinazioni di assegnamento
    # che non rispettano la consistenza dei nomi di paziente o operatore
    arc_list = list(arcs)
    for i in range(len(arc_list) - 1):

        arc = arc_list[i]

        # Quando il core è espanso sul suo giorno esiste certamente
        # l'assegnamento degenere a->a, ma se il giorno è diverso il matching
        # potrebbe essere impossibile fin da subito
        is_vertex_assignable = False
        
        for j in range(i + 1, len(arc_list)):
            other_arc = arc_list[j]

            # Se i vertici di partenza hanno lo stesso paziente ma le
            # destinazioni no, questo assegnamento è incompatibile
            if arc[0].patient_name == other_arc[0].patient_name and arc[1].patient_name != other_arc[1].patient_name:
                consistency_index.add((arc[0], arc[1], other_arc[0], other_arc[1]))
            
            elif (isinstance(arc[0], PatientServiceOperator) and
                isinstance(arc[1], PatientServiceOperator) and
                isinstance(other_arc[0], PatientServiceOperator) and
                isinstance(other_arc[1], PatientServiceOperator)):

                # Se i vertici di partenza hanno lo stesso operatore ma le
                # destinazioni no, questo assegnamento è incompatibile
                if arc[0].operator_name == other_arc[0].operator_name and arc[1].operator_name != other_arc[1].operator_name:
                    consistency_index.add((arc[0], arc[1], other_arc[0], other_arc[1]))
            
            else:
                is_vertex_assignable = True
        
        if not is_vertex_assignable:
            print(f'{arc} is not assignable')
            return None

    model = pyo.ConcreteModel()

    model.choose_index = pyo.Set(initialize=sorted(arcs)) # type: ignore
    model.sources = pyo.Set(initialize=sorted(set(a for a, _ in arcs))) # type: ignore
    model.destinations = pyo.Set(initialize=sorted(set(b for _, b in arcs))) # type: ignore
    model.consistency_index = pyo.Set(initialize=sorted(consistency_index)) # type: ignore

    model.choose = pyo.Var(model.choose_index, domain=pyo.Binary) # type: ignore

    @model.Constraint(model.sources) # type: ignore
    def max_one_choice_per_source(model, a):
        return pyo.quicksum(model.choose[aa, b] for aa, b in model.choose_index if a == aa) <= 1
    
    @model.Constraint(model.destinations) # type: ignore
    def max_one_choice_per_destination(model, b):
        return pyo.quicksum(model.choose[a, bb] for a, bb in model.choose_index if b == bb) <= 1

    @model.Constraint(model.consistency_index) # type: ignore
    def force_same_name_consistency(model, a, b, c, d):
        return model.choose[a, b] + model.choose[c, d] <= 1

    model.cuts = pyo.ConstraintList() # type: ignore

    @model.Objective(sense=pyo.maximize) # type: ignore
    def objective_function(model):
        return pyo.quicksum(model.choose[a, b] for a, b in model.choose_index)

    return model # type: ignore


def ban_matching_from_model(
        model: pyo.ConcreteModel,
        cut: set[SlimArc] | set[FatArc]):
    """Funzioen che aggiunge un taglio che vieta il ripresentarsi della medesima
    soluzione data dagli archi forniti in input."""

    model.cuts.add(expr=pyo.quicksum(model.choose[a, b] for a, b in cut) <= len(cut) - 1) # type: ignore


def get_matching_from_max_matching_model(model, result) -> set[SlimArc] | set[FatArc]:

    matching: set[SlimArc] | set[FatArc] = set()

    if (result.solver.status != pyo.SolverStatus.ok) or (result.solver.termination_condition != pyo.TerminationCondition.optimal):
        return matching

    for a, b in model.choose_index:
        if pyo.value(model.choose[a, b]) > 0.5: # type: ignore
            matching.add((a, b))

    return matching