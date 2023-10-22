import pandas as pd
import numpy as np
import random

# Load the working_schedule CSV
schedule_df = pd.read_csv("./playGround/working_schedule.csv")

SHIFT_TYPES = ['a', 'b', 'c', 'ea', 'eb', 'd', 'an', 'bn0', 'bn1', 'cn']
PHYSICIANS = [f"Dr{chr(i)}" for i in range(65, 65+26)]  # DrA to DrZ

SHIFT_START_TIMES = {
    'a': '08:00', 'b': '08:00', 'c': '08:00', 'ea': '08:00', 'eb': '08:00', 'd': '14:00',
    'an': '20:00', 'bn0': '20:00', 'bn1': '23:00', 'cn': '20:00'
}

SHIFT_END_TIMES = {
    'a': '20:00', 'b': '20:00', 'c': '20:00', 'ea': '20:00', 'eb': '20:00', 'd': '21:30',
    'an': '08:00', 'bn0': '23:00', 'bn1': '08:00', 'cn': '08:00'
}

# Define a function to get the next physician ensuring they rest for at least 8 hours
def get_next_physician(current_physician, last_shift_end_times, shift_start_time):
    # Create a copy of the physicians list and shuffle it for randomness
    shuffled_physicians = PHYSICIANS.copy()
    random.shuffle(shuffled_physicians)
    
    for next_physician in shuffled_physicians:
        last_shift_end_time = last_shift_end_times.get(next_physician, "00:00")
        hours_since_last_shift = (pd.Timestamp(shift_start_time) - pd.Timestamp(last_shift_end_time)).seconds / 3600
        if hours_since_last_shift >= 8:
            return next_physician
    return None

# Update the working schedule using the constraints provided
last_assigned = {}  # Track the last shift a physician was assigned to
shift_end_times = {}  # Track when a physician's last shift ended

# Define a function to determine if a physician can be assigned to a new shift based on rest hours
def can_assign_physician_to_shift(physician, shift, last_shift_end_times):
    last_shift_end_time = last_shift_end_times.get(physician, "00:00")
    hours_since_last_shift = (pd.Timestamp(SHIFT_START_TIMES[shift]) - pd.Timestamp(last_shift_end_time)).seconds / 3600
    return hours_since_last_shift >= 8

# Create a working schedule from scratch
schedule_filled_data = []
last_shift_end_times = {}  # Track when a physician's last shift ended

# Start assigning from DrA
current_physician = "DrZ"

for _, row in schedule_df.iterrows():
    day_schedule = {'Date': row['Date']}
    physicians_for_the_day = []  # Keep track of physicians assigned for the day to avoid duplicates
    
    for shift in SHIFT_TYPES:
        # If the shift type is 'bn1', assign the same physician as 'bn0'
        if shift == 'bn1':
            day_schedule[shift] = day_schedule['bn0']
            continue
        
        # Find next available physician for this shift
        while True:
            current_physician = get_next_physician(None, last_shift_end_times, SHIFT_START_TIMES[shift])
            if current_physician and current_physician not in physicians_for_the_day:
                break
        
        day_schedule[shift] = current_physician
        physicians_for_the_day.append(current_physician)
        last_shift_end_times[current_physician] = SHIFT_END_TIMES[shift]
        
    schedule_filled_data.append(day_schedule)

# Convert the filled schedule to DataFrame
schedule_filled_df = pd.DataFrame(schedule_filled_data)

# Save the filled working schedule
schedule_filled_df.to_csv("./playGround/working_schedule_filled.csv", index=False)

