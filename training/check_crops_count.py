import os
from datetime import datetime, timedelta

# === CONFIG ===
base_dir = "/data1/crops/ir108_100x100_2013-2020_3xrandomcrops_1xtimestamp_cma_nc/nc/1"
start_year, end_year = 2013, 2020
months_to_check = [4,5,6,7,8,9]  # April to September
minutes_step = 15
num_crops = 3  # 0, 1, 2

# === GENERATE EXPECTED FILENAMES ===
expected_files = []

for year in range(start_year, end_year + 1):
    for month in months_to_check:
        # get the first and last day of the month
        start_date = datetime(year, month, 1, 0, 0)
        # find next month to stop
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # iterate every 15 minutes
        t = start_date
        while t < end_date:
            # build expected filenames for 3 crops
            timestamp_str = t.strftime("%Y-%m-%dT%H:%M:%S")
            for crop_id in range(num_crops):
                filename = f"{timestamp_str}_{crop_id}.nc"
                expected_files.append(filename)
            t += timedelta(minutes=minutes_step)

# === CHECK WHICH FILES EXIST ===
existing_files = set(os.listdir(base_dir))
missing_files = [f for f in expected_files if f not in existing_files]

# === SUMMARY ===
print(f"Total expected files: {len(expected_files)}")
print(f"Existing files: {len(existing_files)}")
print(f"Missing files: {len(missing_files)}")

# Optionally save the list of missing files
if missing_files:
    with open("missing_files.txt", "w") as f:
        for m in missing_files:
            f.write(m + "\n")
    print("Missing files list saved to missing_files.txt")
else:
    print("✅ All expected files are present!")
