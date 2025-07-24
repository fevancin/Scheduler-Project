import random

def generate_fat_subproblem_requests(config, instance):
    '''Funzione che aggiunge richieste all'istanza del sottoproblema. Queste
    richieste contengono i nomi degli operatori.'''

    # Nomi degli operatori da cui attingere
    operator_names = set()
    for care_unit in instance['day'].values():
        operator_names.update(care_unit.keys())
    
    # Nomi delle unità di cura di ogni operatore
    operator_care_unit = {}

    # Time slot rimenenti ad ogni operatore, per riuscire a saturarli in maniera
    # omogenea
    operator_remaining_duration = {op: 0 for op in operator_names}

    for care_unit_name, care_unit in instance['day'].items():
        for operator_name, operator in care_unit.items():
            operator_care_unit[operator_name] = care_unit_name
            operator_remaining_duration[operator_name] = operator['duration']

    # Totale dei time slot liberi rimanenti nell'istanza
    total_remaining_duration = sum(d for d in operator_remaining_duration.values())

    # Primo, ultimo e span totale degli intervalli degli operatori
    first_time_slot = min(o['start'] for cu in instance['day'].values() for o in cu.values())
    last_time_slot = max(o['start'] + o['duration'] for cu in instance['day'].values() for o in cu.values())
    max_time_slot_span = last_time_slot - first_time_slot

    # Nomi dei pazienti e loro durata rimanente, per non sovrassaturare nessuno
    patient_names = set(pat for pat in instance['patients'].keys())
    patient_remaining_duration = {pat: max_time_slot_span for pat in patient_names}

    # Ogni richiesta possiederà il proprio servizio senza ripetizioni,
    # indicizzato in maniera crescente
    service_index = 0

    # Genera richieste finchè l'istanza non è esattamente satura
    while total_remaining_duration > 0:

        # Selezione dell'operatore più scarico
        operator_name = max([op for op in operator_names], key=lambda op: operator_remaining_duration[op])
    
        # Genearazione del servizio con durata decisa da una distribuzione
        # triangolare
        service_name = f'srv{service_index:02}'
        service_index += 1
        service_duration = int(random.triangular(
            low=config['service_duration']['min'],
            high=config['service_duration']['max'],
            mode=config['service_duration']['mode']))
        
        # Eventuale tranciatura se la durata del servizio eccede quella
        # rimanente del suo operatore
        if service_duration > operator_remaining_duration[operator_name]:
            service_duration = operator_remaining_duration[operator_name]

        # Aggiunta del servizio nell'istanza
        instance['services'][service_name] = {
            'care_unit': operator_care_unit[operator_name],
            'duration': service_duration
        }

        # Selezione del paziente più scarico
        patient_name = max([pat for pat in patient_names], key=lambda pat: patient_remaining_duration[pat])
        
        # Aggiunta della richiesta nell'istanza
        instance['patients'][patient_name]['requests'].append({
            'service': service_name,
            'operator': operator_name
        })
        
        # Aggiornamento dei contatori
        patient_remaining_duration[patient_name] -= service_duration
        operator_remaining_duration[operator_name] -= service_duration
        total_remaining_duration -= service_duration


def generate_slim_subproblem_requests(config, instance):
    '''Funzione che aggiunge richieste all'istanza del sottoproblema. Queste
    richieste non contengono i nomi degli operatori.'''
    
    care_unit_names = set(instance['day'].keys())

    # Time slot rimanenti di ogni unità di cura. Questi valori permettono di
    # saturare esattamente ognuna di queste
    care_unit_remaining_duration = {cu: 0 for cu in care_unit_names}
    for care_unit_name, care_unit in instance['day'].items():
        care_unit_remaining_duration[care_unit_name] += sum(o['duration'] for o in care_unit.values())

    # Totale dei time slot liberi rimanenti nell'istanza
    total_remaining_duration = sum(d for d in care_unit_remaining_duration.values())

    # Primo, ultimo e span totale degli intervalli degli operatori
    first_time_slot = min(o['start'] for cu in instance['day'].values() for o in cu.values())
    last_time_slot = max(o['start'] + o['duration'] for cu in instance['day'].values() for o in cu.values())
    max_time_slot_span = last_time_slot - first_time_slot

    # Nomi dei pazienti e loro durata rimanente, per non sovrassaturare nessuno
    patient_names = set(pat for pat in instance['patients'].keys())
    patient_remaining_duration = {pat: max_time_slot_span for pat in patient_names}

    # Ogni richiesta possiederà il proprio servizio senza ripetizioni,
    # indicizzato in maniera crescente
    service_index = 0

    # Genera richieste finchè l'istanza non è esattamente satura
    while total_remaining_duration > 0:

        # Scelta dell'unità di cura più scarica
        care_unit_name = max([cu for cu in care_unit_names], key=lambda cu: care_unit_remaining_duration[cu])
    
        # Genearazione del servizio con durata decisa da una distribuzione
        # triangolare
        service_name = f'srv{service_index:02}'
        service_index += 1
        service_duration = int(random.triangular(
            low=config['service_duration']['min'],
            high=config['service_duration']['max'],
            mode=config['service_duration']['mode']))
        
        # Eventuale tranciatura se la durata del servizio eccede quella
        # rimanente della sua unità di cura
        if service_duration > care_unit_remaining_duration[care_unit_name]:
            service_duration = care_unit_remaining_duration[care_unit_name]

        # Aggiunta del servizio nell'istanza
        instance['services'][service_name] = {
            'care_unit': care_unit_name,
            'duration': service_duration
        }

        # Selezione del paziente più scarico
        patient_name = max([pat for pat in patient_names], key=lambda pat: patient_remaining_duration[pat])
        instance['patients'][patient_name]['requests'].append(service_name)
        
        # Aggiornamento dei contatori
        patient_remaining_duration[patient_name] -= service_duration
        care_unit_remaining_duration[care_unit_name] -= service_duration
        total_remaining_duration -= service_duration


def generate_subproblem_instance(config):
    '''Funzione che ritorna un'istanza del sottoproblema con le caratteristiche
    definite dalla configurazione fornita.'''

    instance = {
        'day': {},
        'services': {},
        'patients': {}
    }

    # Generazione delle unità di cura
    operator_index = 0
    for care_unit_index in range(config['care_unit_number']):
        
        instance['day'][f'cu{care_unit_index:02}'] = {}
        
        # Generazione degli operatori
        for _ in range(config['operator_number']):
            instance['day'][f'cu{care_unit_index:02}'][f'op{operator_index:02}'] = {
                'start': 0,
                'duration': config['operator_duration']
            }

            operator_index += 1

    # Generazione dei pazienti, per ora senza richieste
    for patient_index in range(config['patient_number']):
        instance['patients'][f'pat{patient_index:03}'] = {
            'priority': 1,
            'requests': []
        }
    
    # Generazione delle richieste
    if config['type'] == 'fat':
        generate_fat_subproblem_requests(config, instance)
    else:
        generate_slim_subproblem_requests(config, instance)

    # Rimozione di eventuali pazienti senza richieste
    empty_patient_names = []
    for patient_name, patient in instance['patients'].items():
        if len(patient['requests']) == 0:
            empty_patient_names.append(patient_name)
    for patient_name in empty_patient_names:
        del instance['patients'][patient_name]
    
    # Ordinamento dei nomi delle richieste
    for patient in instance['patients'].values():
        if config['type'] == 'fat':
            patient['requests'].sort(lambda v: v['service'])
        else:
            patient['requests'].sort()

    return instance