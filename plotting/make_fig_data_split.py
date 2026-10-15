import os
import re
import glob
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter

# -------------------------
# Paths
# -------------------------
TRAIN_DIR = "/data1/crops/ir108_100x100_2013-2017-2021-2025_2xrandomcrops_1xtimestamp_cma_nc/nc/1"
TEST_DIR  = "/data1/crops/test_case_essl_14-15-16-18-19-20-22-23-24_100x100_ir108_cma_traj/nc/1"

REPORT_FILE = (
    "/data1/fig/dcv2_resnet_k7_ir108_100x100_2013-2017-2021-2025_2xrandomcrops_1xtimestamp_cma_nc/"
    "epoch_800/test/essl_reports/eswd-v2-2012-2025_expats.csv"
)

OUT_DIR = "/data1/fig/dcv2_resnet_k7_ir108_100x100_2013-2017-2021-2025_2xrandomcrops_1xtimestamp_cma_nc/epoch_800/"

# -------------------------
# Helpers
# -------------------------
DATE_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}")

def extract_date_from_filename(fname):
    """Extract YYYY-MM-DD from filename."""
    match = DATE_REGEX.search(fname)
    if match:
        return pd.to_datetime(match.group())
    return None


def daily_counts_from_dir(directory):
    files = glob.glob(os.path.join(directory, "*.nc"))
    dates = [extract_date_from_filename(os.path.basename(f)) for f in files]
    dates = [d for d in dates if d is not None]
    return (
        pd.Series(dates)
        .dt.floor("D")
        .value_counts()
        .sort_index()
    )

# -------------------------
# ESWD reports (daily events)
# -------------------------
df_reports = pd.read_csv(REPORT_FILE, low_memory=False)
df_reports["TIME_EVENT"] = (
    pd.to_datetime(df_reports["TIME_EVENT"])
    .dt.tz_localize(None)
)

#include onlu events in years 2014,15,16,18,19,20,22,23,24
df_reports = df_reports[df_reports["TIME_EVENT"].dt.year.isin([2014,2015,2016,2018,2019,2020,2022,2023,2024])]
#include only events in APril to September
df_reports = df_reports[df_reports["TIME_EVENT"].dt.month.isin([4,5,6,7,8,9])]


# -------------------------
# Training & test samples
# -------------------------
train_daily = daily_counts_from_dir(TRAIN_DIR)
test_daily  = daily_counts_from_dir(TEST_DIR)

# Align index
#all_days = train_daily.index.union(test_daily.index)

report_days = (
    df_reports["TIME_EVENT"]
    .dt.floor("D")
    .unique()
)

all_days = (
    train_daily.index
    .union(test_daily.index)
    .union(pd.to_datetime(report_days))
    .sort_values()
)


train_daily = train_daily.reindex(all_days, fill_value=0)
test_daily  = test_daily.reindex(all_days, fill_value=0)



report_daily = (
    df_reports["TIME_EVENT"]
    .dt.floor("D")
    .value_counts()
    .sort_index()
    .reindex(all_days, fill_value=0)
)



# -------------------------
# Trajectories per day (test set)
# -------------------------
# Assuming one trajectory per storm file
traj_dates = [
    extract_date_from_filename(os.path.basename(f))
    for f in glob.glob(os.path.join(TEST_DIR, "*.nc"))
]
traj_dates = [d for d in traj_dates if d is not None]

traj_daily = (
    pd.Series(traj_dates)
    .dt.floor("D")
    .value_counts()
    .sort_index()
    .reindex(all_days, fill_value=0)
)


# Keep only Apr–Sep
def is_apr_sep(dt):
    return dt.month >= 4 and dt.month <= 9

valid_days = [d for d in all_days if is_apr_sep(d)]

# Create a compressed integer x-axis
day_to_x = {day: i for i, day in enumerate(valid_days)}
x_vals = pd.Series(day_to_x)

def map_to_x(series):
    return series.index.map(day_to_x)

x_train = map_to_x(train_daily)
x_test  = map_to_x(test_daily)
x_rep   = map_to_x(report_daily)
x_traj  = map_to_x(traj_daily)
print(x_train)
print(x_test)   


year_midpoints = {}
for year in sorted({d.year for d in valid_days}):
    days_in_year = [d for d in valid_days if d.year == year]
    if days_in_year:
        mid_day = days_in_year[len(days_in_year)//2]
        year_midpoints[year] = day_to_x[mid_day]

# -------------------------
# Plot
# -------------------------
fig, axes = plt.subplots(
    2, 1, figsize=(15, 10), sharex=True,
    gridspec_kw=dict(hspace=0.15)
)

# # --- alternating year shading ---
# for i, year in enumerate(sorted(year_midpoints)):
#     days = [d for d in valid_days if d.year == year]
#     x0 = day_to_x[days[0]]
#     x1 = day_to_x[days[-1]]
#     if i % 2 == 0:
#         for ax in axes:
#             ax.axvspan(x0, x1, color="0.9", zorder=0)

# --- Row 1: samples per day ---
axes[0].bar(
    x_train,
    train_daily.values,
    width=1,
    label="Training samples",
    color="#4C72B0"
)
axes[0].bar(
    x_test,
    test_daily.values,
    width=1,
    label="Test samples",
    color="#DD8452"
)

axes[0].set_ylabel("Samples / day")
axes[0].legend(frameon=False)

# --- Row 2: ESWD reports ---
axes[1].bar(
    x_rep,
    report_daily.values,
    width=1,
    color="black",
    alpha=0.7
)
axes[1].set_ylabel("ESWD events / day")

""" # --- Row 3: trajectories ---
axes[2].bar(
    x_traj,
    traj_daily.values,
    width=1,
    color="#55A868"
)
axes[2].set_ylabel("Trajectories / day")
"""
# -------------------------
# X-axis formatting
# -------------------------
axes[1].xaxis.set_major_locator(MonthLocator())
axes[1].xaxis.set_major_formatter(DateFormatter("%Y-%m"))

for ax in axes:
    ax.grid(ls="--", alpha=0.3)

axes[1].set_xlabel("Time (Year–Month)")




plt.savefig(f"{OUT_DIR}fig_data_split.png", dpi=300, bbox_inches="tight")
plt.close()
