from __future__ import annotations
from dataclasses import dataclass, field

# TIPI ATOMICI #################################################################

type CareUnitName = str
type ServiceName = str
type PatientName = str
type OperatorName = str
type TimeSlot = int
type DayName = int
type IterationName = int

# STRUTTURE DATI BASICHE #######################################################

@dataclass
class Service:
    care_unit_name: CareUnitName
    duration: TimeSlot

@dataclass
class Operator:
    care_unit_name: CareUnitName
    start: TimeSlot
    duration: TimeSlot

    @property
    def end(self) -> TimeSlot:
        return self.start + self.duration

@dataclass
class Day:
    care_units: dict[CareUnitName, dict[OperatorName, Operator]] = field(default_factory=dict)
    operators: dict[OperatorName, Operator] = field(default_factory=dict)

    def add_operator(self, operator_name: OperatorName, operator: Operator):
        
        care_unit_name = operator.care_unit_name
        if care_unit_name not in self.care_units:
            self.care_units[care_unit_name] = {}
        
        self.care_units[care_unit_name][operator_name] = operator
        self.operators[operator_name] = operator
    
    def duration(self, name: CareUnitName | OperatorName) -> TimeSlot:

        if name in self.care_units:
            return sum(operator.duration for operator in self.care_units[name].values())
        
        if name in self.operators:
            return self.operators[name].duration
        
        return 0

@dataclass(unsafe_hash=True, eq=True)
class Window:
    start: DayName
    end: DayName

    @property
    def duration(self) -> DayName:
        return self.end - self.start
    
    def contains(self, day_name: DayName) -> bool:
        return self.start <= day_name and self.end >= day_name
    
    def overlaps(self, window: Window) -> bool:
        return ((self.start <= window.start and self.end >= window.start) or
                (window.start <= self.start and window.end >= self.start))

@dataclass(unsafe_hash=True, eq=True)
class ServiceWindow:
    service_name: ServiceName
    window: Window

@dataclass(unsafe_hash=True, eq=True)
class PatientService:
    patient_name: PatientName
    service_name: ServiceName

@dataclass(unsafe_hash=True, eq=True)
class ServiceOperator:
    service_name: ServiceName
    operator_name: OperatorName

@dataclass(unsafe_hash=True, eq=True)
class PatientServiceWindow(PatientService):
    window: Window

@dataclass(unsafe_hash=True, eq=True)
class PatientServiceOperator(PatientService):
    operator_name: OperatorName

@dataclass(unsafe_hash=True, eq=True)
class PatientServiceOperatorTimeSlot(PatientServiceOperator):
    time_slot: TimeSlot

@dataclass(unsafe_hash=True, eq=True)
class IterationDay:
    iteration_name: IterationName
    day_name: DayName

type Cache = dict[PatientServiceWindow, list[IterationDay]]
type CacheMatch = dict[DayName, IterationName]

# PAZIENTE #####################################################################

@dataclass
class AbstractPatient:
    priority: int

@dataclass
class MasterPatient(AbstractPatient):
    requests: dict[ServiceName, list[Window]] = field(default_factory=dict)

    @property
    def windows(self) -> list[ServiceWindow]:
        
        merged_windows: list[ServiceWindow] = []
        for service_name, windows in self.requests.items():
            for window in windows:
                merged_windows.append(ServiceWindow(service_name, window))
        
        return merged_windows
    
    def add_request(self, service_window: ServiceWindow):
        service_name = service_window.service_name
        if service_name not in self.requests:
            self.requests[service_name] = []
        self.requests[service_name].append(service_window.window)
    
    def add_requests(self, service_windows: list[ServiceWindow]):
        for service_window in service_windows:
            self.add_request(service_window)

@dataclass
class FatSubproblemPatient(AbstractPatient):
    requests: list[ServiceOperator] = field(default_factory=list)

@dataclass
class SlimSubproblemPatient(AbstractPatient):
    requests: list[ServiceName] = field(default_factory=list)

# ISTANZE ######################################################################

@dataclass
class MasterInstance:
    days: dict[DayName, Day] = field(default_factory=dict)
    services: dict[ServiceName, Service] = field(default_factory=dict)
    patients: dict[PatientName, MasterPatient] = field(default_factory=dict)

@dataclass
class AbstractSubproblemInstance:
    day: Day = field(default_factory=Day)
    services: dict[ServiceName, Service] = field(default_factory=dict)

    @property
    def operators(self) -> dict[OperatorName, Operator]:
        return self.day.operators

    @property
    def care_units(self) -> dict[CareUnitName, dict[OperatorName, Operator]]:
        return self.day.care_units

@dataclass
class FatSubproblemInstance(AbstractSubproblemInstance):
    patients: dict[PatientName, FatSubproblemPatient] = field(default_factory=dict)

@dataclass
class SlimSubproblemInstance(AbstractSubproblemInstance):
    patients: dict[PatientName, SlimSubproblemPatient] = field(default_factory=dict)

# RISULTATI ####################################################################

@dataclass
class AbstractMasterResult:
    rejected: list[PatientServiceWindow] = field(default_factory=list)

@dataclass
class SlimMasterResult(AbstractMasterResult):
    scheduled: dict[DayName, list[PatientService]] = field(default_factory=dict)

@dataclass
class FatMasterResult(AbstractMasterResult):
    scheduled: dict[DayName, list[PatientServiceOperator]] = field(default_factory=dict)

@dataclass
class AbstractSubproblemResult:
    scheduled: list[PatientServiceOperatorTimeSlot] = field(default_factory=list)

@dataclass
class FatSubproblemResult(AbstractSubproblemResult):
    rejected: list[PatientServiceOperator] = field(default_factory=list)

@dataclass
class SlimSubproblemResult(AbstractSubproblemResult):
    rejected: list[PatientService] = field(default_factory=list)

@dataclass
class FinalResult(AbstractMasterResult):
    scheduled: dict[DayName, list[PatientServiceOperatorTimeSlot]] = field(default_factory=dict)

# CORE #########################################################################

@dataclass
class AbstractCore:
    days: list[DayName] = field(default_factory=list)

@dataclass
class SlimCore(AbstractCore):
    reason: list[PatientService] = field(default_factory=list)
    components: list[PatientService] = field(default_factory=list)

    def has_same_components(self, core: SlimCore) -> bool:
        if len(self.components) != len(core.components):
            return False
        for component in self.components:
            if component not in core.components:
                return False
        return True

@dataclass
class FatCore(AbstractCore):
    reason: list[PatientServiceOperator] = field(default_factory=list)
    components: list[PatientServiceOperator] = field(default_factory=list)

    def has_same_components(self, core: FatCore) -> bool:
        if len(self.components) != len(core.components):
            return False
        for component in self.components:
            if component not in core.components:
                return False
        return True