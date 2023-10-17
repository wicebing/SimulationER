import random, os, csv, threading, time, glob, logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

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
        hours = ["{:02d}:00-{:02d}:59".format(i, i) for i in range(24)]
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
        hours = ["{:02d}:00-{:02d}:59".format(i, i) for i in range(24)]
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
        hours = ["{:02d}:00-{:02d}:59".format(i, i) for i in range(24)]
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
        day_of_week = arrival_time.strftime('%A')
        hour_of_day = arrival_time.strftime('%H:00-%H:59')
        
        self.patient_type = patient_type
        self.boarding_blood = boarding_blood or Patient.DEFAULT_BLOOD_VALUES[day_of_week][hour_of_day][patient_type]['boarding']
        self.disease_blood = disease_blood or Patient.DEFAULT_BLOOD_VALUES[day_of_week][hour_of_day][patient_type]['disease']
        self.departure_blood = departure_blood or Patient.DEFAULT_BLOOD_VALUES[day_of_week][hour_of_day][patient_type]['departure']
        
        self.status = 'triage'
        self.discharge_status = False
        self.assigned_physician = None
        self.need_admission = False
        self.underTreat = 0
        self.bedsideVisit = 0
        
        self.disease_increase_rate = Patient.DEFAULT_DISEASE_INCREASE_RATES[day_of_week][hour_of_day][patient_type]

    def update_disease_blood(self, elapsed_time):
        if self.disease_blood > 0:
            self.disease_blood += self.disease_increase_rate * elapsed_time

    def update_blood_and_status(self, elapsed_time, current_time):
        # Update disease blood based on elapsed time
        self.update_disease_blood(elapsed_time)

        if self.underTreat > 0:
            self.underTreat = max(0, self.underTreat - elapsed_time)  # Decrement underTreat, but not below 0
        
        # Assuming the physician's mojo is a number indicating how much blood is reduced per second
        if self.assigned_physician:
            mojo = self.assigned_physician.get_mojo(self.patient_type, current_time)
            blood_reduction = mojo * elapsed_time  #  elapsed_time is in minutes
            
            if self.underTreat > 0 and self.disease_blood > 0:
                self.disease_blood = max(0, self.disease_blood - blood_reduction)  
                print(f"Patient {self.num} disease blood reduced by {blood_reduction} to {self.disease_blood} by {self.assigned_physician.name}.")
                logging.info(f"Patient {self.num} disease blood reduced by {blood_reduction} to {self.disease_blood} by {self.assigned_physician.name}.")             

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
    
    def __init__(self, name, abilities=None, energy=180):
        if name in Physician.used_names:
            raise ValueError(f"The name '{name}' is already in use. Please choose a different name.")
        self.name = name
        Physician.used_names.add(name)  # Add the name to the set of used names
        
        if abilities is None:
            self.abilities = self.default_abilities()
        else:
            self.abilities = abilities
        self.energy = energy  # Default energy is 100
        self.fatigue = 0  # Default fatigue is 0
        self.rest_tendency = 1  # Default rest tendency is 1, minimum is 1
        self.shift_type = None  # Initial shift type is None

    @staticmethod
    def default_abilities():
        abilities = {}
        hours = ["{:02d}:00-{:02d}:59".format(i, i) for i in range(24)]
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
    all_shifts = []

    def __init__(self, name, start_time_str, end_time_str, recieve_patient_type=['med', 'trauma'], new_patient=True):
        if name in ShiftType.used_names:
            raise ValueError(f"The name '{name}' is already in use. Please choose a different name.")
        self.name = name
        ShiftType.used_names.add(name)  # Add the name to the set of used names
        
        self.start_time = self._convert_to_time(start_time_str)
        self.end_time = self._convert_to_time(end_time_str)
        
        # Determine the end_day_offset
        if self.end_time <= self.start_time:
            self.end_day_offset = 1
        else:
            self.end_day_offset = 0
        
        self.recieve_patient_type = recieve_patient_type
        self.recieve_patient_num = 0
        self.new_patient = new_patient
        self.shift_rule = None  # Initial rule is None
        ShiftType.all_shifts.append(self)


    def _convert_to_time(self, time_str):
        """Convert a string in HH:MM format to a time object."""
        return datetime.strptime(time_str, "%H:%M").time()

    def is_time_within_shift(self, check_time):
        """Check if a given time is within the shift's start and end times."""
        if self.end_day_offset == 0:
            return self.start_time <= check_time <= self.end_time
        # For shifts that span midnight
        return check_time >= self.start_time or check_time <= self.end_time

    def set_shift_rule(self, before_midnight_shifts, after_midnight_shifts, no_division=None):
        """Set the handoff rule for this shift.
        
        Parameters:
        - before_midnight_shifts: List of shift names to hand off patients arriving before midnight.
        - after_midnight_shifts: List of shift names to hand off patients arriving after midnight.
        """
        self.shift_rule = {
            'before_midnight': [self.get_shift_by_name(name) for name in before_midnight_shifts],
            'after_midnight': [self.get_shift_by_name(name) for name in after_midnight_shifts],
            'no_division': [self.get_shift_by_name(name) for name in no_division] if no_division else None
        }
    
    def get_handoff_shift(self, arrival_datetime, current_time):
        """Determine which shift to hand off a patient based on their arrival time."""
        if self.shift_rule.get('no_division'):
            return random.choice(self.shift_rule['no_division'])
        if arrival_datetime.date() < current_time.date():
            return random.choice(self.shift_rule['before_midnight'])
        else:
            return random.choice(self.shift_rule['after_midnight'])
        
    @classmethod
    def get_shift_by_name(cls, name):
        for shift in cls.all_shifts:
            if shift.name == name:
                return shift
        return None

class ERSimulation:
    FRAME_RATE = 100  # Default frame rate is 100 frames per second
    def __init__(self, 
                 start_datetime, 
                 end_datetime, 
                 daily_patient_count,
                 med_to_trauma_ratio, 
                 csv_file_path=None,
                 Simulate=False):
        self.setup_logging()
        self.daily_patient_count = daily_patient_count
        self.med_to_trauma_ratio = med_to_trauma_ratio
        if csv_file_path:
            self.load_hourly_range_from_csv(csv_file_path)
            self.adjust_hourly_range()
        else:
            self.hourly_range = {}  # Default empty dictionary or some default values
        self.patients = []
        self.physicians = []
        self.shift_types = []
        self.start_datetime = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
        self.end_datetime = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M:%S")
        self.current_time = self.start_datetime
        self.time_speed = 1  # Default is real-time
        self.running = False
        self.patient_records = {}
        self.Simulate = Simulate

        # attributes for recording
        self.physician_records = {}  # Stores physician's actions every minute
        self.shift_records = {}  # Stores shiftType's patient counts (status and underTreat) every minute
        self.total_er_records = []  # Stores total ER patient counts (status and underTreat) every minute

    def setup_logging(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Remove existing log file (if it exists)
        log_file_path = f"./log/ersimulation_{timestamp}.log"  

        # Ensure the log directory exists
        if not os.path.exists("./log"):
            os.makedirs("./log")
        if os.path.exists(log_file_path):
            os.remove(log_file_path)

        logging.basicConfig(filename=log_file_path, 
                            level=logging.INFO, 
                            format='%(asctime)s - %(message)s', 
                            datefmt='%Y-%m-%d %H:%M:%S')

    def set_time_speed(self, speed):
        """
        Set the time speed of the simulation.

        Parameters:
        - speed: an integer. 
                 0 is default speed (100 frames/second).
                 Positive values speed up time (e.g., 4 means 500 frames/second).
                 Negative values slow down time (e.g., -4 means 20 frames/second).
        """
        if speed > 4 or speed < -4:
            raise ValueError("Speed should be between -4 and 4.")

        if speed == 0:
            self.time_speed = 1
        elif speed > 0:
            self.time_speed = 1+speed
        else:
            self.time_speed = 1 / (1+ abs(speed))

    def start(self):
        # Ensure that there's at least one ShiftType added before starting
        if not self.shift_types:
            raise RuntimeError("At least one ShiftType needs to be added before starting the simulation.")
        
        # Check if all ShiftTypes have handoff rules set
        for shift in self.shift_types:
            if not shift.shift_rule:
                raise RuntimeError(f"ShiftType '{shift.name}' does not have a handoff rule set.")

        if not hasattr(self, 'working_schedule') or not self.working_schedule:
            raise RuntimeError("Please create a working schedule before starting the simulation.")

        self.running = True
        while self.running and self.current_time < self.end_datetime:
            frame_duration = 1 / (ERSimulation.FRAME_RATE * self.time_speed)  # duration of a frame in real-world seconds
            self.current_time += timedelta(minutes=1)
            print(self.current_time)
            logging.info(self.current_time)

            # Patient arrival logic
            self.patient_arrival()

            discharged_patients = []  # List to store patients who have been discharged this iteration
            # Handle physician-patient interactions
            # Determine which physicians are currently working
            current_shift = [shift for shift in self.shift_types if shift.is_time_within_shift(self.current_time.time())]
            current_physician_names = []
            for shift in current_shift:
                # Determine the date to use for looking up the schedule for this specific shift
                if self.current_time.time() < shift.start_time:
                    lookup_date = self.current_time.date() - timedelta(days=1)
                else:
                    lookup_date = self.current_time.date()

                physician_name = self.working_schedule.get(lookup_date, {}).get(shift.name)
                if physician_name:
                    current_physician_names.append(physician_name)

            current_physicians = [physician for physician in self.physicians if physician.name in current_physician_names]

            discharged_patients = []  # List to store patients who have been discharged this iteration
            # Handle physician-patient interactions for only those physicians currently working
            for physician in current_physicians:
                self.physician_treat_patient(physician)

            for patient in self.patients:
                self.record_patient_process(patient)
                patient.update_blood_and_status(1, self.current_time)
                if patient.discharge_status:
                    discharged_patients.append(patient)
                self.record_patient_process(patient)
                    
            # Remove discharged patients from the active patient list
            for patient in discharged_patients:
                self.record_patient_process(patient)
                self.patients.remove(patient)
                del patient  # Explicitly delete the patient object

            # Record total ER patient counts for this frame (minute)
            self.record_patient_counts()

            # Check for shift change and handoff patients
            self.check_shift_change_and_handoff()

            if self.Simulate:    
                time.sleep(frame_duration)
        self.running = False
        print("Simulation ending.")
        logging.info("Simulation ending.")

    def stop(self):
        self.running = False
        print("Simulation ending.")
        logging.info("Simulation ending.")

    def create_working_schedule(self):
        if not self.shift_types:
            raise ValueError("Please create ShiftTypes before generating a working schedule.")
        
        schedule = {}
        current_date = self.start_datetime.date()
        
        while current_date <= self.end_datetime.date():
            daily_schedule = {}
            for shift in self.shift_types:
                # Check if the shift on the previous day covers the current day
                if current_date - timedelta(days=1) in schedule and shift.name in schedule[current_date - timedelta(days=1)] and shift.end_day_offset == 1:
                    continue
                # Check if the end_datetime is on the current_date and if the shift's start time is not covered by the end_datetime
                if current_date == self.end_datetime.date() and self.end_datetime.time() <= shift.start_time:
                    continue
                daily_schedule[shift.name] = None  # Initially, no physician is assigned

            if daily_schedule:
                schedule[current_date] = daily_schedule
            current_date += timedelta(days=1)
        
        self.working_schedule = schedule
        return schedule

    def save_working_schedule_to_csv(self, directory="./playGround"):
        if not hasattr(self, 'working_schedule') or not self.working_schedule:
            self.create_working_schedule()
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        csv_file_path = os.path.join(directory, "working_schedule.csv")
        
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            # For the header, take the union of all shift names scheduled for any date
            all_shift_names = set().union(*[set(shifts.keys()) for shifts in self.working_schedule.values()])
            header = ["Date"] + sorted(list(all_shift_names))
            writer.writerow(header)
            
            for date, daily_schedule in self.working_schedule.items():
                row = [date] + [daily_schedule.get(shift_name, '') for shift_name in header[1:]]
                writer.writerow(row)

    def load_working_schedule_from_csv(self, csv_file_path="./playGround/working_schedule.csv"):
        with open(csv_file_path, mode='r') as csv_file:
            csv_reader = csv.reader(csv_file)
            header = next(csv_reader)  # Get the header with shift names
            
            for row in csv_reader:
                try:
                    date = datetime.strptime(row[0], "%Y-%m-%d").date()
                except:
                    date = datetime.strptime(row[0], "%Y/%m/%d").date()
                if date not in self.working_schedule:
                    self.working_schedule[date] = {}
                    
                for i, shift_name in enumerate(header[1:]):
                    if row[i+1]:  # If there's a physician assigned
                        self.working_schedule[date][shift_name] = row[i+1]


    def verify_schedule(self):
        for date, daily_schedule in self.working_schedule.items():
            for shift, physician in daily_schedule.items():
                if not physician:
                    raise ValueError(f"No physician assigned to {shift} on {date}.")

    def check_shift_change_and_handoff(self):
        """Check if the current time matches any ShiftType end time and handle patient handoff."""
        for shift in self.shift_types:
            if self.current_time.time() == shift.end_time:  # Shift end time reached
                print(f"Shift {shift.name} ending at {self.current_time}.")
                logging.info(f"Shift {shift.name} ending at {self.current_time}.")           
                for patient in self.patients:
                    if patient.assigned_physician and patient.assigned_physician.shift_type == shift.name:
                        off_physician = patient.assigned_physician
                        # Determine the next shift based on the handoff rule
                        new_shift = shift.get_handoff_shift(patient.arrival_time, self.current_time)
                        
                        # Find the physician for the new shift from the working schedule
                        if new_shift.end_day_offset == 0:
                            new_physician_name = self.working_schedule.get(self.current_time.date(), {}).get(new_shift.name)
                        else:
                            if self.current_time.time() >= new_shift.start_time:
                                new_physician_name = self.working_schedule.get(self.current_time.date(), {}).get(new_shift.name)
                            else:
                                new_physician_name = self.working_schedule.get(self.current_time.date() - timedelta(days=1), {}).get(new_shift.name)
                        
                        # Assign the new physician to the patient
                        patient.assigned_physician = next((physician for physician in self.physicians if physician.name == new_physician_name), None)
                        print(f"Patient {patient.num} assigned to {patient.assigned_physician.name} for {new_shift.name}.")
                        logging.info(f"Patient {patient.num} assigned to {patient.assigned_physician.name} for {new_shift.name}.")
                        patient.assigned_physician.shift_type = new_shift.name
                        logging.info(f"Patient {patient.num}: {patient.assigned_physician.name}, shift:{patient.assigned_physician.shift_type}")
                        patient.bedsideVisit = 0
                        new_shift.recieve_patient_num =0

                        logging.info(f"{off_physician.name} off, shift:{off_physician.shift_type}")


    def record_patient_process(self, patient):
        """
        Record the process of a patient at the current time.
        """
        if patient.num not in self.patient_records:
            # First-time recording for this patient
            self.patient_records[patient.num] = [{
                'Patient_num': patient.num,
                'Arrival_time': patient.arrival_time,
                'Patient_type': patient.patient_type,
                'Initial_boarding_blood': patient.boarding_blood,
                'Initial_disease_blood': patient.disease_blood,
                'Initial_departure_blood': patient.departure_blood,
                'Status': patient.status,
                'Assigned_physician': patient.assigned_physician.name if patient.assigned_physician else None,
                'Timestamp': self.current_time
            }]
            return

        # Check if there's a change in physician or status
        last_record = self.patient_records[patient.num][-1]
        if (last_record['Assigned_physician'] != (patient.assigned_physician.name if patient.assigned_physician else None)) or \
           (last_record['Status'] != patient.status):
            new_record = {
                'Patient_num': patient.num,
                'Arrival_time': patient.arrival_time,
                'Patient_type': patient.patient_type,
                'Current_boarding_blood': patient.boarding_blood,
                'Current_disease_blood': patient.disease_blood,
                'Current_departure_blood': patient.departure_blood,
                'Status': patient.status,
                'Assigned_physician': patient.assigned_physician.name if patient.assigned_physician else None,
                'Timestamp': self.current_time
            }
            self.patient_records[patient.num].append(new_record)

    def generate_patient_chart(self):
        # Flatten the patient records to generate a chart
        chart = []
        for records in self.patient_records.values():
            chart.extend(records)
        return chart

    def generate_summary(self):
        summary = []
        
        # We'll go through each day in the working_schedule
        for date, daily_schedule in self.working_schedule.items():
            for shift_name, physician_name in daily_schedule.items():
                # Retrieve the shift object by name
                shift = next((s for s in self.shift_types if s.name == shift_name), None)
                
                # Initialize counters
                metrics = {
                    'total': {
                        'new_arrivals': 0,
                        'handoffs_received': 0,
                        'handoffs_given': 0,
                        'discharges': 0
                    }
                }
                # Initialize counters for each patient type
                for patient_type in ['med', 'trauma', ]:  # You can adjust this list as needed
                    metrics[patient_type] = {
                        'new_arrivals': 0,
                        'handoffs_received': 0,
                        'handoffs_given': 0,
                        'discharges': 0
                    }

                # Calculate shift start and end datetime
                start_datetime = datetime.combine(date, shift.start_time)
                end_datetime = datetime.combine(date + timedelta(days=shift.end_day_offset), shift.end_time) + timedelta(minutes=1)
                
                # Go through patient records to count metrics
                for patient_num, records in self.patient_records.items():
                    for i, record in enumerate(records):
                        timestamp = record['Timestamp']
                        current_type = record['Patient_type']  # Assuming there's a 'Patient_type' field
                        
                        # Check if the record is within the current shift
                        if start_datetime <= timestamp <= end_datetime:
                            # Update metrics for both total and the respective patient type
                            for key in ['total', current_type]:
                                # Check for new arrivals
                                if record['Arrival_time'] == timestamp and record['Assigned_physician'] == physician_name:
                                    metrics[key]['new_arrivals'] += 1
                                # Check for handoffs received by this physician
                                if i != 0 and records[i-1]['Assigned_physician'] != physician_name and record['Assigned_physician'] == physician_name:
                                    metrics[key]['handoffs_received'] += 1
                                # Check for handoffs given by this physician
                                if i != 0 and records[i-1]['Assigned_physician'] == physician_name and record['Assigned_physician'] != physician_name:
                                    metrics[key]['handoffs_given'] += 1
                                # Check for discharges
                                if record['Status'] == 'discharge' and record['Assigned_physician'] == physician_name:
                                    metrics[key]['discharges'] += 1

                # Append the summary for this shift and physician (for total and each patient type)
                for key, metric in metrics.items():
                    summary.append({
                        'Type': key,  # 'total' or patient type
                        'Shift Type': shift_name,
                        'Physician Name': physician_name,
                        'Shift Start Timing': start_datetime,
                        'Shift End Timing': end_datetime,
                        'New Arrival Patients': metric['new_arrivals'],
                        'Handoff Patients Received': metric['handoffs_received'],
                        'Handoff Patients Given': metric['handoffs_given'],
                        'Discharged Patients': metric['discharges']
                    })  
        return summary

    def record_patient_counts(self):
        """Record the patient counts (status and underTreat) for each shift and the total ER at the current frame."""

        # Initial setup
        shift_dicts = {shift.name: {
            'triage': 0,
            'on-board': 0,
            'wait-depart': 0,
            'underTreat': 0
        } for shift in self.shift_types}

        total_er_dict = {
            'triage': 0,
            'on-board': 0,
            'wait-depart': 0,
            'underTreat': 0
        }

        # Iterating through each patient once
        for patient in self.patients:
            assigned_shift = patient.assigned_physician.shift_type if patient.assigned_physician else None
            if assigned_shift and patient.status in shift_dicts[assigned_shift]:
                shift_dicts[assigned_shift][patient.status] += 1
                if patient.underTreat > 0:
                    shift_dicts[assigned_shift]['underTreat'] += 1

            if patient.status in total_er_dict:
                total_er_dict[patient.status] += 1
                if patient.underTreat > 0:
                    total_er_dict['underTreat'] += 1

        # Appending the current frame's data to the respective record lists
        for shift_name, counts in shift_dicts.items():
            if shift_name not in self.shift_records:
                self.shift_records[shift_name] = []
            self.shift_records[shift_name].append({
                'Timestamp': self.current_time,
                **counts
            })

        self.total_er_records.append({
            'Timestamp': self.current_time,
            **total_er_dict
        })

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
        scaling_factor = self.daily_patient_count / (total_patients_in_hourly_range)  # Assuming a month is roughly 30 days

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

    def create_physicians_from_csvs(self, file_paths):
        csv_file_paths = glob.glob(os.path.join(file_paths,'*.csv'))
        for csv_file_path in csv_file_paths:
            name = os.path.basename(csv_file_path).split('.')[0]  # Use the filename (without extension) as the physician's name
            physician = Physician(name)
            physician.set_abilities_from_csv(csv_file_path)
            self.physicians.append(physician)

    def create_shift_type(self, name, start_time, end_time, new_patient=True):
        shift_type = ShiftType(name, start_time, end_time, new_patient)
        self.shift_types.append(shift_type)

    def patient_arrival(self):
        current_hour_str = f"{self.current_time.hour:02d}:00-{(self.current_time.hour) % 24:02d}:59"
        min_patients, max_patients = self.hourly_range.get(current_hour_str, (0, 0))

        # Calculate the average expected number of arrivals for the current minute
        average_arrivals_this_minute = (max_patients - min_patients) / 60.0 + min_patients / 60.0

        # Use the Poisson distribution to get a random number of arrivals for this minute
        num_arrivals = np.random.poisson(average_arrivals_this_minute)

        for _ in range(num_arrivals):
            patient_type = 'med' if random.random() < self.med_to_trauma_ratio else 'trauma'
            arrival_time = self.current_time
            patient = Patient(arrival_time, patient_type)
            self.patients.append(patient)

            # Determine the current shifts based on the current_time and patient type
            current_shifts = [shift for shift in self.shift_types 
                            if shift.new_patient 
                            and shift.is_time_within_shift(self.current_time.time())
                            and patient_type in shift.receive_patient_type]

            # If there are no shifts available for new patients, we can't assign a physician
            if not current_shifts:
                print(f"Patient {patient.num} arrived at {patient.arrival_time} with type {patient.patient_type}, but no available shifts for new patients.")
                logging.info(f"Patient {patient.num} arrived at {patient.arrival_time} with type {patient.patient_type}, but no available shifts for new patients.")
                continue

            # Count how many new patients each shift has received
            shift_counts = {shift.name: shift.recieve_patient_num for shift in current_shifts}

            # Find the shift with the least number of new patients
            min_count = min(shift_counts.values())
            shifts_with_min_count = [shift for shift, count in shift_counts.items() if count == min_count]

            # Randomly select one of the current shifts
            selected_shift = random.choice(shifts_with_min_count)

            # Get the physician assigned to that shift from the working schedule
            if selected_shift.end_day_offset ==0:
                assigned_physician_name = self.working_schedule.get(self.current_time.date(), {}).get(selected_shift.name)
            else:
                if self.current_time.time() >= selected_shift.start_time:
                    assigned_physician_name = self.working_schedule.get(self.current_time.date(), {}).get(selected_shift.name)
                else:
                    assigned_physician_name = self.working_schedule.get(self.current_time.date() - timedelta(days=1), {}).get(selected_shift.name)

            # Find the physician object based on the name
            assigned_physician = next((physician for physician in self.physicians if physician.name == assigned_physician_name), None)
            assigned_physician.shift_type = selected_shift.name

            # Assign the patient to the physician
            patient.assigned_physician = assigned_physician
            selected_shift.recieve_patient_num += 1
            print(f"Patient {patient.num} arrived at {patient.arrival_time} with type {patient.patient_type} and was assigned to {assigned_physician.name}.")
            logging.info(f"Patient {patient.num} arrived at {patient.arrival_time} with type {patient.patient_type} and was assigned to {assigned_physician.name}.")

    def physician_treat_patient(self, physician):
        all_status = ['triage', 'on-board', 'wait-depart']
        # Filter out the patients assigned to the current physician
        physician_patients = [p for p in self.patients if p.assigned_physician == physician]
        # Count the number of patients in each status
        status_counts = {status: sum(1 for p in physician_patients if p.status == status) for status in all_status}
        underTreat_count = sum(1 for p in physician_patients if p.underTreat > 0)
        
        print(f"Physician {physician.name} has {len(physician_patients)} patients. Status counts: {status_counts}. Number of patients with underTreat > 0: {underTreat_count}")
        logging.info(f'physician {physician.name} has {len(physician_patients)} patients. Status counts: {status_counts}. Number of patients with underTreat > 0: {underTreat_count}')

        # Check if any patient is currently being visited by the physician
        visited_patient = next((p for p in physician_patients if p.bedsideVisit == 1), None)
        if visited_patient:
            print(f"Physician {physician.name} keep visiting patient {visited_patient.num}.")
            logging.info(f"Physician {physician.name} keep visiting patient {visited_patient.num}.")               
        # If no patient is being visited, select a patient to visit based on some criteria (e.g., arrival time)
        else:
            status_weight = [1 if status_counts[status] > 0 else 0 for status in all_status]
            # Adjust the selection probability based on the physician's energy
            weights = [*status_weight, max(physician.rest_tendency, physician.rest_tendency/(1+physician.energy))]  # Increasing the weight for 'rest' as energy decreases
            select_status = random.choices([*all_status, 'rest'], weights=weights, k=1)[0]

            potential_patients = [p for p in physician_patients if p.status == select_status]

            if potential_patients:
                if select_status != 'on-board':
                    visited_patient = random.choice(potential_patients)
                else:
                    # Filter potential patients with underTreat = 0
                    potential_underTreat_zero = [p for p in potential_patients if p.underTreat == 0]
                    if potential_underTreat_zero:
                        visited_patient = random.choice(potential_underTreat_zero)
                    else:
                        visited_patient = random.choice(potential_patients)
            if visited_patient:
                print(f"Physician {physician.name} is visiting patient {visited_patient.num}." )
                logging.info(f"Physician {physician.name} is visiting patient {visited_patient.num}." )

        """Record the physician's action for the current frame."""
        action = 1 if visited_patient else 0
        if physician.name not in self.physician_records:
            self.physician_records[physician.name] = []
        self.physician_records[physician.name].append({
            'ShiftType': physician.shift_type,
            'Timestamp': self.current_time,
            'Action': action,
            'patient': visited_patient.num if visited_patient else None,
            'underTreat': underTreat_count,
            **status_counts,
        })

        # If we still don't have a patient to visit (e.g., all are discharged), exit the function
        if not visited_patient:
            print(f"Physician {physician.name} rest in this minute.")
            logging.info(f"Physician {physician.name} rest in this minute, no visit any patient.")
            return
        
        # Set bedsideVisit to 1 for the visited patient
        visited_patient.bedsideVisit = 1
        
        # Calculate the physician's mojo for the patient type
        mojo = physician.get_mojo(visited_patient.patient_type, self.current_time)
        blood_reduction = mojo  # Blood reduction rate when bedsideVisit = 1
        
        # If boarding blood is still positive, reduce it
        if visited_patient.boarding_blood > 0:
            visited_patient.boarding_blood = max(0, visited_patient.boarding_blood - 2*blood_reduction)
            print(f'physician {physician.name} is treating patient {visited_patient.num}, decrease boarding blood by {2*blood_reduction}')
            logging.info(f'physician {physician.name} is treating patient {visited_patient.num}, decrease boarding blood by {2*blood_reduction}')
            if visited_patient.boarding_blood <= 0:
                visited_patient.underTreat += 60  # Increase underTreat by 60 minutes when status becomes on-board
                print(f'patient {visited_patient.num} status becomes on-board')
                logging.info(f'patient {visited_patient.num} status becomes on-board')
        # If underTreat is positive and disease blood is positive, reduce disease blood and increase underTreat
        elif visited_patient.underTreat > 0 and visited_patient.disease_blood > 0:
            visited_patient.disease_blood = max(0, visited_patient.disease_blood - blood_reduction)
            visited_patient.underTreat += 10  # Increase by 10 for each minute the physician visits the patient
            print(f'physician {physician.name} is treating patient {visited_patient.num}, decrease disease blood by {blood_reduction} and increase underTreat by 10')
            logging.info(f'physician {physician.name} is treating patient {visited_patient.num}, decrease disease blood by {blood_reduction} and increase underTreat by 10')
        # If disease blood is 0 and departure blood is still positive, reduce it
        elif visited_patient.disease_blood <= 0 and visited_patient.departure_blood > 0:
            visited_patient.departure_blood = max(0, visited_patient.departure_blood - 2*blood_reduction)
            print(f'physician {physician.name} is treating patient {visited_patient.num}, decrease departure blood by {2*blood_reduction}')
            logging.info(f'physician {physician.name} is treating patient {visited_patient.num}, decrease departure blood by {2*blood_reduction}')
            
        # Update the patient's status based on blood values
        if visited_patient.boarding_blood <= 0:
            visited_patient.status = 'on-board'
        if visited_patient.disease_blood <= 0:
            visited_patient.status = 'wait-depart'
        if visited_patient.departure_blood <= 0:
            visited_patient.status = 'discharge'
            visited_patient.discharge_status = True
        
        # If the patient's boarding blood has reduced to 0, set bedsideVisit back to 0
        if visited_patient.boarding_blood <= 0:
            visited_patient.bedsideVisit = 0
        


    # ... other methods to handle game mechanics

def save_to_excel(data, filename):
    """
    Save a dictionary of dictionaries to an Excel file with separate sheets.
    
    Parameters:
    - data: The dictionary of dictionaries.
    - filename: The filename for the Excel file.
    """
    with pd.ExcelWriter(filename) as writer:
        for key, records in data.items():
            df = pd.DataFrame(records)
            df.to_excel(writer, sheet_name=str(key), index=False)


if __name__ == '__main__':
    er=ERSimulation("2023-03-01 08:00:00", "2023-03-06 07:59:00", 200, 5, "settings/ersimulation_default.csv", Simulate=False)
    er.set_time_speed(4)
    er.create_physician("DrA")
    er.create_physician("DrB")
    er.create_physician("DrC")
    er.create_physician("DrD")
    er.create_physician("DrE")
    er.create_physician("DrF")

    er.create_shift_type(name='a',start_time_str='08:00',end_time_str='20:00',recieve_patient_type=['med',], new_patient=True)
    er.create_shift_type(name='b',start_time_str='08:00',end_time_str='20:00',recieve_patient_type=['med','trauma'], new_patient=True)
    er.create_shift_type(name='an',start_time_str='20:00',end_time_str='08:00',recieve_patient_type=['med','trauma'], new_patient=True)
    er.create_shift_type(name='e',start_time_str='08:00',end_time_str='20:00',recieve_patient_type=['med','trauma'], new_patient=False)

    er.shift_types[0].set_shift_rule(['an'],['an'],['an'])
    er.shift_types[1].set_shift_rule(['an'],['an'],['an'])
    er.shift_types[2].set_shift_rule(['e'],['a','b'])
    er.shift_types[3].set_shift_rule(['an'],['an'],['an'])

    er.create_working_schedule()
    # er.save_working_schedule_to_csv()

    # input("Please complete the schedule CSV and press Enter to continue...")
    er.load_working_schedule_from_csv()
    Patient.load_defaults_from_csv('./settings/patient_default.csv')
    
    er.start()

    result = pd.DataFrame(er.generate_patient_chart())
    summary_physician = pd.DataFrame(er.generate_summary())
    summary_er = pd.DataFrame(er.total_er_records)

    result.to_excel('./results/result.xlsx', index=False)
    summary_physician.to_excel('./results/summary_physician.xlsx', index=False)
    summary_er.to_excel('./results/summary_er.xlsx', index=False)
    save_to_excel(er.shift_records,'./results/summary_shift.xlsx')
    save_to_excel(er.physician_records,'./results/physician_records.xlsx')

