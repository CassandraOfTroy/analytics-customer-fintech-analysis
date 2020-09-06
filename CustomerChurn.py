#this is a part for CUSTOMER CHURN within WEP-AIR
#importing libraries for the module 
from wepair.plugins.plugin import Plugin
from wepair.globals import COLNAMES_PE
import pandas as pd
import inspect
from os.path import join
import pickle
from reportlab.platypus import Paragraph, Spacer, Image, Table, PageBreak
from datetime import *
from reportlab.lib import colors
from ...utils.location import Location
from ...utils.customer_tools import Feature, identify_customers, add_feature
import plotly.io as pio
import plotly.graph_objs as go
from wepair.utils_common.log import Log

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'


#creating a variables from the data frame
TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
CUSTOMER_ID = COLNAMES_PE['Customer Unique ID']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']
FIRST_TRANSACTION_DATE = 'first_transaction_date'
LAST_TRANSACTION_DATE = 'last_transaction_date'


SHOP_NAME = COLNAMES_PE['Merchant Account Short Name']
ORG_UNIT = COLNAMES_PE['Organizational Unit']
MERCHANT_NAME = COLNAMES_PE['Merchant Short Name']
SHOP_COUNTRY = COLNAMES_PE['Merchant Country']
SHOP_COUNTRY_NAME = 'SHOP_COUNTRY_NAME'


class ChurnRate(Plugin):

    def __init__(self, plugin_folder, id, options=None):
        self.plugin_name = "Churn Rate"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle', 'customers.pickle']


#The special syntax *args in function definitions in python is used to pass a variable number of arguments to a function. 
#It is used to pass a non-keyworded, variable-length argument list.
#The syntax is to use the symbol * to take in a variable number of arguments; by convention, it is often used with the word args.
#What *args allows you to do is take in more arguments than the number of formal arguments that you previously defined. 
#With *args, any number of extra arguments can be tacked on to your current formal parameters (including zero extra arguments).
        
#The special syntax **kwargs in function definitions in python is used to pass a keyworded, variable-length argument list. 
#We use the name kwargs with the double star. 
#The reason is because the double star allows us to pass through keyword arguments (and any number of them).
        
    def process(self, *args, **kwargs):
  #initialization of the variable churn_data
        churn_data = {'has_data': False}

        transactions = args[0]

#passing values to the group filter - in case that the  filter is chosen for the account name, org unit, merch name, etc...
        group_filter = None
        if 'filter' in self.options:
            if self.options['filter'] == 'account name':
                group_filter = SHOP_NAME
            elif self.options['filter'] == 'org unit':
                group_filter = ORG_UNIT
            elif self.options['filter'] == 'merchant name':
                group_filter = MERCHANT_NAME
            elif self.options['filter'] == 'shop country name':
                group_filter = SHOP_COUNTRY_NAME
                location = Location(self.options['assets'])
                transactions['country_code'] = transactions[SHOP_COUNTRY].apply(location.get_country_iso3)
                transactions[SHOP_COUNTRY_NAME] = transactions[SHOP_COUNTRY].apply(location.get_country_name)
            else:
                logger.warning('unknown filter option')

#below are ncessary keys to create an output
        # Check that all the required columns are present
        necessary_keys = [TRANSACTION_DATE, AMOUNT_IN_EUR, CUSTOMER_ID, TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]
#this step is for additional application of the filters
        if group_filter:
            necessary_keys.append(group_filter)

        if not all(key in transactions.columns for key in necessary_keys):
            logger.warning('{fct_name}: necessary keys are missing: {keys}'
                            .format(fct_name=inspect.stack()[0][3],
                                    keys=[key for key in necessary_keys if key not in transactions.columns]))
            return churn_data
#returning the churn data based on the selected filters and necessary keys
# The dict() function creates a dictionary.
#A dictionary is a collection which is unordered, changeable and indexed
            
        churn_data = {'has_data': True, 'filter_values': dict()}

        # Group by the filter
        # create variable and pass the no filter value
        # variable below is used for the 
        list_of_filter = ['no filter']
        if group_filter:
            list_of_filter = transactions[group_filter].unique()

        for filter_idx, filter_value in enumerate(list_of_filter):

            print("Now processing: ", filter_value)

            if group_filter:
                txs = transactions[transactions[TRANSACTION_IS_CAPTURE] & (transactions[group_filter] == filter_value)]
            else:
                txs = transactions[transactions[TRANSACTION_IS_CAPTURE]]

            if len(txs) == 0:
                continue
            customers, txs = identify_customers(txs)
            customers = add_feature(customers, txs, Feature.ALL, end_period=txs[TRANSACTION_DATE].max())

            # Extract the data of interest
            txs = txs[necessary_keys]

            cust = customers[[CUSTOMER_ID, FIRST_TRANSACTION_DATE, LAST_TRANSACTION_DATE]].copy()
            start = datetime.date(datetime(2017, 6, 1))
            end = datetime.date(datetime(2018, 7, 1))
            months = pd.date_range(start, end, freq='M')

            churn_rates = list()
            prev = start
            for i, _ in enumerate(months):
                if set(txs[txs[TRANSACTION_DATE] < months[i]][CUSTOMER_ID].unique()) & set(cust[cust[LAST_TRANSACTION_DATE] > months[i]][CUSTOMER_ID]):
                    churn_rates.append(len(set(cust[(cust[LAST_TRANSACTION_DATE] <= months[i]) & (cust[LAST_TRANSACTION_DATE] > prev)][CUSTOMER_ID]) & set(cust[cust[FIRST_TRANSACTION_DATE] < prev][CUSTOMER_ID])) / len(set(txs[txs[TRANSACTION_DATE] < months[i]][CUSTOMER_ID].unique()) & set(cust[cust[LAST_TRANSACTION_DATE] > months[i]][CUSTOMER_ID])))
                else:
                    churn_rates.append(0)
                prev = months[i]
            churn_data['filter_values'][filter_idx] = dict()
            churn_data['filter_values'][filter_idx]["filter_value"] = filter_value
            churn_data['filter_values'][filter_idx]['months'] = [str(m.month) + '-' + str(m.year) for m in months]
            churn_data['filter_values'][filter_idx]['churn_rates'] = churn_rates

        process_output_file = join(self.process_output_folder, 'out.pickle')
        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(churn_data, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return churn_data
    
#plotting the data to the output file
    def plot(self, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')
        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        mycolors = ['#000000', '#00FF00', '#0000FF', '#FF0000', '#01FFFE', '#FFA6FE', '#FFDB66', '#006401', '#010067',
                    '#95003A', '#007DB5', '#FF00F6', '#FFEEE8', '#774D00', '#90FB92', '#0076FF', '#D5FF00', '#FF937E',
                    '#6A826C', '#FF029D', '#FE8900', '#7A4782', '#7E2DD2', '#85A900', '#FF0056', '#A42400', '#00AE7E',
                    '#683D3B', '#BDC6FF', '#263400', '#BDD393', '#00B917', '#9E008E', '#001544', '#C28C9F', '#FF74A3',
                    '#01D0FF', '#004754', '#E56FFE', '#788231', '#0E4CA1', '#91D0CB', '#BE9970', '#968AE8', '#BB8800',
                    '#43002C', '#DEFF74', '#00FFC6', '#FFE502', '#620E00', '#008F9C', '#98FF52', '#7544B1', '#B500FF',
                    '#00FF78', '#FF6E41', '#005F39', '#6B6882', '#5FAD4E', '#A75740', '#A5FFD2', '#FFB167', '#009BFF',
                    '#E85EBE']




        plot_data = list()
        for i in data['filter_values']:
            if ('values' in kwargs['options']) and (data['filter_values'][i]['filter_value']
                                                    not in kwargs['options']['values']):
                continue
            else:
                plot_data.append(go.Scatter(
                    x=data['filter_values'][i]['months'][1:-1],
                    y=data['filter_values'][i]['churn_rates'][1:-1],
                    line=dict(
                        color=(mycolors[i])
                    ),
                    mode='lines',
                    name=data['filter_values'][i]['filter_value']
                ))
        layout = go.Layout(
            height=1080,
            width=1920,
            yaxis=dict(
                range=[0, 0.4],
                tickformat=',.0%'
            ),
            legend=dict(
                font=dict(
                    size=10
                )
            )
        )
        fig = dict(data=plot_data, layout=layout)

        output_png_filename = join(self.plot_output_folder, 'churn_rates.png')
        pio.write_image(fig, output_png_filename, format='png', scale=4)


#creating a report
    def report(self, report, styles, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        report.append(Paragraph('RETENTION COHORTS (Gross Sales)', style=styles['Heading2']))
        report.append(Paragraph('Retention rate of new customers', style=styles['Heading3-NightBlue']))

        n_plots = len(data['cohorts'])

        for plot_idx in range(n_plots):

            report.append(Paragraph('Cohort for {filter}'.format(filter=data['cohorts'][plot_idx]["filter_value"]),
                                    style=styles['Heading3-NightBlue']))

            img = Image(join(self.plot_output_folder, 'out_{idx}.png'.format(idx=plot_idx)),
                        width=320,
                        height=275)

            data_list = list()
            for index, month in enumerate(
                    [elem for elem in data['cohorts'][plot_idx].keys() if elem != "filter_value"]):
                if index < 13:
                    data_list.append([datetime.strftime(datetime.strptime(
                        data['cohorts'][plot_idx][month]['months'][0], "%m-%Y"), "%b, %Y"),
                        "{:,}".format(data['cohorts'][plot_idx][month]['n_customers']), ''])
            data_table = [['', '# New cust.', img]] + data_list
            table = Table(data_table, hAlign='CENTER', vAlign='MIDDLE')
            table.setStyle(
                [
                    ('BOX', (1, 1), (1, -1), 0.25, colors.lightgrey), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (1, -1), 'TOP'), ('SPAN', (2, 0), (2, -1)), ('TOPPADDING', (2, 0), (2, -1), 8),
                    ('BOTTOMPADDING', (2, 0), (2, -1), 0), ('ALIGN', (2, 0), (2, -1), 'LEFT')])

            report.append(table)
            report.append(Spacer(1, 20))
            report.append(
                Paragraph('<b>Description:</b> This triangular chart shows the cohort retention rate over time. '
                          'We define a cohort as a group of customers who made their first purchase in the same '
                          'month. Each row shows one of these monthly cohorts: it first displays the number of '
                          'customers in the cohort, followed by the retention rates over subsequent months in '
                          'their purchase lifecycle. Since this graphic '
                          'focuses on customers retention, we look only at the purchases and discard all the '
                          'returns. This way we identify the returning customers, even if they eventually '
                          'return all the goods that they purchased.',
                          style=styles['Normal']))

            report.append(PageBreak())
