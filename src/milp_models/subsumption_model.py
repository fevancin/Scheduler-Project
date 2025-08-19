import pyomo.environ as pyo

from src.common.custom_types import Operator, OperatorName


def get_subsumption_model(big_operators: dict[OperatorName, Operator], small_operators: dict[OperatorName, Operator]) -> pyo.ConcreteModel:

    choose_index = set()
    for big_operator_name, big_operator in big_operators.items():
        for small_operator_name, small_operator in small_operators.items():
            if small_operator.start >= big_operator.start and small_operator.start + small_operator.duration <= big_operator.start + big_operator.duration:
                choose_index.add((small_operator_name, big_operator_name))

    consistency_index = set()
    for on, o in small_operators.items():
        for oon, oo in small_operators.items():
            if on == oon:
                continue
            if ((o.start <= oo.start and o.start + o.duration >= oo.start) or
                (oo.start <= o.start and oo.start + oo.duration >= o.start)):
                for big_on in big_operators.keys():
                    if (on, big_on) in choose_index and (oon, big_on) in choose_index:
                        consistency_index.add((on, oon, big_on))

    model = pyo.ConcreteModel()

    model.choose_index = pyo.Set(initialize=sorted(choose_index)) # type: ignore
    model.small_operators_index = pyo.Set(initialize=sorted(small_operators.keys())) # type: ignore
    model.big_operators = pyo.Set(initialize=sorted(big_operators.keys())) # type: ignore
    model.consistency_index = pyo.Set(initialize=sorted(consistency_index)) # type: ignore

    model.choose = pyo.Var(model.choose_index, domain=pyo.Binary) # type: ignore

    @model.Constraint(model.small_operators_index) # type: ignore
    def max_one_choice_per_small_operators(model, small_o):
        return pyo.quicksum(model.choose[o, big_o] for o, big_o in model.choose_index if o == small_o) <= 1
    
    @model.Constraint(model.consistency_index) # type: ignore
    def maintain_consistency(model, o, oo, big_o):
        return model.choose[o, big_o] + model.choose[oo, big_o] <= 1

    @model.Objective(sense=pyo.maximize) # type: ignore
    def objective_function(model):
        return pyo.quicksum(model.choose[a, b] for a, b in model.choose_index)

    return model # type: ignore


def subsumption_model_has_solution(model, result) -> bool:
    
    if (result.solver.status != pyo.SolverStatus.ok) or (result.solver.termination_condition != pyo.TerminationCondition.optimal):
        return False
    
    for small_operator_name in model.small_operators_index:
        
        is_operator_assigned = False
        
        for o, oo in model.choose_index:
            if o == small_operator_name and pyo.value(model.choose[o, oo]) > 0.5: # type: ignore
                is_operator_assigned = True
                break
        
        if not is_operator_assigned:
            return False
    
    return True
