import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns

# Parameters
#resolution 0.04 degre
#lat 51.5 - 42.0  = 9.5 degre -> 9.5/0.04 = 237.5 ~ 237
#lon 16 - 5.0 = 11 degre -> 11/0.04 = 275
domain_size = (237, 275)   # (height, width) - (lat, lon)
crop_size = (100, 100)       # (height, width) - (lat, lon)
crop_counts = [2, 3, 4, 5] # number of crops per experiment
n_samples = 1000           # number of random trials per crop count
out_plot = '/home/Daniele/codes/ML_data_generator/overlapping/'

rng = np.random.default_rng(42)

def random_crop_positions(domain_size, crop_size, n_crops):
    """Generate random top-left corners for n_crops within domain bounds."""
    H, W = domain_size
    h, w = crop_size
    xs = rng.integers(0, W - w + 1, n_crops)
    ys = rng.integers(0, H - h + 1, n_crops)
    return list(zip(xs, ys))

def compute_overlap_mask(domain_size, crop_positions, crop_size):
    """Compute overlap mask given crop positions."""
    mask = np.zeros(domain_size, dtype=int)
    h, w = crop_size
    for (x, y) in crop_positions:
        mask[y:y+h, x:x+w] += 1
    return mask

def plot_example(domain_size, crop_positions, crop_size, n_crops):
    """Visualize crops on domain."""
    H, W = domain_size
    fig, ax = plt.subplots(figsize=(4,4))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect('equal')
    colors = sns.color_palette("husl", n_crops)
    for (x, y), c in zip(crop_positions, colors):
        rect = patches.Rectangle((x, y), crop_size[1], crop_size[0],
                                 linewidth=2, edgecolor=c, facecolor='none', alpha=0.8)
        ax.add_patch(rect)
    ax.set_title(f"{n_crops} random crops")
    ax.invert_yaxis()
    plt.tight_layout()
    return fig, ax

# Compute overlap statistics
overlap_results = {}

for n_crops in crop_counts:
    overlaps = []
    for _ in range(n_samples):
        positions = random_crop_positions(domain_size, crop_size, n_crops)
        mask = compute_overlap_mask(domain_size, positions, crop_size)
        overlap_fraction = np.sum(mask >= 2) / mask.size
        overlaps.append(overlap_fraction)
    overlap_results[n_crops] = overlaps

# ---- Plot examples ----
n_examples = 5  # number of random examples (rows)
fig_ex, axs = plt.subplots(
    n_examples, len(crop_counts),
    figsize=(3 * len(crop_counts), 3 * n_examples),
    squeeze=False
)

for i in range(n_examples):
    for j, n_crops in enumerate(crop_counts):
        ax = axs[i, j]
        pos = random_crop_positions(domain_size, crop_size, n_crops)
        colors = sns.color_palette("husl", n_crops)
        for (x, y), c in zip(pos, colors):
            rect = patches.Rectangle(
                (x, y), crop_size[1], crop_size[0],
                linewidth=2, edgecolor=c, facecolor='none', alpha=0.8
            )
            ax.add_patch(rect)
        ax.set_xlim(0, domain_size[1])
        ax.set_ylim(0, domain_size[0])
        ax.invert_yaxis()
        if i == 0:
            ax.set_title(f"{n_crops} crops", fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])

plt.savefig(out_plot + "example_random_crops_grid.png", dpi=200, bbox_inches='tight')



# # ---- Plot overlap distributions ----
# plt.figure(figsize=(8, 4))
# data = [overlap_results[n] for n in crop_counts]
# plt.boxplot(data, labels=crop_counts, patch_artist=True)
# plt.xlabel("Number of crops")
# plt.ylabel("Overlap fraction (pixels ≥ 2 crops)")
# plt.title("Overlap distribution vs number of crops")
# plt.savefig(out_plot + "overlap_distribution.png")

# # ---- Plot average overlap ----
# means = [np.mean(overlap_results[n]) for n in crop_counts]
# plt.figure(figsize=(6, 4))
# plt.plot(crop_counts, means, marker='o')
# plt.xlabel("Number of crops")
# plt.ylabel("Mean overlap fraction")
# plt.title("Average overlap vs number of crops")
# plt.grid(True, alpha=0.3)
# plt.savefig(out_plot + "average_overlap.png")
