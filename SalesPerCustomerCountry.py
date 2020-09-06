# -*- coding: utf-8 -*-

from wepair.plugins.plugin import Plugin
from ...globals import COLNAMES_PE
from ...utils.location import Location
from os.path import join
import pandas as pd
import pickle
import inspect
from reportlab.platypus import Image
import plotly.io as pio
from ...utils.report import Report
from wepair.utils_common.log import Log

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'

TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']
CONSUMER_COUNTRY = COLNAMES_PE['Country (Consumer Address)']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']
TRANSACTION_REF_ID = COLNAMES_PE['Transaction Reference ID']


class SalesPerCustomerCountry(Plugin):

    def __init__(self, plugin_folder, id, options=None):
        self.plugin_name = "Sales Per Customer Country"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle']

    def process(self, *args, **kwargs):

        sales_per_customer_country = {'has_data': False}

        args = list(args)
        logger.debug(kwargs)

        if len(args) < 1:
            logger.warning('Fatal Error: Plugin Sales Per Customer Country: Transaction data Missing')
            return sales_per_customer_country

        location = Location(self.options['assets'])

        transactions = args[0]

        necessary_keys = [CONSUMER_COUNTRY, AMOUNT_IN_EUR, TRANSACTION_REF_ID,
                          TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]
        if not all(key in transactions.columns for key in necessary_keys):
            return sales_per_customer_country

        sales_per_customer_country = {'has_data': True}

        # Extract the data of interest
        
        columns_to_keep = [TRANSACTION_DATE, CONSUMER_COUNTRY, AMOUNT_IN_EUR, TRANSACTION_REF_ID,
                           TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]
        if TRANSACTION_DATE not in transactions.columns:
            logger.warning('{fct_name}: There is no column TRANSACTION_DATE. '
                            'Plotting results for the net sales will not be possible.'
                            .format(fct_name=inspect.stack()[0][3]))
            #removing only one attribute from the dataset above
            columns_to_keep.remove(TRANSACTION_DATE)
            #transactions should be 
        transactions = transactions[columns_to_keep]

        # Split the transaction set into gross sales and sales returns
        gross_sales_txs = transactions[transactions[TRANSACTION_IS_CAPTURE]].copy()
        #sum amount in euros by transaction ref_id
        gross_sales_txs['new_amount'] = gross_sales_txs.groupby(TRANSACTION_REF_ID)[AMOUNT_IN_EUR].transform('sum')
        gross_sales_txs = gross_sales_txs.drop_duplicates(subset=[TRANSACTION_REF_ID], keep='first') \
            .drop(AMOUNT_IN_EUR, axis=1) \
            .rename(columns={'new_amount': AMOUNT_IN_EUR})
            
# creation of the variable salses_returns_txs
        sales_returns_txs = transactions[transactions[TRANSACTION_IS_RETURN]].copy()
        sales_returns_txs['new_amount'] = sales_returns_txs.groupby(TRANSACTION_REF_ID)[AMOUNT_IN_EUR].transform('sum')
        sales_returns_txs = sales_returns_txs.drop_duplicates(subset=[TRANSACTION_REF_ID], keep='first') \
            .drop(AMOUNT_IN_EUR, axis=1) \
            .rename(columns={'new_amount': AMOUNT_IN_EUR})
#net sales had to be translated to data frame
        net_sales_txs = pd.DataFrame()
#merging gross_sales_txs and sales_returns_txs to calculate the net_sales_txs
        if len(gross_sales_txs) > 0 and len(sales_returns_txs) > 0:
            net_sales_txs = pd.merge(gross_sales_txs, sales_returns_txs[[TRANSACTION_REF_ID, AMOUNT_IN_EUR]],
                                     on=TRANSACTION_REF_ID, how='left')
            net_sales_txs.fillna(0, inplace=True)
            #subtract the amount_in_eur from left data source (x - this is a gross sale)
            #right data source (y- this is a sales returns txs)
            net_sales_txs[AMOUNT_IN_EUR] = net_sales_txs[AMOUNT_IN_EUR + '_x'] - net_sales_txs[AMOUNT_IN_EUR + '_y']
            net_sales_txs.drop([AMOUNT_IN_EUR + '_x', AMOUNT_IN_EUR + '_y'], axis=1, inplace=True)

        # Compute the gross sales per customer country
        # ------------------------------------------------
        if len(gross_sales_txs) > 0:
            sales_per_customer_country['gross_sales_has_data'] = True
            
            gross_sales = gross_sales_txs[[CONSUMER_COUNTRY, AMOUNT_IN_EUR]].copy()
            
            gross_sales = gross_sales.groupby(CONSUMER_COUNTRY).sum()
            gross_sales.reset_index(inplace=True)
            gross_sales.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            gross_sales['gross_sales_country_code'] = location.get_country_iso3(gross_sales, CONSUMER_COUNTRY).tolist()
            gross_sales['gross_sales_country_name'] = location.get_country_name(gross_sales, CONSUMER_COUNTRY).tolist()
            gross_sales_no_unknown = gross_sales[gross_sales['gross_sales_country_name'] != 'Unknown'].copy()
            gross_sales_no_unknown.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            sales_per_customer_country.update({
                'gross_sales_country_name': gross_sales['gross_sales_country_name'].astype(str).str.title().tolist(),
                'gross_sales_country_code': gross_sales['gross_sales_country_code'].tolist(),
                'gross_sales': gross_sales[AMOUNT_IN_EUR].tolist(),
                'gross_sales_country_name_no_unknown':
                    gross_sales_no_unknown['gross_sales_country_name'].astype(str).str.title().tolist(),
                'gross_sales_country_code_no_unknown': gross_sales_no_unknown['gross_sales_country_code'].tolist(),
                'gross_sales_no_unknown': gross_sales_no_unknown[AMOUNT_IN_EUR].tolist()
            })
            del gross_sales

        # Compute the sales returns per customer country
        # ------------------------------------------------
        # sales returns txs 
        if len(sales_returns_txs) > 0:
            sales_per_customer_country['sales_returns_has_data'] = True
            sales_returns = sales_returns_txs[[CONSUMER_COUNTRY, AMOUNT_IN_EUR]].copy()
            sales_returns = sales_returns.groupby(CONSUMER_COUNTRY).sum()
            sales_returns.reset_index(inplace=True)
            sales_returns.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            #why is this iso3 used here?
            sales_returns['sales_returns_country_code'] = location.get_country_iso3(sales_returns, CONSUMER_COUNTRY) \
                .tolist()
            sales_returns['sales_returns_country_name'] = location.get_country_name(sales_returns, CONSUMER_COUNTRY) \
                .tolist()
            sales_returns_no_unknown = sales_returns[sales_returns['sales_returns_country_name'] != 'Unknown'].copy()
            sales_returns_no_unknown.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            sales_per_customer_country.update({
                'sales_returns_country_name': sales_returns['sales_returns_country_name'].astype(
                    str).str.title().tolist(),
                'sales_returns_country_code': sales_returns['sales_returns_country_code'].tolist(),
                'sales_returns': sales_returns[AMOUNT_IN_EUR].tolist(),
                'sales_returns_country_name_no_unknown':
                    sales_returns_no_unknown['sales_returns_country_name'].astype(str).str.title().tolist(),
                'sales_returns_country_code_no_unknown': sales_returns_no_unknown[
                    'sales_returns_country_code'].tolist(),
                'sales_returns_no_unknown': sales_returns_no_unknown[AMOUNT_IN_EUR].tolist()
            })
            del sales_returns

        # Compute the net sales per customer country
        # ------------------------------------------------
        if len(net_sales_txs) > 0:
            sales_per_customer_country['net_sales_has_data'] = True
            net_sales = net_sales_txs[[CONSUMER_COUNTRY, AMOUNT_IN_EUR]].copy()
            net_sales = net_sales.groupby(CONSUMER_COUNTRY).sum()
            net_sales.reset_index(inplace=True)
            #inplace = true?
            net_sales.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            net_sales['net_sales_country_code'] = location.get_country_iso3(net_sales, CONSUMER_COUNTRY).tolist()
            net_sales['net_sales_country_name'] = location.get_country_name(net_sales, CONSUMER_COUNTRY).tolist()
            net_sales_no_unknown = net_sales[net_sales['net_sales_country_name'] != 'Unknown'].copy()
            net_sales_no_unknown.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            # Sort the list of net sales according to the sorted list of gross sales
            gross_country_list = sales_per_customer_country['gross_sales_country_name_no_unknown']
            # Note that for the net_country_list, we need to apply the "title" function so that it matches with
            # the gross_country_list (to which it has been applied already)
            net_country_list = net_sales_no_unknown['net_sales_country_name'].astype(str).str.title().tolist()
            idx = [gross_country_list.index(country) for country in net_country_list if country in gross_country_list]
            #this needs further explanation
            net_list = [x for _, x in sorted(zip(idx, net_sales_no_unknown[AMOUNT_IN_EUR].tolist()),
                                             key=lambda pair: pair[0])]
            sales_per_customer_country.update({'net_sales_no_unknown': net_list})
            del net_sales

        process_output_file = join(self.process_output_folder, 'out.pickle')

        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(sales_per_customer_country, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return sales_per_customer_country

#already a part for the plotting  the outputs

    def plot(self, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        output_png_filename = join(self.plot_output_folder, 'sales_per_customer_country.png')

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "h",
                    "x": data['gross_sales_no_unknown'][:5],
                    "y": data['gross_sales_country_name_no_unknown'][:5],
                    "text": list(map(lambda x: '{:0,.0f}€'.format(x), data['gross_sales_no_unknown'][:5])),
                    "textposition": "outside",
                    "textfont": {
                        "color":  kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    },
                    "name": "Gross Sales",
                    "marker": {
                        "color":  kwargs['cmap']['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "orientation": "h",
                    "x": data['net_sales_no_unknown'][:5],
                    "y": data['gross_sales_country_name_no_unknown'][:5],
                    "text": list(map(lambda x: '{:0,.0f}€'.format(x), data['net_sales_no_unknown'][:5])),
                    "textposition": "outside",
                    "textfont": {
                        "color":  kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    },
                    "name": "Net Sales",
                    "marker": {
                        "color":  kwargs['cmap']['colors']['accent1']
                    },
                    "cliponaxis": False
                }
            ],
            "layout": {
                "barmode": "group",
                "xaxis": {
                    "type": "linear",
                    "autorange": True,
                    "side": 'bottom',
                    "separatethousands": True,
                    "visible": True,
                    "showticklabels": False,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444"
                },
                "yaxis": {
                    "type": "category",
                    "automargin": True,
                    "autorange": "reversed",
                    "tickfont": {
                        "color":  kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    }
                },
                "autosize": False,
                "bargroupgap": 0.2,
                "bargap": 0.3,
                "legend": {
                    "font": {
                        "color":  kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    },
                    "xanchor": "left",
                    "yanchor": "bottom",
                    "orientation": "h",
                    "y": 0.0,
                    "x": 0.6
                },
                "margin": {
                    "pad": 10,
                    "t": 0,
                    "b": 20,
                    "l": 300,
                    "r": 200
                },
                "height": 480,
                "width": 2000
            }
        }
        pio.write_image(fig, output_png_filename, format='png')

    def report(self, report, styles, *args, **kwargs):

        if 'printTitle' not in kwargs['options']:
            kwargs['options']['printTitle'] = True
        if 'printDescription' not in kwargs['options']:
            kwargs['options']['printDescription'] = True

        if kwargs['options']['printTitle']:
            """" report.append(Paragraph('Top 5 customer country based on gross sales', style=styles['Heading3-NightBlue']))
             report.append(Paragraph('Note that customer countries are known only for guaranteed invoices and cards',
                                     style=styles['Heading3-NightBlue']))
         report.append(Spacer(1, 10))"""
        img = Image(join(self.plot_output_folder, 'sales_per_customer_country.png'),
                    width=500,
                    height=120,
                    hAlign='LEFT')

        Report.draw_images_in_grid(report, [img], row_number=2, total_rows=3)

        Report.draw_text_left(report, 'Customer countries based on gross sales', styles['Heading3-NightBlue'], 25, 362)
