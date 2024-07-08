import os
from math import isnan

from utils import DataImport, RunSimulator
from config import asset1_name, asset2_name, weekly_investment

DCA_asset1 = None
DCA_asset2 = None
cross_compare = None
start_date = None
end_date = None
range_of_report_yrs = None
total_usd_invested = None
ending_units_asset1 = None
ending_units_asset2 = None
ending_usd_asset1 = None
ending_usd_asset2 = None
nom_roi_asset1 = None
nom_roi_asset2 = None
real_roi_asset1 = None
real_roi_asset2 = None
correl = None
slope = None


def main():
    global DCA_asset1, DCA_asset2, cross_compare, start_date, end_date, range_of_report_yrs, correl, slope, \
        total_usd_invested, ending_units_asset1, ending_units_asset2, ending_usd_asset1, ending_usd_asset2, \
        real_roi_asset1, real_roi_asset2, nom_roi_asset1, nom_roi_asset2

    main_dir = os.path.dirname(__file__)
    output_path = os.path.join(main_dir, "Raw Data.xlsx")

    # instantiate data import
    run = DataImport(main_directory=main_dir)

    # determine date range
    start_date, end_date, range_of_report_yrs = run.determine_date_range()
    print(f"Running report for date range: {start_date} through {end_date}, spanning {range_of_report_yrs} years...")

    # determine CPI for time period (in order to determine inflation rate)
    RunSimulator.cpi_scrape(start_date, end_date)
    # print(f"The CPI for this date range is {RunSimulator.cpi_scrape(start_date, end_date)}")

    # pivot the data by year/week and obtain average weekly closing price
    cross_compare = run.join_dfs_and_pivot_weekly(join_method='inner')

    # quick EDA (optional)
    # print(cross_compare.head())
    # print(cross_compare.info())

    # export data to excel file (optional)
    # run.export_df(output_path)

    # unpack DCA investment simulation for asset 1
    DCA_asset1 = RunSimulator(cross_compare, asset1_name, weekly_investment)
    DCA_asset1.rolling_totals()
    ending_usd_asset1 = DCA_asset1.ending_investment_value()
    ending_units_asset1 = DCA_asset1.total_asset_purchased()
    nom_roi_asset1 = DCA_asset1.nominal_roi()
    real_roi_asset1 = DCA_asset1.real_roi()
    usd_return_inflation_adj_1 = DCA_asset1.usd_return_inflation_adjusted()

    # unpack DCA investment simulation for asset 2
    DCA_asset2 = RunSimulator(cross_compare, asset2_name, weekly_investment)
    DCA_asset2.rolling_totals()
    ending_usd_asset2 = DCA_asset2.ending_investment_value()
    ending_units_asset2 = DCA_asset2.total_asset_purchased()
    nom_roi_asset2 = DCA_asset2.nominal_roi()
    real_roi_asset2 = DCA_asset2.real_roi()
    usd_return_inflation_adj_2 = DCA_asset2.usd_return_inflation_adjusted()

    # static analytical variables
    total_usd_invested = DCA_asset1.total_usd_invested()
    inflation_rate = DCA_asset1.inflation_rate()
    correl = RunSimulator.correlation(cross_compare)[0]
    slope = RunSimulator.correlation(cross_compare)[1]

    # summary statements:
    # if CPI of 0 is detected, omit inflation stats
    if DCA_asset1.cpi_starting == 0 or DCA_asset2.cpi_ending == 0 \
            or isnan(DCA_asset1.cpi_starting) or isnan(DCA_asset2.cpi_ending):
        print(f"Weekly DCA of ${weekly_investment} for {range_of_report_yrs} years (assuming you market sell everything"
              f" on the week of {end_date}):\n"
              f"Total invested: ${total_usd_invested:,.0f}\n\n"
              f"RESULTS ${asset1_name.upper()}:\n"
              f"Ending Value: ${ending_usd_asset1:,.0f}\n"
              f"Ending Quantity: {ending_units_asset1} units of {asset1_name}\n"
              f"Nominal ROI: {nom_roi_asset1}%.\n\n"
              f"RESULTS ${asset2_name.upper()}:\n"
              f"Ending Value: ${ending_usd_asset2:,.0f}\n"
              f"Ending Quantity: {ending_units_asset2} units of {asset2_name}\n"
              f"Nominal ROI: {nom_roi_asset2}%\n\n"
              f"These two assets have a correlation of {correl}. "
              f"For every $1 increase in the weaker asset, the other increased by ~{slope}x.\n"
              )

    # otherwise, return the print statement with inflation stats
    else:
        print(f"\nWeekly DCA of ${weekly_investment} for {range_of_report_yrs} years (market sell on {end_date}):\n"
              f"Total invested: ${total_usd_invested:,.0f}\n"
              f"USD has lost {inflation_rate}% of its value over this period.\n\n"
              f"RESULTS ${asset1_name.upper()}:\n"
              f"Ending Value: ${ending_usd_asset1:,.0f}\n"
              f"Ending Quantity: {ending_units_asset1} units of {asset1_name}\n"
              f"Nominal ROI: {nom_roi_asset1}%\n"
              f"Real ROI: {real_roi_asset1}% - "
              f"That's ${usd_return_inflation_adj_1:,.0f} in {start_date.year} dollars.\n\n"
              f"RESULTS ${asset2_name.upper()}:\n"
              f"Ending Value: ${ending_usd_asset2:,.0f}\n"
              f"Ending Quantity: {ending_units_asset2} units of {asset2_name}\n"
              f"Nominal ROI: {nom_roi_asset2}%\n"
              f"Real ROI: {real_roi_asset2}% - "
              f"That's ${usd_return_inflation_adj_2:,.0f} in {start_date.year} dollars.\n\n"
              f"These two assets have a correlation of {correl}. "
              f"For every $1 increase in the weaker asset, the other increased by ~{slope}x.\n"
              )


if __name__ == '__main__':
    main()
