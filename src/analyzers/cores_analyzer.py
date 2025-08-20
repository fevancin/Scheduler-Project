from src.common.custom_types import MasterInstance, FatCore, SlimCore, DayName, TimeSlot

def analyze_cores(instance: MasterInstance, cores: list[FatCore] | list[SlimCore]) -> dict[str, int | float]:

    cores_number = len(cores)
    
    core_size = [len(core.components) for core in cores]
    core_reason_sizes = [len(core.reason) for core in cores]

    patient_number_per_core = [len(set(component.patient_name for component in core.components)) for core in cores]
    care_unit_number_per_core = [len(set(instance.services[component.service_name].care_unit_name for component in core.components)) for core in cores]
    
    total_operator_duration_per_day: dict[DayName, TimeSlot] = {day_name: sum(operator.duration for operator in day.operators.values()) for day_name, day in instance.days.items()}
    
    total_duration_per_core: list[TimeSlot] = []
    core_day_saturation_percentage: list[float] = []
    
    for core in cores:
        total_core_duration = sum(instance.services[component.service_name].duration for component in core.components)
        total_duration_per_core.append(total_core_duration)
        core_day_saturation_percentage.append(total_core_duration / total_operator_duration_per_day[core.day])

    analysis = {
        'core_number': cores_number,
        
        'min_core_size': min(core_size),
        'max_core_size': max(core_size),
        'average_core_size': sum(core_size) / cores_number,
        
        'min_core_reason_size': min(core_reason_sizes),
        'max_core_reason_size': max(core_reason_sizes),
        'average_core_reason_size': sum(core_reason_sizes) / cores_number,
        
        'min_patient_number_per_core': min(patient_number_per_core),
        'max_patient_number_per_core': max(patient_number_per_core),
        'average_patient_number_per_core': sum(patient_number_per_core) / cores_number,
        
        'min_care_unit_number_per_core': min(care_unit_number_per_core),
        'max_care_unit_number_per_core': max(care_unit_number_per_core),
        'average_care_unit_number_per_core': sum(care_unit_number_per_core) / cores_number,
        
        'min_total_duration_per_core': min(total_duration_per_core),
        'max_total_duration_per_core': max(total_duration_per_core),
        'average_total_duration_per_core': sum(total_duration_per_core) / cores_number,
        
        'min_core_day_saturation_percentage': min(core_day_saturation_percentage),
        'max_core_day_saturation_percentage': max(core_day_saturation_percentage),
        'average_core_day_saturation_percentage': sum(core_day_saturation_percentage) / cores_number
    }

    if isinstance(cores, FatCore):

        operator_number_per_core = [len(set(component.operator_name for component in core.components)) for core in cores] # type: ignore
        
        analysis.update({
            'min_operator_number_per_core': min(operator_number_per_core),
            'max_operator_number_per_core': max(operator_number_per_core),
            'average_operator_number_per_core': sum(operator_number_per_core) / cores_number
        })

    return analysis