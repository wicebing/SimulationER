import pandas as pd
import numpy as np

# Load the c548_T0_ERSim.csv file
ersim_df = pd.read_csv('../data_ehr548/c548_T0_ERSim.csv')

# Modify the s_DEPTCODE column
ersim_df['s_DEPTCODE'] = ersim_df['s_DEPTCODE'].replace({'SURG': 'trauma', 'DTRA': 'trauma', 'MED': 'med'})
# Convert TRIAGEDATETIME to datetime format
ersim_df['s_TRIAGEDATETIME'] = pd.to_datetime(ersim_df['s_TRIAGEDATETIME'])
ersim_df['s_DISCHARGEDATETIME'] = pd.to_datetime(ersim_df['s_DISCHARGEDATETIME'])

# Extract hour from TRIAGEDATETIME
ersim_df['TRIAGE_HOUR'] = ersim_df['s_TRIAGEDATETIME'].dt.hour
ersim_df['TRIAGE_DATE'] = ersim_df['s_TRIAGEDATETIME'].dt.date

# Group by date and hour, then calculate the patient count for each combination
hourly_daily_counts = ersim_df.groupby(['TRIAGE_DATE', 'TRIAGE_HOUR']).size().reset_index(name='patient_count')

# Pivot the table to have hours as columns and dates as rows
hourly_daily_pivot = hourly_daily_counts.pivot(index='TRIAGE_DATE', columns='TRIAGE_HOUR', values='patient_count').reset_index()

# Exclude the 'TRIAGE_DATE' column before computing mean and std
hourly_mean = hourly_daily_pivot.drop(columns=['TRIAGE_DATE']).mean()
hourly_std = hourly_daily_pivot.drop(columns=['TRIAGE_DATE']).std()

# Combine the results into a summary dataframe
hourly_summary = pd.DataFrame({
    'hour': [f"{x:02d}:00-{x:02d}:59" for x in range(24)],
    'mean': hourly_mean.values,
    'std': hourly_std.values
})

hourly_summary.to_csv('./setting/ersimulation_default.csv', index=False)

# Filter rows where s_disposition is 'admission'
admission_df = ersim_df[ersim_df['s_disposition'] == 'admission']

admission_df['DISCHARGE_DATE'] = admission_df['s_DISCHARGEDATETIME'].dt.date
admission_df['DISCHARGE_HOUR'] = admission_df['s_DISCHARGEDATETIME'].dt.hour
admission_df['DISCHARGE_DAY'] = admission_df['s_DISCHARGEDATETIME'].dt.dayofweek
# Group by day of week and hour, then count the number of admissions
admission_counts_by_hour = admission_df.groupby(['DISCHARGE_DATE','DISCHARGE_DAY', 'DISCHARGE_HOUR']).size().reset_index(name='admission_count')

# Group by day of week and hour, then calculate mean and std for the number of admissions
admission_day_hourly_stats = admission_counts_by_hour.groupby(['DISCHARGE_DAY', 'DISCHARGE_HOUR'])['admission_count'].agg(['mean', 'std']).reset_index()

# Map days of the week for readability and create a column for the hour range
admission_day_hourly_stats['DISCHARGE_DAY'] = admission_day_hourly_stats['DISCHARGE_DAY'].map(day_map)
admission_day_hourly_stats['hour_range'] = admission_day_hourly_stats['DISCHARGE_HOUR'].apply(lambda x: f"{x:02d}:00-{x:02d}:59")

# Reorder and rename columns for clarity
admission_day_hourly_stats = admission_day_hourly_stats[['DISCHARGE_DAY', 'hour_range', 'mean', 'std']]
admission_day_hourly_stats.columns = ['Day', 'Hour', 'Mean', 'Std']
admission_day_hourly_stats.to_csv('./settings/admission_default.csv', index=False)

