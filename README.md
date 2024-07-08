_________________________________________________________________________________________
Description;

This script is a DCA calculator that takes two csv files, each containing historic prices for some assets/stocks, and returns a comparisson of how much money you'd have grossed if you dollar-cost-averaged a fixed sum of money every week for the duration of the date range in the csv's.

Example: Say you invested $50 in both gold and bitcoin every week from 2020 to 2024. This report will return a graph showing your portfolio USD value over time, and provide some stats such as % return over time, inflation adjusted return. (You must download historic price data of BTC and Gold for the time period from 2020 to 2024 on your own accord).
 
utils.py -  contains classes DataImport and RunSimulation. The former reads in your csv's and the latter runs the DCA experiment

importer.py - runs the classes from utils 

config.py - contains the critical values the end user should adjust, such as $$ invested weekly, and name of the assets 

main.py - runs the importer.py, and generates the chart
_________________________________________________________________________________________
