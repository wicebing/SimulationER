import random
import csv


class Patient:
    patient_counter = 0  # This is a class-level variable
    
    def __init__(self, arrival_time, patient_type):
        Patient.patient_counter += 1  # Increment the counter
        self.num = Patient.patient_counter  # Assign the current counter value to the patient
        
        self.arrival_time = arrival_time
        self.triage_time = None
        self.boarding_time = None
        self.departure_time = None
        self.status = 'triage'  # or 'on_board', 'departure'
        self.discharge_status = False
        self.patient_type = patient_type  # 'med' or 'trauma'
        self.boarding_blood = 30  # initial value, you can adjust this
        self.disease_blood = 100  # initial value
        self.departure_blood = 10  # initial value
        self.assigned_physician = None


class Physician:
    used_names = set()  # This is a class-level set to store used names
    
    def __init__(self, name, abilities=None):
        if name in Physician.used_names:
            raise ValueError(f"The name '{name}' is already in use. Please choose a different name.")
        self.name = name
        Physician.used_names.add(name)  # Add the name to the set of used names
        
        if abilities is None:
            self.abilities = self.default_abilities()
        else:
            self.abilities = abilities

    @staticmethod
    def default_abilities():
        abilities = {}
        hours = ["{:02d}:00-{:02d}:00".format(i, i+1) for i in range(24)]
        for hour in hours:
            abilities[hour] = {'med': 5, 'trauma': 7}
        return abilities

    def set_abilities_from_csv(self, csv_file_path):
        with open(csv_file_path, mode='r') as csv_file:
            csv_reader = csv.reader(csv_file_path)
            next(csv_reader)  # Skip the header row
            for row in csv_reader:
                hour, med_mojo, trauma_mojo = row
                self.abilities[hour] = {'med': int(med_mojo), 'trauma': int(trauma_mojo)}




class ShiftType:
    def __init__(self, name, start_time, end_time, new_patient=True):
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
        self.new_patient = new_patient
        self.assigned_physicians = []

class ERSimulation:
    def __init__(self, monthly_patient_count, med_to_trauma_ratio, hourly_range):
        self.monthly_patient_count = monthly_patient_count
        self.med_to_trauma_ratio = med_to_trauma_ratio
        self.hourly_range = hourly_range  # a dictionary like {'00:00-01:00': (5,10), ...}
        self.current_time = 0
        self.patients = []
        self.physicians = []
        self.shift_types = []

    def create_physician(self, name, abilities):
        physician = Physician(name, abilities)
        self.physicians.append(physician)

    def create_physicians_from_csvs(csv_file_paths):
        physicians = []
        for csv_file_path in csv_file_paths:
            name = csv_file_path.split('.')[0]  # Use the filename (without extension) as the physician's name
            physician = Physician(name)
            physician.set_abilities_from_csv(csv_file_path)
            physicians.append(physician)
        return physicians

    def create_shift_type(self, name, start_time, end_time, new_patient=True):
        shift_type = ShiftType(name, start_time, end_time, new_patient)
        self.shift_types.append(shift_type)

    def patient_arrival(self):
        patient_type = 'med' if random.random() < self.med_to_trauma_ratio else 'trauma'
        arrival_time = self.current_time
        patient = Patient(arrival_time, patient_type)
        self.patients.append(patient)
    def assign_patient_to_area(self, patient, area):
        patient.assigned_area = area
        area.patients.append(patient)
    def physician_treat_patient(self, physician):
        # ... logic to choose a patient based on priority
        pass
    def advance_time(self, minutes=1):
        self.current_time += minutes
        # Handle patient arrivals, treatment completions, etc.
        if self.current_time % 10 == 0:  # Every 10 minutes, for example
            self.patient_arrival()

    # ... other methods to handle game mechanics




