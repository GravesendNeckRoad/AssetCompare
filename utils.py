import logging
import os
import math
from sys import exit
from typing import List, Literal, Tuple

import numpy as np
import pandas as pd

from config import asset1_name, asset2_name

logging.basicConfig(level=logging.INFO, format='Error: %(message)s')


class DataImport:
    """Used to import price-action data of two assets, and prepare them for the weekly DCA investment simulator."""
    def __init__(self, main_directory):
        self.main_directory = main_directory
        self.imported_df = self._import_price_action_csv()
        self.df1 = self.imported_df[0]
        self.df2 = self.imported_df[1]
        self.df = self.join_dfs_and_pivot_weekly()

    def _import_price_action_csv(self) -> List[pd.DataFrame]:
        """
        Creates a list of DataFrames from .csv files, assuming each has a 'Date' and 'Close' column.
        One .csv per asset, and both must be located inside the project root directory.
        """
        df = []
        # order matters: need to assign assets to df in order, so the indexing is maintained for the rest of the script
        for asset in [asset1_name, asset2_name]:
            for _file in os.listdir(self.main_directory):
                file_path = os.path.join(self.main_directory, _file)
                # if file_path.endswith('.csv'):
                if _file.upper().__contains__(asset.upper()) and _file.endswith('csv'):
                    test_import = pd.read_csv(file_path, nrows=1, encoding='latin1').columns
                    if 'Date' in test_import and 'Close' in test_import:
                        df.append(pd.read_csv(
                            file_path,
                            usecols=['Date', 'Close'],
                            parse_dates=['Date'],
                            encoding='latin1')
                        )

        # Making sure both df's are read. Any other errors will be passed to parent method - will exception-catch there.
        if len(df) < 2:
            logging.error(" Check your directory to ensure there are 2 csv files - one for each asset - and that each "
                          "contains the required columns - 'Date' and 'Close'.\n"
                          "\t\tAlso, make sure that the asset variables in config.py correspond to the names of the "
                          "assets you are running this report for.")
            exit(1)
            # NOTE: .error will terminate program but .exception will still run it, giving you NoneType: None
            # even if an exit() follows it
        return df

    def determine_date_range(self) -> List:
        """
        Returns a 3-item list containing the start/end dates of the price-history data, as well as total years elapsed.
        Exactly 2 csv files are required. Both assets must start/end on the same date, the date range(s) must be >=1Y.
        """
        try:
            if (
                self.imported_df[0]['Date'].dt.date.min() == self.imported_df[1]['Date'].dt.date.min() and
                self.imported_df[0]['Date'].dt.date.max() == self.imported_df[1]['Date'].dt.date.max()
            ):
                start_date = self.imported_df[0]['Date'].dt.date.min()
                end_date = self.imported_df[0]['Date'].dt.date.max()
                report_date_range_in_years = round((end_date - start_date).days / 365, 2)
                n_dfs_imported = len(self.imported_df)

                if report_date_range_in_years < 1:
                    logging.error("To run this report, ensure that your dataset has at least 1 year of price history. "
                                  f"You've provided just {(end_date - start_date).days} days worth.\n\n")
                    exit(1)

                elif n_dfs_imported > 2:
                    logging.error(f"Detected {n_dfs_imported} assets in your DataImport. Only 2 are allowed. "
                                  f"Delete any extra .csv files in your root directory and try again.")
                    exit(1)

                return [start_date, end_date, report_date_range_in_years]

            else:
                logging.error("The date-ranges of the two data sets do not match. "
                              "For this report to run, both datasets must start & end on the same dates.")
                exit(1)
        except AttributeError:
            logging.exception("There appears to be 1 or more improperly formatted dates in your dataset.\n\n")
            exit(1)
        except IndexError:
            logging.exception("Check to make sure there are exactly 2 .csv files with price data in your directory, "
                              "and that each file contains at least a 'Date' and 'Close' column (case sensitive).\n\n")
            exit(1)
        except TypeError:
            logging.exception("The dates in your datasets may be formatted improperly, or there might be some "
                              "whitespace in an empty column. Clean your data and try again.\n\n")
            exit(1)

    def join_dfs_and_pivot_weekly(
            self,
            join_method: Literal['left', 'right', 'inner', 'outer', 'cross'] = None
    ) -> pd.DataFrame:

        """
        Merges the 2 price-history df's, then calculates the mean weekly closing price for each asset.

        :param: join_method: the join method (left, right, inner, outer, cross)
        :return: (pd.DataFrame) 3 columns; Year-Week, Asset1 mean closing price, and Asset2 mean closing price.
        """

        # since this method is eager loaded, you need the param to have a default this way:
        if join_method is None:
            join_method = 'outer'

        # Join the two df's on the date column.
        merged_df = \
            pd.merge(
                self.df1,
                self.df2,
                on='Date',
                how=join_method  # some assets trade on weekends, while others don't. Hence, outer join is preferred.
            ).rename({'Close_x': f'{asset1_name} Close', 'Close_y': f'{asset2_name} Close'}, axis=1) \
            .reset_index() \
            [['Date', f'{asset1_name} Close', f'{asset2_name} Close']]

        # Create pivot table by year/week, with average weekly closing price.
        piv = merged_df.resample('W-MON', on='Date').mean().reset_index()

        # round the newly created value columns
        piv.iloc[:, -2:] = piv.iloc[:, -2:].round(2)

        return piv

    def export_df(self, output_directory) -> None:
        """
        Returns .xlsx file with 3 sheets: the merged df from pivot() method, and the original data of the two assets."""
        import os

        with pd.ExcelWriter(os.path.join(output_directory)) as writer:
            self.df.to_excel(writer, sheet_name=f'by week - {asset1_name} x {asset2_name}', index=False)
            self.df1.to_excel(writer, sheet_name=f'raw data - {asset1_name}', index=False)
            self.df2.to_excel(writer, sheet_name=f'raw data - {asset2_name}', index=False)


class RunSimulator:
    """
    Runs a DCA simulation based on an assets weekly average price history, and a fixed reoccurring investment amount.

    :param df: The DataFrame you created in the `join_dfs_and_pivot_weekly` method of the `DataImport` class
    :param asset_name: the name of the asset (ex: 'BTC' or 'XAU')
    :param weekly_investment: the static dollar amount to invest weekly
    """

    # these attributes are returned from `cpi_scrape()`, which are then passed to `inflation_rate()`
    cpi_starting = None
    cpi_ending = None
    inflation_is_zero = False

    def __init__(self, df: pd.DataFrame, asset_name: str, weekly_investment: int) -> None:
        self.df = df
        self.asset_name = asset_name
        self.weekly_investment = weekly_investment

    def rolling_totals(self) -> None:
        """Creates 3 new columns for the df -
            1. Purchase Amount: how much of the asset was purchased each week with the fixed weekly investment
            2. Rolling Sum: how much asset you have accumulated in your portfolio by that given week
            3. Portfolio Value: your portfolio value over time, using the most recent weekly average price
        """
        try:
            # 1. Create column of amount purchased each given week (fixed investment amount / asset price that week)
            self.df[f'{self.asset_name} Weekly Purchase'] = \
                (self.weekly_investment/self.df[f'{self.asset_name} Close']).round(2)

            # 2. Create column of asset accumulated over time (rolling sum of weekly purchase column)
            n_weeks = len(self.df[f'{self.asset_name} Weekly Purchase'])
            self.df[f'{self.asset_name} Rolling Sum'] = \
                self.df[f'{self.asset_name} Weekly Purchase'].rolling(n_weeks, min_periods=0).sum()

            # 3. Same as step 2, but denominated in USD (weekly closing price * asset accumulated by that given week)
            self.df[f'{self.asset_name} Portfolio Value Rolling Sum'] = \
                (self.df[f'{self.asset_name} Rolling Sum'] * self.df[f'{self.asset_name} Close']).round(2)

        except (TypeError, KeyError):
            logging.exception("Please check your weekly_investment and df parameters in the rolling_totals method.")
            exit(1)

    def total_asset_purchased(self) -> float:
        """Returns the total quantity of asset you have purchased over the entire date range."""
        return self.df[f'{self.asset_name} Weekly Purchase'].sum().round(2)

    def total_usd_invested(self) -> float:
        """Returns the total USD invested over the date range."""
        return (self.df['Date'].count() * self.weekly_investment).round(2)

    def ending_investment_value(self) -> float:
        """Returns the ending portfolio value in USD that you have on the last week of the date range."""
        return (
            self.df.query("Date == Date.max()")[f'{self.asset_name} Portfolio Value Rolling Sum'].values[0]
        ).round(2)

    def nominal_roi(self) -> float:
        """Returns the nominal rate of return of the date range for the asset in your df."""
        total_invested = self.total_usd_invested()
        current_investment_value = self.ending_investment_value()
        return round(((current_investment_value - total_invested) / total_invested)*100, 2)

    def real_roi(self) -> float:
        """Returns the real rate of return by factoring in inflation using the Fisher equation."""
        inflation_rate_as_decimal = self.inflation_rate()/100
        nominal_roi_as_decimal = self.nominal_roi()/100
        fisher_equation = ((1+nominal_roi_as_decimal) / (1+inflation_rate_as_decimal)) - 1
        return round(fisher_equation*100, 2)

    def usd_return_inflation_adjusted(self) -> float:
        """Returns the USD returned on your investment, priced in starting dollars (inflation adjusted)."""
        real_roi_as_decimal = self.real_roi()/100
        return round(self.total_usd_invested() * (1+real_roi_as_decimal), 2)

    @staticmethod
    def cpi_scrape(start, end) -> Tuple[float, float]:
        """
        Returns the starting and ending CPI from government stats, and based on date range from DataImport.
        :return [cpi_starting, cpi_ending] - also saves these vars as class attributes
        """
        try:
            start = pd.to_datetime(start)
            end = pd.to_datetime(end)
            url = "https://www.usinflationcalculator.com/inflation/" \
                  "consumer-price-index-and-annual-percent-changes-from-1913-to-2008/"

            # import/wrangle CPI table
            df = pd.read_html(url)[0]
            df.columns = df.iloc[1]
            df = df.iloc[2:, :-4]
            df = df.melt(id_vars='Year')\
                .rename({1: 'Month'}, axis=1)

            # map dates, so pandas can work with them
            df['Month'] = df['Month'].map(
                {
                    'Jan': 1,
                    'Feb': 2,
                    'Mar': 3,
                    'Apr': 4,
                    'May': 5,
                    'June': 6,
                    'July': 7,
                    'Aug': 8,
                    'Sep': 9,
                    'Oct': 10,
                    'Nov': 11,
                    'Dec': 12
                }
            )

            # return the values that correspond to the min/max of the df's date range
            _cpi_starting_fetch = df.iloc[:, -1].loc[
                (df['Year'] == str(start.year)) &
                (df['Month'] == start.month)
                ].iloc[0]

            _cpi_ending_fetch = df.iloc[:, -1].loc[
                (df['Year'] == str(end.year)) &
                (df['Month'] == end.month)
                ].iloc[0]

            if math.isnan(float(_cpi_starting_fetch)) or math.isnan(float(_cpi_ending_fetch)):
                print("\nWarning: Couldn't locate a valid CPI for this date range. "
                      "Report will proceed assuming 0 inflation.\n")
                RunSimulator.cpi_starting = float(0)
                RunSimulator.cpi_ending = float(0)
                return RunSimulator.cpi_starting, RunSimulator.cpi_ending

            RunSimulator.cpi_starting = float(_cpi_starting_fetch)
            RunSimulator.cpi_ending = float(_cpi_ending_fetch)
            return RunSimulator.cpi_starting, RunSimulator.cpi_ending

        except (ValueError, IndexError, TypeError):
            RunSimulator.cpi_starting = float(0)
            RunSimulator.cpi_ending = float(0)
            return RunSimulator.cpi_starting, RunSimulator.cpi_ending

    @staticmethod
    def inflation_rate() -> float:
        """Returns the inflation rate based on starting and ending CPI, as defined in config.py"""
        try:
            if RunSimulator.cpi_ending > 0 and RunSimulator.cpi_starting > 0:
                return round(((RunSimulator.cpi_ending - RunSimulator.cpi_starting) / RunSimulator.cpi_starting)*100, 1)
            else:
                return 0
        except (ImportError, TypeError, ZeroDivisionError):
            logging.exception("Please enter valid float values for the starting/ending CPI.")
            exit(1)

    @staticmethod
    def correlation(df) -> Tuple[float, int]:
        """Returns the slope and correlation of the two assets from the df created with the `DataImport` class"""
        try:
            asset1_weekly_price_column = df[f'{asset1_name} Close']
            asset2_weekly_price_column = df[f'{asset2_name} Close']

            correl = asset1_weekly_price_column.corr(asset2_weekly_price_column).round(2)
            slope1, intercept1 = (np.polyfit(asset2_weekly_price_column, asset1_weekly_price_column, 1))
            slope2, intercept2 = (np.polyfit(asset1_weekly_price_column, asset2_weekly_price_column, 1))

            return correl, int(slope1) if slope1 > slope2 else int(slope2)

        except np.linalg.LinAlgError:
            logging.exception("Numpy cannot parse the values in one of the columns.\n"
                              "Try passing method='inner' to the `join_dfs_and_pivot_weekly` method in importer.py, "
                              "to exclude any potentially troublesome rows.\n"
                              "Older datasets are difficult to parse as they were more sparsely recorded - "
                              "try a more recent data range.")
            exit(1)
