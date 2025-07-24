import random

def generate_master_instance(config):
    '''Funzione che ritorna un'istanza del problema master con le
    caratteristiche definite dalla configurazione fornita.'''

    instance = {
        'days': {},
        'services': {},
        'patients': {}
    }

    # Generazione dei giorni
    for day_index in range(1, config['day_number'] + 1):
        
        instance['days'][f'{day_index}'] = {}
        
        # Gli operatori sono numerati ripartendo da 0 ogni giorno (e non da ogni
        # unità di cura)
        operator_index = 0

        # Generazione delle unità di cura
        for care_unit_index in range(config['care_unit_number']):
            
            instance['days'][f'{day_index}'][f'cu{care_unit_index:02}'] = {}
            
            # Generazione degli operatori
            for _ in range(config['operator_number']):
                
                instance['days'][f'{day_index}'][f'cu{care_unit_index:02}'][f'op{operator_index:02}'] = {
                    'start': 0,
                    'duration': config['operator_duration']
                }

                operator_index += 1

    # Generazione dei servizi
    care_unit_number = config['care_unit_number']
    for service_index in range(config['service_number']):
        
        instance['services'][f'srv{service_index:02}'] = {

            # Le unità di cura sono scelte a rotazione per ottenere la migliore
            # distribuzione di richieste
            'care_unit': f'cu{(service_index % care_unit_number):02}',

            # La durata è scelta da una distribuzione triangolare
            'duration': int(random.triangular(
                low=config['service_duration']['min'],
                high=config['service_duration']['max'],
                mode=config['service_duration']['mode']))
        }

    # Generazione dei pazienti, per ora senza richieste
    for patient_index in range(config['patient_number']):
        instance['patients'][f'pat{patient_index:03}'] = {
            'priority': 1,
            'requests': {}
        }
    
    patient_names = set(pat for pat in instance['patients'].keys())
    care_unit_names = set()
    for day in instance['days'].values():
        care_unit_names.update(day.keys())
    
    # Minimo e massimo giorno dell'istanza
    min_day = min(int(day_name) for day_name in instance['days'].keys())
    max_day = max(int(day_name) for day_name in instance['days'].keys())

    # Contatori dei time slot totali rimanenti liberi di ogni unità di cura in
    # tutti i giorni. Questi valori saranno aggiornati dopo l'aggiunta di ogni
    # richiesta e permettono di controllare la loro saturazione
    care_unit_remaining_duration = {cu: 0 for cu in care_unit_names}
    for day in instance['days'].values():
        for care_unit_name, care_unit in day.items():
            care_unit_remaining_duration[care_unit_name] += sum(o['duration'] for o in care_unit.values())

    # Numero totale di time slot da riempire con richieste. Questo valore è
    # scalato con la proprietà 'request_over_disponibility_ratio' per ottenere
    # sovrassaturazione
    total_remaining_duration = sum(d for d in care_unit_remaining_duration.values())
    total_remaining_duration = int(total_remaining_duration * config['request_over_disponibility_ratio'])
    
    # Divisione dei servizi  per unità di cura in liste, per una più veloce
    # selezione al bisogno
    service_names_by_care_unit = {cu: [] for cu in care_unit_names}
    for service_name, service in instance['services'].items():
        care_unit_name = service['care_unit']
        service_names_by_care_unit[care_unit_name].append(service_name)

    # Durate totali dei servizi assegnati ad ogni paziente, per la garanzia di
    # un'equa suddivisione delle richieste fra di loro
    patient_total_duration = {pat: 0 for pat in patient_names}

    # Genera richieste finchè il totale non è raggiunto
    while total_remaining_duration > 0:

        # Selezione dell'unità di cura più scarica
        care_unit_name = max([cu for cu in care_unit_names], key=lambda cu: care_unit_remaining_duration[cu])
    
        # Selezione di un servizio di questa unità di cura
        service_name = random.choice(service_names_by_care_unit[care_unit_name])
        service = instance['services'][service_name]
        service_duration = service['duration']

        # Generazione e posizionamento della finestra in maniera tale da essere
        # completamente interna ai giorni dell'istanza
        window_size = random.randint(1, min(config['window_max_size'], max_day - min_day))
        start_day = random.randint(min_day, max_day - window_size)
        end_day = start_day + window_size

        # Scelta del paziente meno carico finora
        patient_name = min([pat for pat in patient_names], key=lambda pat: patient_total_duration[pat])
        
        # Aggiunta della richiesta al paziente
        if service_name not in instance['patients'][patient_name]['requests']:
            instance['patients'][patient_name]['requests'][service_name] = []
        instance['patients'][patient_name]['requests'][service_name].append([start_day, end_day])
        
        # Aggiornamento dei contatori
        patient_total_duration[patient_name] += service_duration
        care_unit_remaining_duration[care_unit_name] -= service_duration
        total_remaining_duration -= service_duration
    
    # Rimozione di eventuali pazienti senza richieste
    empty_patient_names = []
    for patient_name, patient in instance['patients'].items():
        if len(patient['requests']) == 0:
            empty_patient_names.append(patient_name)
    for patient_name in empty_patient_names:
        del instance['patients'][patient_name]
    
    # Eventuale copia delle finestre all'interno dello stesso paziente per
    # ottenere duplicazione delle stesse con probabilità specificata da
    # 'same_window_percentage'
    if config['same_window_percentage'] != 0.0:
        for patient in instance['patients'].values():
            
            # Non è possibile copiare delle finestre se il paziente richiede un
            # solo un servizio
            service_names = list(patient['requests'].keys())
            if len(service_names) < 2:
                continue
            
            # Scorri ogni finestra dei servizi a parte il primo
            for service_index, service_name in enumerate(service_names[1:]):
                for window_index in range(len(patient['requests'][service_name])):
            
                    # Se la finestra è scelta, sostituiscila con una di un
                    # servizio precedente
                    if random.random() < config['same_window_percentage']:
                        other_service_name = random.choice(service_names[:service_index + 1])
                        if other_service_name == service_name:
                            continue

                        # Selezione e sostituzione con una finestra precedente
                        other_window = random.choice(patient['requests'][other_service_name])
                        patient['requests'][service_name][window_index] = other_window

    # Ordinamento dei nomi delle richieste e delle finestre al loro interno
    for patient in instance['patients'].values():
        patient['requests'] = {k: v for k, v in sorted(patient['requests'].items())}
        for windows in patient['requests'].values():
            windows.sort(key=lambda v: (v[0], v[1]))

    return instance