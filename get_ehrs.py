import pandas as pd
import numpy as np

# Read in the data
# df = pd.read_csv('../data_ehr548/C548_15_PATIENTTRIAGE.txt', sep='\t')

df = pd.read_pickle('../data_ehr548/vs_supervise_20221019_b.pdpkl')

selected = ['PERSONID2', 'ACCOUNTIDSE2', 'ACCOUNTSEQNO', 'ASSIGNAREA',  'TRIAGE', 
            's_TRIAGEDATETIME', 's_REGISTERDATETIME',
       's_DIAGNOSISDATETIME', 's_ALLOWDISCHARGEDATETIME',
       's_DISCHARGEDATETIME', 's_HOSPITALCODE',
       's_DEPTCODE', 's_disposition',]

df2 = df[selected]
df2.to_csv('../data_ehr548/c548_T0_ERSim.csv', index=False)