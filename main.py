import matplotlib.pyplot as plt
import seaborn as sns

import importer as i
from config import moving_average_weeks

# load in data to graph
i.main()

# add black background
plt.rcParams['axes.facecolor'] = 'black'

# assign axis and chart-size
fig, ax = plt.subplots(figsize=[12, 5])

# create line chart for the two assets, on one axis
for asset, color in {f'{i.asset1_name}': '#F7931A', f'{i.asset2_name}': '#FFD700'}.items():
    sns.lineplot(
        data=i.cross_compare,
        x='Date',
        y=i.cross_compare[f'{asset} Portfolio Value Rolling Sum'].rolling(
                moving_average_weeks if moving_average_weeks > 0 else 1,
                min_periods=0
            ).mean(),
        linewidth=4,
        color=color,
        label=asset.upper()
    )

# add title
plt.title(
    f'{i.asset1_name.upper()} vs {i.asset2_name.upper()}: '
    f'{i.range_of_report_yrs} years DCA ({moving_average_weeks}-wk MA)',
    fontsize=12
)

# format x labels
plt.xlabel('')

# format y labels
plt.ylabel('Portfolio Value')
ax.grid(axis='y', color='darkgray', linestyle='dotted')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: f"${x:,.0f}"))

# apply legend
ax.legend(labelcolor='white', loc='upper left')

# add creator signature
ax.text(.01, .01, 'D. Taygunov', color='white', fontsize=8, style='italic', transform=ax.transAxes)

# create text box with results summary from simulation
results = f"Total initial investment: ${i.total_usd_invested:,.0f}\n\n" \
       f"Ending {i.asset1_name.upper()}:" \
       f" {i.ending_units_asset1.round(1)} {i.asset1_name.upper()} " \
       f"(${i.ending_usd_asset1:,.0f})\n" \
       f"Real RoI: {int(i.real_roi_asset1)}%\n\n" \
       f"Ending {i.asset2_name.upper()}: {i.ending_units_asset2.round(1)} " \
       f"(${i.ending_usd_asset2:,.0f})\n" \
       f"Real RoI: {int(i.real_roi_asset2)}%\n\n" \
       f"Correlation; {i.correl}\n" \
       f"Magnitude: 1:{i.slope}"

results_no_inflation = f"Total initial investment: ${i.total_usd_invested:,.0f}\n\n" \
          f"Ending {i.asset1_name.upper()}:" \
          f" {i.ending_units_asset1.round(1)} {i.asset1_name.upper()} " \
          f"(${i.ending_usd_asset1:,.0f})\n" \
          f"Nominal RoI {i.asset1_name.upper()}: {int(i.nom_roi_asset1)}%\n\n" \
          f"Ending {i.asset2_name.upper()}: {i.ending_units_asset2.round(1)} " \
          f"(${i.ending_usd_asset2:,.0f})\n" \
          f"Nominal RoI {i.asset2_name.upper()}: {int(i.nom_roi_asset2)}%\n\n" \
          f"Correlation; {i.correl}\n" \
          f"Magnitude: 1:{i.slope}"

# apply summary to text box
ax.text(
    0.01,
    0.375,
    results_no_inflation if i.DCA_asset1.cpi_starting == 0 or i.DCA_asset2.cpi_ending == 0 else results,
    color='white',
    bbox=dict(
        facecolor='black',
        boxstyle='round',
        edgecolor='white'
    ),
    fontsize=9,
    transform=ax.transAxes
)

# finalize/save
plt.tight_layout()
plt.show()
# plt.savefig(os.path.join(directory, "3426t343.jpg"))
