# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 16:02:04 2019

@author: marina.tosic
"""

from wepair.plugins.plugin import Plugin
from ...globals import COLNAMES_PE
import pandas as pd
import pickle
from os.path import join
import numpy as np
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
CUSTOMER_ID = COLNAMES_PE['Customer Unique ID']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']


class NewAndReturningCustomers(Plugin):

    def __init__(self, plugin_folder, id, options=None):
        self.plugin_name = "New and Returning Customers"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle']

    def process(self, *args, **kwargs):

        new_and_returning_customers_over_time = {'has_data': False}
        args = list(args)
        logger.debug(kwargs)

        if len(args) < 1:
            logger.warning('Fatal Error: Plugin FPS KPIs: FPS Transactional data Missing')
            return new_and_returning_customers_over_time

        transactions = args[0]

        # Check that all the required columns are present
        necessary_keys = [TRANSACTION_DATE, CUSTOMER_ID, TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]
        if not all(key in transactions.columns for key in necessary_keys):
            logger.warning('{fct_name}: necessary keys are missing: {keys}'
                            .format(fct_name=inspect.stack()[0][3],
                                    keys=[key for key in necessary_keys if key not in transactions.columns]))
            return new_and_returning_customers_over_time

        # Extract the data of interest
        transactions = transactions[[TRANSACTION_DATE, CUSTOMER_ID, TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]]
        # Split the transaction set into gross sales and sales returns
        gross_sales_txs = transactions[transactions[TRANSACTION_IS_CAPTURE]].copy()

        gross_sales_txs = gross_sales_txs[[TRANSACTION_DATE, CUSTOMER_ID]].copy()
        gross_sales_txs = gross_sales_txs.astype({TRANSACTION_DATE: np.str, CUSTOMER_ID: np.str})
        gross_sales_txs[TRANSACTION_DATE] = pd.to_datetime(gross_sales_txs[TRANSACTION_DATE],
                                                           format="%Y-%m-%d %H:%M:%S").apply(lambda x: x.date())
        gross_sales_txs['month_year'] = gross_sales_txs[TRANSACTION_DATE].values.astype('datetime64[M]')
        gross_sales_txs.drop(TRANSACTION_DATE, axis=1, inplace=True)

        # sorting txs by date and name
        gross_sales_txs.sort_values(by=[CUSTOMER_ID, 'month_year'], ascending=[True, True], inplace=True)
        gross_sales_txs = gross_sales_txs.sort_values(by=[CUSTOMER_ID, 'month_year'], ascending=[True, True]) \
            .drop_duplicates(subset=[CUSTOMER_ID, 'month_year'], keep='first')

        # new vs returning customers
        customers = gross_sales_txs.groupby([CUSTOMER_ID, 'month_year'], sort=False).head()
        customers['cumcount'] = pd.DataFrame(customers.groupby(CUSTOMER_ID).cumcount())

        # calculating new vs returning customer count per month
        new_cust = customers[customers['cumcount'] == 0]
        ret_cust = customers[customers['cumcount'] > 0]

        new_cust_cpm = new_cust.groupby(['month_year'], sort=False)[CUSTOMER_ID].agg(['count']) \
            .reset_index() \
            .sort_values(by=['month_year'], ascending=True)
        ret_cust_cpm = ret_cust.groupby(['month_year'], sort=False)[CUSTOMER_ID].agg(['count']) \
            .reset_index() \
            .sort_values(by=['month_year'], ascending=True)
        cust_cpm = customers.groupby(['month_year'], sort=False)[CUSTOMER_ID].agg(['count']) \
            .reset_index() \
            .sort_values(by=['month_year'], ascending=True)

        new_and_returning_customers_over_time = {
            'has_data': True,
            'new_customers': {
                'month_year': new_cust_cpm['month_year'].apply(lambda x: x.strftime('%b-%y')).tolist(),
                'n_customers': new_cust_cpm['count'].astype(int).tolist()
            },
            'returning_customers': {
                'month_year': ret_cust_cpm['month_year'].apply(lambda x: x.strftime('%b-%y')).tolist(),
                'n_customers': ret_cust_cpm['count'].astype(int).tolist()
            },
            'total_customers': {
                'month_year': cust_cpm['month_year'].apply(lambda x: x.strftime('%b-%y')).tolist(),
                'n_customers': cust_cpm['count'].astype(int).tolist()
            }
        }

        # Pad the list of returning customers with 0's for the first dates
        if len(new_and_returning_customers_over_time['returning_customers']['month_year']) == 0:
            new_and_returning_customers_over_time['returning_customers']['month_year'] = \
                new_and_returning_customers_over_time['new_customers']['month_year']
            new_and_returning_customers_over_time['returning_customers']['n_customers'] = \
                ([0] * len(new_and_returning_customers_over_time['new_customers']['n_customers']))
        else:
            idx = 0
            for idx, date in enumerate(new_and_returning_customers_over_time['new_customers']['month_year']):
                if new_and_returning_customers_over_time['returning_customers']['month_year'][0] == date:
                    break
            if idx > 0:
                new_and_returning_customers_over_time['returning_customers']['month_year'] = \
                    new_and_returning_customers_over_time['new_customers']['month_year'][0:idx] \
                    + new_and_returning_customers_over_time['returning_customers']['month_year']
                new_and_returning_customers_over_time['returning_customers']['n_customers'] = \
                    ([0] * idx) + new_and_returning_customers_over_time['returning_customers']['n_customers']

        process_output_file = join(self.process_output_folder, 'out.pickle')

        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(new_and_returning_customers_over_time, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return new_and_returning_customers_over_time

    def plot(self, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        output_png_filename = join(self.plot_output_folder, 'new_returning_customers.png')

        df = pd.DataFrame()
        df['y_new'] = data['new_customers']['n_customers']
        df['y_ret'] = data['returning_customers']['n_customers']
        df['y_tot'] = data['total_customers']['n_customers']
        df['x'] = data['new_customers']['month_year']
        df['y_new_perc'] = df['y_new'] / df['y_tot'] * 100.0
        df['y_ret_perc'] = df['y_ret'] / df['y_tot'] * 100.0

        fig = {
            "data": [
                {
                    "type": "bar",
                    "x": data['new_customers']['month_year'],
                    "y": df['y_new_perc'],
                    "text": list(map(lambda x: '{:0,.0f}%'.format(x), df['y_new_perc'])),
                    "textposition": "inside",
                    "textfont": {
                        "size": 20,
                        "color": "#ffffff"
                    },
                    "name": "New customers",
                    "marker": {
                        "color": kwargs['cmap']['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "x": data['new_customers']['month_year'],
                    "y": df['y_ret_perc'],
                    "name": "Returning customers",
                    "marker": {
                        "color": kwargs['cmap']['colors']['accent1']
                    },
                    "cliponaxis": False
                }
            ],
            "layout": {
                "barmode": "stack",
                "xaxis": {
                    "type": "category",
                    "autorange": True,
                    "side": 'bottom',
                    "visible": True,
                    "tickangle": -45,
                    "showticklabels": True,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444",
                    "ticklen": 5,
                    "tickwidth": 1,
                    "tickfont": {
                        "size": 20
                    }
                },
                "yaxis": {
                    "type": "linear",
                    "title": "Percentage of customers",
                    "titlefont": {
                        "size": 20},
                    "automargin": True,
                    "tickfont": {
                        "size": 20
                    },
                    "ticksuffix": '%'
                },
                "legend": {
                    "font": {
                        "color": kwargs['cmap']['colors']['night blue'],
                        "size": 20
                    },
                    "xanchor": "center",
                    "yanchor": "top",
                    "orientation": "h",
                    "y": -0.2,
                    "x": 0.5
                },
                "margin": {
                    "pad": 10,
                    "t": 0,
                    "b": 100,
                    "l": 100,
                    "r": 100
                },
                "width": 1000,
                "height": 1000
            }
        }

        pio.write_image(fig, output_png_filename, format='png', scale=2)


        """
        df = pd.DataFrame()
        df['y_new'] = data['new_customers']['n_customers']
        df['y_ret'] = data['returning_customers']['n_customers']
        df['y_tot'] = data['total_customers']['n_customers']
        df['x'] = data['new_customers']['month_year']
        df['y_new_perc'] = df['y_new']/df['y_tot']*100.0
        df['y_ret_perc'] = df['y_ret'] / df['y_tot'] * 100.0
        df = df.tail(6)

        bar_width = 0.3
        fig, ax = plt.subplots(figsize=(18, 10))
        ax.yaxis.grid()  # grid lines
        ax.set_axisbelow(True)  # grid lines are behind the rest

        ind = np.arange(len(df['x']))
        p1 = plt.bar(ind, df['y_new_perc'], bar_width, color='#003366')
        p2 = plt.bar(ind, df['y_ret_perc'], bar_width, color='#009999', bottom=df['y_new_perc'])

        formatter = FuncFormatter(lambda y, pos: "%d%%" % (y))
        ax.yaxis.set_major_formatter(formatter)
        plt.ylabel('Percentage', fontdict={'fontsize': 32})
        plt.xticks(ind, df['x'])
        plt.legend((p1[0], p2[0]), ('New customers', 'Returning customers'), loc="best", fontsize=24, bbox_to_anchor=(0.5, -0.05))
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        plt.tick_params(axis='both', which='major', labelsize=24)

        i = 0
        for rect in p1:
            cnt_cust = df.iloc[i]['y_tot']
            plt.text(rect.get_x() + rect.get_width() / 2.0, 100, cnt_cust, fontsize=24, ha='center', va='bottom')
            i = i + 1

        i = 0
        for rect in p1:
            y_new_perc = df.iloc[i]['y_new_perc']
            plt.text(rect.get_x() + rect.get_width() / 2.0, y_new_perc/2, "{0:.2f}".format(y_new_perc) + '%', color='white', fontsize=12, ha='center', va='bottom')
            i = i + 1

        i = 0
        for rect in p2:
            y_ret_perc = df.iloc[i]['y_ret_perc']
            y_new_perc = df.iloc[i]['y_new_perc']
            plt.text(rect.get_x() + rect.get_width() / 2.0, y_new_perc + y_ret_perc / 2, "{0:.2f}".format(y_ret_perc) +
                     '%', color='white', fontsize=12,
                     ha='center', va='bottom')
            i = i + 1

        # Save the results
        plt.savefig(output_png_filename, bbox_inches='tight', dpi=300)

        """

    def report(self, report, styles, *args, **kwargs):

        Report.draw_text_right(report, 'CUSTOMER INSIGHTS', styles['Heading2-White'])

        Report.draw_text_right(report, 'Percentage of returning and new customers per month', styles['Heading3-White'])

        img = Image(join(self.plot_output_folder, 'new_returning_customers.png'),
                    width=450,
                    height=450)
        Report.draw_image_left(report, img)

        text = 'New customers are customers who have not purchased before. ' \
               'Returning customers are customers who have purchased at least once in a ' \
               'previous month. This graphic focuses on customer ' \
               'retention, so it considers only purchases and discards any returns.'

        Report.draw_text_right(report, text, styles['Normal-White'])

