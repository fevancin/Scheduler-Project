# SCHEDULER PROJECT

The project comprend four phases:
- generation of input (`generator.py`)
- iterative solving (`solver.py`)
- analysis of the results (`analyzer.py`)
- plot of the results (`plotter.py`)

## Command examples

### Master instance generator:
`python generator.py -c configs/master_generator_config.yaml -o instances --overwrite`

### Subproblem instance generator: 
`python generator.py -c configs/subproblem_generator_config.yaml -o instances --overwrite`

### Iterative solver:
`python solver.py -c configs/solver_config.yaml -i instances -o results --overwrite`

### Results analizer:
`python analyzer.py -c configs/analyzer_config.yaml -i results`

### Results plotter:
`python plotter.py all -c configs/plotter_config.yaml -i results`

### Single instance result plotter:
`python plotter.py instance -i ... -o ...`

## Analysis data

Those are all the fields extracted from instances and results

### Master analysis
- day_number
- care_unit_total_number
- operator_total_number
- patient_number
- total_window_number
- average_care_unit_per_day
- min_care_unit_duration
- max_care_unit_duration
- average_care_unit_duration
- min_operator_duration
- max_operator_duration
- average_operator_duration
- min_service_duration
- max_service_duration
- average_service_duration
- operator_total_duration
- total_time_slots_requested
- request_over_disponibility_ratio
- min_window_size
- max_window_size
- average_window_size
- min_patient_request_number
- max_patient_request_number
- average_patient_request_number
- total_overlapping_windows
- min_windows_overapping_per_patient
- max_windows_overapping_per_patient
- average_windows_overapping_per_patient
- min_day_number_used_per_patient
- max_day_number_used_per_patient
- average_day_number_used_per_patient

### Master result
- day_number
- patient_number
- total_scheduled_request_number
- total_scheduled_request_duration
- total_rejected_request_number
- total_rejected_request_durationrejected
- min_scheduled_request_number_per_day
- max_scheduled_request_number_per_day
- average_scheduled_request_number_per_day
- min_scheduled_request_duration_per_day
- max_scheduled_request_duration_per_day
- average_scheduled_request_duration_per_day
- min_patients_per_day
- max_patients_per_day
- average_patients_per_day
- min_day_number_used_per_patient
- max_day_number_used_per_patient
- average_day_number_used_per_patient
- min_request_number_per_patient_same_day
- max_request_number_per_patient_same_day
- average_request_number_per_patient_same_day
- min_request_duration_per_patient_same_day
- max_request_duration_per_patient_same_day
- average_request_duration_per_patient_same_day
- min_care_unit_used_per_patient_same_day
- max_care_unit_used_per_patient_same_day
- average_care_unit_used_per_patient_same_day

If fat:
- total_operator_used_per_patient
- min_operator_used_per_patient
- max_operator_used_per_patient
- average_operator_used_per_patient
- total_patient_served_per_operator
- min_patient_served_per_operator
- max_patient_served_per_operator
- average_patient_served_per_operator

### Final result
Same than fat master results with:
- objective_value
- total_time_slots_remaining
- min_time_slots_remaining_per_day
- max_time_slots_remaining_per_day
- average_time_slots_remaining_per_day

### Subproblem instance
- care_unit_number
- operator_total_number
- patient_number
- total_request_number
- min_care_unit_duration
- max_care_unit_duration
- average_care_unit_duration
- min_operator_duration
- max_operator_duration
- average_operator_duration
- min_service_duration
- max_service_duration
- average_service_duration
- operator_total_duration
- total_time_slots_requested
- request_over_disponibility_ratio
- min_patient_request_number
- max_patient_request_number
- average_patient_request_number
- min_care_units_used_per_patient
- max_care_units_used_per_patient
- average_care_units_used_per_patient

### Subproblem result
- patient_number
- total_scheduled_request_number
- total_scheduled_request_duration
- rejected_request_number
- rejected_request_duration
- min_care_units_used_per_patient
- max_care_units_used_per_patient
- average_care_units_used_per_patient
- min_scheduled_request_duration
- max_scheduled_request_duration
- average_scheduled_request_duration
- min_request_number_per_patient
- max_request_number_per_patient
- average_request_number_per_patient
- min_request_duration_per_patient
- max_request_duration_per_patient
- average_request_duration_per_patient
- min_operator_used_per_patient
- max_operator_used_per_patient
- average_operator_used_per_patient
- min_patient_served_per_operator
- max_patient_served_per_operator
- average_patient_served_per_operator

### Cores
- core_number
- min_core_size
- max_core_size
- average_core_size
- min_core_reason_size
- max_core_reason_size
- average_core_reason_size
- min_patient_number_per_core
- max_patient_number_per_core
- average_patient_number_per_core
- min_care_unit_number_per_core
- max_care_unit_number_per_core
- average_care_unit_number_per_core
- min_total_duration_per_core
- max_total_duration_per_core
- average_total_duration_per_core
- min_core_day_saturation_percentage
- max_core_day_saturation_percentage
- average_core_day_saturation_percentage

If fat:
- min_operator_number_per_core
- max_operator_number_per_core
- average_operator_number_per_core

### Log
- status
- objective_value
- upper_bound
- gap
- root_relaxation
- time
- constraint_number
- variable_number
- presolved_constraint_number
- presolved_variable_number
- best_solution_time

bla bla bla