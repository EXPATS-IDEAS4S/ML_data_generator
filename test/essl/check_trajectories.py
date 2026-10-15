import pandas as pd
import os

#from data_utils import haversine_km
from plot_utils import trajectory_diagnostics_plot, trajectory_diagnostics_stats

path_trajectories = "/home/Daniele/codes/ML_data_generator/test/essl/storm_trajectories_after_merge.csv"
path_grouped = "/home/Daniele/codes/ML_data_generator/test/essl/events_grouped.csv"
path_summary = "/home/Daniele/codes/ML_data_generator/test/essl/events_summary.csv"

df_traj = pd.read_csv(path_trajectories)
df_grouped = pd.read_csv(path_grouped)
df_summary = pd.read_csv(path_summary)
print(df_grouped.columns.tolist())
print(df_summary.columns.tolist())
exit()

output_dir = "/home/Daniele/codes/ML_data_generator/test/essl/trajectories_merged/"
os.makedirs(output_dir, exist_ok=True)

print("Trajectories:")
print(df_traj.head())
print(df_traj.columns.tolist())
exit()
# print("\nGrouped events:")
# print(df_grouped.head())
# print("\nSummary:")
# print(df_summary.head())

#print some statistics of the trajectories
# n_trajectories = df_traj["storm_id"].nunique()
# print(f"\nNumber of unique storm trajectories: {n_trajectories}")
# lifetime_stats = df_traj.groupby("storm_id").size().describe()
# print("\nStorm lifetime statistics (in number of events):")
# print(lifetime_stats)
# #compute number of trajectories per storm type
# type_counts = df_traj.groupby("storm_type")["storm_id"].nunique()
# print("\nNumber of unique storm trajectories per event type:")
# print(type_counts)
# #compute number of trajectories that had type transitions
# type_transition_counts = df_traj.groupby("storm_id")["type_transition"].max().values.sum()
# print("\nNumber of unique storm trajectories with type transitions:")
# print(type_transition_counts)
# #compute average distance traveled by each trajectory

# def compute_trajectory_distance(traj):
#     traj = traj.sort_values("time")
#     total_distance = 0.0
#     for i in range(1, len(traj)):
#         lat1, lon1 = traj.iloc[i-1][["lat", "lon"]]
#         lat2, lon2 = traj.iloc[i][["lat", "lon"]]
#         distance = haversine_km(lat1, lon1, lat2, lon2)
#         total_distance += distance
#     return total_distance   

# distance_stats = df_traj.groupby("storm_id").apply(compute_trajectory_distance).describe()
# print("\nStorm trajectory distance statistics (in km):")
# print(distance_stats)

# #statistics on interplotated, exptrapolated observed points
# n_total_points = len(df_traj)
# n_interpolated_points = len(df_traj[df_traj["source"] == "interpolated"])
# n_extrapolated_points = len(df_traj[df_traj["source"] == "extrapolated"])
# print(f"\nTotal number of trajectory points: {n_total_points}")
# print(f"Number of interpolated trajectory points: {n_interpolated_points} ({n_interpolated_points / n_total_points * 100:.2f}%)")
# print(f"Number of extrapolated trajectory points: {n_extrapolated_points} ({n_extrapolated_points / n_total_points * 100:.2f}%)")


# trajectory_diagnostics_plot(
#     df_traj,
#     storm_id_col="merged_storm_id",
#     n_days=20,
#     domain=(5, 16, 42, 51.5),
#     res_deg=0.04,
#     crop_pixels=100,
#     seed=12,
#     output_dir=output_dir,
# )

trajectory_diagnostics_stats(
    df_traj,
    storm_id_col="merged_storm_id",
    time_col="time",
    lat_col="lat",
    lon_col="lon",
    type_col="cluster_event_type",
    source_col="source",
    intensity_col="max_intensity",   # can be None or mean_intensity
    output_dir=output_dir,
)