import random, os, csv, threading, time
from datetime import datetime, timedelta

def generate_patient_default_csv(filename="patient_default.csv"):
    # Check if directory exists, if not create it
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Check if the file already exists
    if os.path.isfile(filename):
        print(f"{filename} already exists. Skipping...")
        return

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["day", "hour", "patient_type", "boarding_blood", "disease_blood", "departure_blood", "increase_rate"])
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        hours = ["{:02d}:00-{:02d}:00".format(i, i+1) for i in range(24)]
        for day in days:
            for hour in hours:
                writer.writerow([day, hour, "med", 30, 100, 10, 1])
                writer.writerow([day, hour, "trauma", 50, 150, 15, 2])

def generate_physician_default_csv(filename="physician_default.csv"):
    # Check if directory exists, if not create it
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Check if the file already exists
    if os.path.isfile(filename):
        print(f"{filename} already exists. Skipping...")
        return
    
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["hour", "med", "trauma"])
        hours = ["{:02d}:00-{:02d}:00".format(i, i+1) for i in range(24)]
        for hour in hours:
            writer.writerow([hour, 5, 7])


def generate_ersimulation_default_csv(filename="ersimulation_default.csv"):
    # Check if directory exists, if not create it
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Check if the file already exists
    if os.path.isfile(filename):
        print(f"{filename} already exists. Skipping...")
        return
    
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["hour", "min_patients", "max_patients"])
        hours = ["{:02d}:00-{:02d}:00".format(i, i+1) for i in range(24)]
        for hour in hours:
            writer.writerow([hour, 5, 10])

generate_patient_default_csv("settings/patient_default.csv")
generate_physician_default_csv("settings/physician_default.csv")
generate_ersimulation_default_csv("settings/ersimulation_default.csv")

class Patient:
    patient_counter = 0  # This is a class-level variable
    DEFAULT_BLOOD_VALUES = {
        'Monday': {
            '00:00-01:00': {
                'med': {'boarding': 30, 'disease': 100, 'departure': 10},
                'trauma': {'boarding': 50, 'disease': 150, 'departure': 15}
            },
            # ... and so on for each hour and day
        },
        # ...
    }
    DEFAULT_DISEASE_INCREASE_RATES = {
        'Monday': {
            '00:00-01:00': {'med': 1, 'trauma': 2},
            # ... and so on for each hour and day
        },
        # ...
    }
    
    def __init__(self, arrival_time, patient_type, boarding_blood=None, disease_blood=None, departure_blood=10):
        Patient.patient_counter += 1
        self.num = Patient.patient_counter
        
        self.arrival_time = arrival_time
        day_of_week = datetime.strptime(arrival_time, "%Y-%m-%d %H:%M:%S").strftime('%A')
        hour_of_day = datetime.strptime(arrival_time, "%Y-%m-%d %H:%M:%S").strftime('%H:00-%H:59')
        
        self.patient_type = patient_type
        self.boarding_blood = boarding_blood or Patient.DEFAULT_BLOOD_VALUES[day_of_week][hour_of_day][patient_type]
        self.disease_blood = disease_blood or Patient.DEFAULT_BLOOD_VALUES[day_of_week][hour_of_day][patient_type]
        self.departure_blood = departure_blood
        
        self.status = 'triage'
        self.discharge_status = False
        self.assigned_physician = None
        
        self.disease_increase_rate = Patient.DEFAULT_DISEASE_INCREASE_RATES[day_of_week][hour_of_day][patient_type]

    def update_disease_blood(self, elapsed_time):
        if self.disease_blood > 0:
            self.disease_blood += self.disease_increase_rate * elapsed_time

    def update_blood_and_status(self, elapsed_time, current_time):
        # Update disease blood based on elapsed time
        self.update_disease_blood(elapsed_time)
        
        # Assuming the physician's mojo is a number indicating how much blood is reduced per second
        if self.assigned_physician:
            mojo = self.assigned_physician.get_mojo(self.patient_type, current_time)
            blood_reduction = mojo * elapsed_time  #  elapsed_time is in minutes
            
            if self.boarding_blood > 0:
                self.boarding_blood -= blood_reduction
            elif self.disease_blood > 0:
                self.disease_blood -= blood_reduction
            elif self.departure_blood > 0:
                self.departure_blood -= blood_reduction

        # Update patient's status based on blood values
        if self.boarding_blood <= 0:
            self.status = 'on-board'
        if self.disease_blood <= 0:
            self.status = 'wait-depart'
        if self.departure_blood <= 0:
            self.status = 'discharge'
            self.discharge_status = True

    @classmethod
    def load_defaults_from_csv(cls, csv_file_path):
        with open(csv_file_path, mode='r') as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader)  # Skip the header row
            for row in csv_reader:
                day, hour, patient_type, boarding_value, disease_value, departure_value, increase_rate = row
                blood_values = {
                    'boarding': int(boarding_value),
                    'disease': int(disease_value),
                    'departure': int(departure_value)
                }
                cls.DEFAULT_BLOOD_VALUES.setdefault(day, {}).setdefault(hour, {})[patient_type] = blood_values
                cls.DEFAULT_DISEASE_INCREASE_RATES.setdefault(day, {}).setdefault(hour, {})[patient_type] = int(increase_rate)

    '''
    CSV file should be structured as follows:
    day,hour,patient_type,blood_value,increase_rate
    Monday,00:00-01:00,med,30,1
    Monday,00:00-01:00,trauma,50,2
    '''

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

    def get_mojo(self, patient_type, current_time):
        """
        Get the mojo of the physician based on the patient type and current time.
        
        Parameters:
        - patient_type: 'med' or 'trauma'
        - current_time: The current time in the simulation as a datetime object
        
        Returns:
        - The mojo value
        """
        hour_of_day = current_time.strftime('%H:00-%H:59')
        
        return self.abilities.get(hour_of_day, {}).get(patient_type, 0)

    '''
    CSV file should be structured as follows:
    hour,med,trauma
    00:00-01:00,5,7
    01:00-02:00,5,7
    '''



class ShiftType:
    used_names = set()  # This is a class-level set to store used names
    
    def __init__(self, name, start_time, end_time, new_patient=True):
        if name in ShiftType.used_names:
            raise ValueError(f"The name '{name}' is already in use. Please choose a different name.")
        self.name = name
        ShiftType.used_names.add(name)  # Add the name to the set of used names
        
        self.start_time = start_time
        self.end_time = end_time
        self.new_patient = new_patient


class ERSimulation:
    def __init__(self, 
                 start_datetime, 
                 end_datetime, 
                 monthly_patient_count, 
                 med_to_trauma_ratio, 
                 csv_file_path=None):
        self.monthly_patient_count = monthly_patient_count
        self.med_to_trauma_ratio = med_to_trauma_ratio
        if csv_file_path:
            self.load_hourly_range_from_csv(csv_file_path)
            self.adjust_hourly_range()
        else:
            self.hourly_range = {}  # Default empty dictionary or some default values
        self.current_time = 0
        self.patients = []
        self.physicians = []
        self.shift_types = []
        self.start_datetime = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
        self.end_datetime = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M:%S")
        self.current_time = self.start_datetime
        self.time_speed = 1  # Default is real-time
        self.running = False
        self.patient_records = [] 

    def start(self):
        self.running = True
        while self.running and self.current_time <= self.end_datetime:
            self.current_time += timedelta(minutes=1 * self.time_speed)
            time.sleep(1)  # Sleep for 1 real-world second
            
            discharged_patients = []  # List to store patients who have been discharged this iteration
            for patient in self.patients:
                self.record_patient_process(patient)
                patient.update_blood_and_status(self.time_speed, self.current_time)
                if patient.discharge_status:
                    discharged_patients.append(patient)
                
            # Remove discharged patients from the active patient list
            for patient in discharged_patients:
                self.patients.remove(patient)
                del patient  # Explicitly delete the patient object

    def stop(self):
        self.running = False

    def record_patient_process(self, patient):
        """
        Record the process of a patient at the current time.
        """
        record = {
            'Patient_num': patient.num,
            'Arrival_time': patient.arrival_time,
            'Patient_type': patient.patient_type,
            'Boarding_blood': patient.boarding_blood,
            'Disease_blood': patient.disease_blood,
            'Departure_blood': patient.departure_blood,
            'Status': patient.status,
            'Assigned_physician': patient.assigned_physician.name if patient.assigned_physician else None,
            'Timestamp': self.current_time
        }
        self.patient_records.append(record)

    def generate_patient_chart(self):
        # Return a table (list of dictionaries) showing each patient's journey
        return self.patient_records

    def load_hourly_range_from_csv(self, csv_file_path):
        with open(csv_file_path, mode='r') as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader)  # Skip the header row
            hourly_range = {}
            for row in csv_reader:
                hour, min_patients, max_patients = row
                hourly_range[hour] = (int(min_patients), int(max_patients))
        self.hourly_range = hourly_range

    # structure of the CSV file should be:
    # hour,min_patients,max_patients
    # 00:00-01:00,5,10
    # 01:00-02:00,5,10
    # ...    

    def adjust_hourly_range(self):
        # Calculate the scaling factor
        total_patients_in_hourly_range = sum([max_val for _, max_val in self.hourly_range.values()])
        scaling_factor = self.monthly_patient_count / (total_patients_in_hourly_range * 30)  # Assuming a month is roughly 30 days

        # Adjust the hourly range
        for hour, (min_val, max_val) in self.hourly_range.items():
            self.hourly_range[hour] = (int(min_val * scaling_factor), int(max_val * scaling_factor))

    def create_physician(self, name, abilities=None):
        physician = Physician(name, abilities)
        self.physicians.append(physician)

        # Save to CSV
        self.save_physician_to_csv(physician)

    def save_physician_to_csv(self, physician):
        # Ensure the directory exists
        directory = "./settings/physicians"
        if not os.path.exists(directory):
            os.makedirs(directory)

        # File path for the physician
        csv_file_path = os.path.join(directory, f"{physician.name}.csv")

        # Check if the file already exists
        if os.path.isfile(csv_file_path):
            print(f"{csv_file_path} already exists. Skipping saving...")
            return

        # Save the physician's abilities to the CSV
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["hour", "med", "trauma"])
            for hour, abilities in physician.abilities.items():
                med_ability = abilities.get('med', 0)
                trauma_ability = abilities.get('trauma', 0)
                writer.writerow([hour, med_ability, trauma_ability])

    def create_physicians_from_csvs(self, csv_file_paths):
        for csv_file_path in csv_file_paths:
            name = csv_file_path.split('.')[0]  # Use the filename (without extension) as the physician's name
            physician = Physician(name)
            physician.set_abilities_from_csv(csv_file_path)
            self.physicians.append(physician)

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




