
from wepair.plugins.plugin import Plugin
from wepair.globals import COLNAMES_PE
import pandas as pd
import numpy as np
import inspect
from os.path import join
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
from reportlab.platypus import Image, Table
from datetime import *
from reportlab.lib import colors
from ...utils.location import Location
from ...utils.report import Report
from wepair.utils_common.log import Log

# log
logger = Log(__name__).get_logger()

TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
CUSTOMER_ID = COLNAMES_PE['Customer Unique ID']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']
FIRST_TRANSACTION_DATE = 'first_transaction_date'

SHOP_NAME = COLNAMES_PE['Merchant Account Short Name']
ORG_UNIT = COLNAMES_PE['Organizational Unit']
MERCHANT_NAME = COLNAMES_PE['Merchant Short Name']
SHOP_COUNTRY = COLNAMES_PE['Merchant Country']
SHOP_COUNTRY_NAME = 'SHOP_COUNTRY_NAME'


class RetentionCohorts(Plugin):

    def __init__(self, plugin_folder, id, options=None):
        self.plugin_name = "Retention cohorts"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle', 'customers.pickle']

    def process(self, *args, **kwargs):

        cohort_data = {'has_data': False}

        transactions = args[0]
        customers = args[1]

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

        # Check that all the required columns are present
        necessary_keys = [TRANSACTION_DATE, AMOUNT_IN_EUR, CUSTOMER_ID, TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]

        if group_filter:
            necessary_keys.append(group_filter)

        if not all(key in transactions.columns for key in necessary_keys):
            logger.warning('{fct_name}: necessary keys are missing: {keys}'
                            .format(fct_name=inspect.stack()[0][3],
                                    keys=[key for key in necessary_keys if key not in transactions.columns]))
            return cohort_data

        cohort_data = {'has_data': True, 'cohorts': dict()}

        # Extract the data of interest
        transactions = transactions[necessary_keys]

        # Group by the filter
        list_of_filter = ['no filter']
        if group_filter:
            list_of_filter = transactions[group_filter].unique()

        for filter_idx, filter_value in enumerate(list_of_filter):

            # Split the transaction set into gross sales and sales returns
            if group_filter:
                gross_sales_txs = transactions[transactions[TRANSACTION_IS_CAPTURE]
                                               & (transactions[group_filter] == filter_value)]
            else:
                gross_sales_txs = transactions[transactions[TRANSACTION_IS_CAPTURE]]

            if len(gross_sales_txs) == 0:
                continue

            cohort_data['cohorts'][filter_idx] = dict()
            cohort_data['cohorts'][filter_idx]["filter_value"] = filter_value

            gross_sales_txs = gross_sales_txs[[TRANSACTION_DATE, AMOUNT_IN_EUR, CUSTOMER_ID]].copy()

            cust = customers[[CUSTOMER_ID, FIRST_TRANSACTION_DATE]].copy()

            months = pd.date_range(gross_sales_txs[TRANSACTION_DATE].min().date(),
                                   gross_sales_txs[TRANSACTION_DATE].max().date(),
                                   freq='M')
            gross_sales_txs[TRANSACTION_DATE] = gross_sales_txs[TRANSACTION_DATE].apply(
                lambda x: str(x.month) + '-' + str(x.year))
            cust[FIRST_TRANSACTION_DATE] = cust[FIRST_TRANSACTION_DATE].apply(
                lambda x: str(x.month) + '-' + str(x.year))

            months = [m.to_pydatetime() for m in months]
            months = [str(m.month) + '-' + str(m.year) for m in months]

            for i, month in enumerate(months):
                logger.info('{fct_name}: Computing cohort for the month: {month}'
                             .format(fct_name=inspect.stack()[0][3],
                                     month=month))
                cohort_name = 'M' + str(len(months) - 1 - i)
                first_time_customers = set(cust[cust[FIRST_TRANSACTION_DATE] == month][CUSTOMER_ID].unique()) & \
                                       set(gross_sales_txs[gross_sales_txs[TRANSACTION_DATE] == month][CUSTOMER_ID]
                                           .unique())
                cohort_data['cohorts'][filter_idx][cohort_name] = {
                    'months': [month],
                    'customers': [first_time_customers],
                    'n_customers': len(first_time_customers),
                    'percents': [1.0],
                    'percents_cum': [1.0],
                    'n_customers_per_month': [len(first_time_customers)]
                }
                for next_month in months[i + 1:]:
                    repeat_cust = set(
                        gross_sales_txs[gross_sales_txs[TRANSACTION_DATE] == next_month][CUSTOMER_ID].unique()) & \
                                  first_time_customers
                    cohort_data['cohorts'][filter_idx][cohort_name]['customers'].append(repeat_cust)
                    if len(first_time_customers) == 0:
                        cohort_data['cohorts'][filter_idx][cohort_name]['percents'].append(0)
                    else:
                        cohort_data['cohorts'][filter_idx][cohort_name]['percents'].append(
                            len(repeat_cust) / len(first_time_customers))
                    cohort_data['cohorts'][filter_idx][cohort_name]['n_customers_per_month'].append(len(repeat_cust))
                for j in range(i + 1, len(months)):
                    repeat_cust = set()
                    for k in range(j, len(months)):
                        repeat_cust = repeat_cust | cohort_data['cohorts'][filter_idx][cohort_name]['customers'][k - i]
                    if len(first_time_customers) == 0:
                        cohort_data['cohorts'][filter_idx][cohort_name]['percents_cum'].append(0)
                    else:
                        cohort_data['cohorts'][filter_idx][cohort_name]['percents_cum'].append(
                            len(repeat_cust) / len(first_time_customers))
                del cohort_data['cohorts'][filter_idx][cohort_name]['customers']

        process_output_file = join(self.process_output_folder, 'out.pickle')
        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(cohort_data, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return cohort_data

    def plot(self, *args, **kwargs):

        sns.set()
        sns.set_style("white")

        # Load the data
        input_data_file = join(self.process_output_folder, 'out.pickle')
        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        n_plots = len(data['cohorts'])

        # Plot the normal cohort
        for plot_idx in range(n_plots):

            output_png_filename = join(self.plot_output_folder, 'out_monthly_{idx}.png'.format(idx=plot_idx))

            n_months = len(data['cohorts'][plot_idx].keys()) - 1

            cohort = np.empty((n_months, n_months))
            months = list()
            cohort[:] = np.nan
            for idx, month in enumerate([elem for elem in data['cohorts'][plot_idx].keys() if elem != "filter_value"]):
                months.append(data['cohorts'][plot_idx][month]['months'][0])
                for idx2, percents in enumerate(data['cohorts'][plot_idx][month]['percents']):
                    cohort[idx, idx2] = percents * 100
            cohort = cohort[-13:, :13]

            plt.rcParams['xtick.labeltop'] = True
            plt.rcParams['xtick.labelbottom'] = False
            _, _ = plt.subplots(figsize=(10, 10))

            ax = sns.heatmap(cohort, annot=True, linewidths=1.2, fmt='0,.0f', cbar=False, cmap=kwargs['cmap']['palettes']['blues-cohort-monthly'])
            for t in ax.texts:
                t.set_text(t.get_text() + "%")

            # labels = [datetime.strptime(x, "%m-%Y") for x in months]
            # labels = [datetime.strftime(x, "%b, %Y") for x in labels]
            ax.set_xticklabels(["M+" + str(x) for x in range(13)], rotation='horizontal', fontsize=12)
            ax.set_yticklabels([])
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position('top')

            # Save the results
            plt.savefig(output_png_filename, bbox_inches='tight', dpi=300)
            # plt.show()

        # Plot the cumulative cohort
        for plot_idx in range(n_plots):

            output_png_filename = join(self.plot_output_folder, 'out_cumul_{idx}.png'.format(idx=plot_idx))

            n_months = len(data['cohorts'][plot_idx].keys()) - 1

            cohort = np.empty((n_months, n_months))
            months = list()
            cohort[:] = np.nan
            for idx, month in enumerate([elem for elem in data['cohorts'][plot_idx].keys() if elem != "filter_value"]):
                months.append(data['cohorts'][plot_idx][month]['months'][0])
                for idx2, percents_cum in enumerate(data['cohorts'][plot_idx][month]['percents_cum']):
                    cohort[idx, idx2] = percents_cum * 100
            cohort = cohort[-13:, :13]
            plt.rcParams['xtick.labeltop'] = True
            plt.rcParams['xtick.labelbottom'] = False
            _, _ = plt.subplots(figsize=(10, 10))

            ax = sns.heatmap(cohort, annot=True, linewidths=1.2, fmt='0,.0f', cbar=False, cmap=kwargs['cmap']['palettes']['blues-cohort-cumulative'])
            for t in ax.texts:
                t.set_text(t.get_text() + "%")

            # labels = [datetime.strptime(x, "%m-%Y") for x in months]
            # labels = [datetime.strftime(x, "%b, %Y") for x in labels]
            ax.set_xticklabels(["M+" + str(x) for x in range(13)], rotation='horizontal', fontsize=12)
            ax.set_yticklabels([])
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position('top')

            # Save the results
            plt.savefig(output_png_filename, bbox_inches='tight', dpi=300)
            # plt.show()

        # Plot the number of customer for each month of the cohort
        for plot_idx in range(n_plots):

            output_png_filename = join(self.plot_output_folder, 'out_ncust_{idx}.png'.format(idx=plot_idx))

            n_months = len(data['cohorts'][plot_idx].keys()) - 1

            cohort = np.empty((n_months, n_months))
            months = list()
            cohort[:] = np.nan
            for idx, month in enumerate(
                    [elem for elem in data['cohorts'][plot_idx].keys() if elem != "filter_value"]):
                months.append(data['cohorts'][plot_idx][month]['months'][0])
                for idx2, n_customers_per_month in enumerate(data['cohorts'][plot_idx][month]['n_customers_per_month']):
                    cohort[idx, idx2] = n_customers_per_month
            cohort = cohort[-13:, :13]
            _, _ = plt.subplots(figsize=(10, 10))

            ax = sns.heatmap(cohort, annot=True, linewidths=1.2, fmt='0,.0f', cbar=False, cmap=kwargs['cmap']['palettes']['blues-heatmap'])
            for t in ax.texts:
                t.set_text(t.get_text())

            # labels = [datetime.strptime(x, "%m-%Y") for x in months]
            # labels = [datetime.strftime(x, "%b, %Y") for x in labels]
            ax.set_xticklabels(["M+" + str(x) for x in range(13)], rotation='horizontal', fontsize=35)
            ax.set_yticklabels([])
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position('top')

            # Save the results
            plt.savefig(output_png_filename, bbox_inches='tight', dpi=300)
            # plt.show()

    def report(self, report, styles, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        if 'printMonthlyCohort' in kwargs['options'] and kwargs['options']['printMonthlyCohort']:
            #Report.add_new_page(config=kwargs['config'], doc=report)
            Report.draw_text_right(report, 'RETENTION COHORTS ', styles['Heading2-White'])

            n_plots = len(data['cohorts'])

            # For the monthly cohort
            for plot_idx in range(n_plots):

                if data['cohorts'][plot_idx]["filter_value"] != "no filter":
                    Report.draw_text_right(report, 'Monthly cohorts for {filter}: Percentage of customers '
                                                   'coming back per single month'.format
                    (filter=data['cohorts'][plot_idx]["filter_value"]), styles['Heading3-White'])
                else:
                    Report.draw_text_right(report, 'Absolute cohorts: Percentage of customers coming '
                                                   'back each subsequent month'.format
                    (filter=data['cohorts'][plot_idx]["filter_value"]), styles['Heading3-White'])

                img = Image(join(self.plot_output_folder, 'out_monthly_{idx}.png'.format(idx=plot_idx)),
                            width=410,
                            height=414)

                data_list = list()

                for index, month in enumerate([elem for elem in data['cohorts'][plot_idx].keys()
                                               if elem != "filter_value"]):
                    if month in data['cohorts'][plot_idx]:
                        data_list.append([datetime.strftime(datetime.strptime(
                            data['cohorts'][plot_idx][month]['months'][0], "%m-%Y"), "%b, %y"),
                            "{:,}".format(data['cohorts'][plot_idx][month]['n_customers']), ''])
                data_list = data_list[-13:]
                data_table = [['', '# New cust.', img]] + data_list
                table = Table(data_table, hAlign='CENTER', vAlign='MIDDLE', rowHeights=30)
                table.setStyle(
                    [
                        ('BOX', (1, 1), (1, -1), 0.25, colors.lightgrey), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (1, -1), 'TOP'), ('SPAN', (2, 0), (2, -1)),
                        ('TOPPADDING', (2, 0), (2, -1), 8),
                        ('BOTTOMPADDING', (2, 0), (2, -1), 0), ('ALIGN', (2, 0), (2, -1), 'LEFT')])

                Report.draw_table_left(report, table)

                text = 'This triangular chart shows the absolute cohort retention rate over time.<br/>A cohort is defined ' \
                       'as a group of customers who made their first purchase in the respective month.<br/>Each row shows ' \
                       'one of these monthly cohorts: it first displays the number of customers in the cohort, ' \
                       'followed by the retention rates per single following month (no accumulation with later months).' \
                       '<br/>' \
                       '<br/>' \
                       'Since this graphic focuses on customer retention, only purchases are taken into account and ' \
                       'returns are discarded. This allows to identify returning customers even in case the goods have ' \
                       'been returned.'



                Report.draw_text_right(report, text, styles['Normal-White'])


    # For the cumul cohort

        if 'printCumulativeMonthlyCohort' in kwargs['options'] \
                and kwargs['options']['printCumulativeMonthlyCohort']:

            Report.add_new_page(config=kwargs['config'], doc=report)
            Report.draw_text_right(report, 'RETENTION COHORTS', styles['Heading2-White'])

            for plot_idx in range(n_plots):

                if data['cohorts'][plot_idx]["filter_value"] != "no filter":
                    Report.draw_text_right(report, 'Cumulative cohorts for {filter}: Percentage of customers '
                                                   'coming back every single month'.format(
                        filter=data['cohorts'][plot_idx]["filter_value"]), styles['Heading3-White'])

                else:
                    Report.draw_text_right(report, 'Cumulative cohorts: Percentage of customers '
                                                   'coming back in each or any later month'.format(
                        filter=data['cohorts'][plot_idx]["filter_value"]), styles['Heading3-White'])

                img = Image(join(self.plot_output_folder, 'out_cumul_{idx}.png'.format(idx=plot_idx)),
                            width=410,
                            height=414)

                data_list = list()

                for index, month in enumerate(
                        [elem for elem in data['cohorts'][plot_idx].keys() if elem != "filter_value"]):
                    if month in data['cohorts'][plot_idx]:
                        data_list.append([datetime.strftime(datetime.strptime(
                            data['cohorts'][plot_idx][month]['months'][0], "%m-%Y"), "%b, %y"),
                            "{:,}".format(data['cohorts'][plot_idx][month]['n_customers']), ''])
                data_list = data_list[-13:]
                data_table = [['', '# New cust.', img]] + data_list
                table = Table(data_table, hAlign='CENTER', vAlign='MIDDLE', rowHeights=30)
                table.setStyle(
                    [
                        ('BOX', (1, 1), (1, -1), 0.25, colors.lightgrey), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (1, -1), 'TOP'), ('SPAN', (2, 0), (2, -1)),
                        ('TOPPADDING', (2, 0), (2, -1), 8),
                        ('BOTTOMPADDING', (2, 0), (2, -1), 0), ('ALIGN', (2, 0), (2, -1), 'LEFT')])

                Report.draw_table_left(report, table)

                text = 'This triangular chart shows the cumulative cohort retention rate over time.<br/>A cohort is ' \
                       'defined as a group of customers who made their first purchase in the respective month.<br/>' \
                       'Each row shows one of these monthly cohorts: it first displays the number of customers in ' \
                       'the cohort, followed by the accumulated retention rates over subsequent months in ' \
                       'their customer lifecycle.' \
                       '<br/>' \
                       'It means that customers did either return in the respective month or later in time.' \
                       '<br/>' \
                       '<br/>' \
                       'Since this graphic focuses on customer retention, only purchases are taken into account and ' \
                       'returns are discarded. This allows to identify returning customers even in case the ' \
                       'goods have been returned.'


                Report.draw_text_right(report, text, styles['Normal-White'])


        if 'printMonthlyCohortNbCustomers' in kwargs['options'] \
                and kwargs['options']['printMonthlyCohortNbCustomers']:

            Report.add_new_page(config=kwargs['config'], doc=report)
            Report.draw_text_right(report, 'RETENTION COHORTS', styles['Heading2-White'])

            n_plots = len(data['cohorts'])

            # For the ncust cohort
            for plot_idx in range(n_plots):
                if data['cohorts'][plot_idx]["filter_value"] != "no filter":
                    Report.draw_text_right(report, 'Cohort with number of customers for {filter}'.format(
                        filter=data['cohorts'][plot_idx]["filter_value"]), styles['Heading3-White'], bias=10)
                else:
                    Report.draw_text_right(report, 'Cohort with number of customers'.format(
                        filter=data['cohorts'][plot_idx]["filter_value"]), styles['Heading3-White'], bias=10)

                img = Image(join(self.plot_output_folder, 'out_ncust_{idx}.png'.format(idx=plot_idx)),
                            width=410,
                            height=414)

                data_list = list()

                for index, month in enumerate(
                        [elem for elem in data['cohorts'][plot_idx].keys() if elem != "filter_value"]):
                    if month in data['cohorts'][plot_idx]:
                        data_list.append([datetime.strftime(datetime.strptime(
                            data['cohorts'][plot_idx][month]['months'][0], "%m-%y"), "%b, %y"),
                            "{:,}".format(data['cohorts'][plot_idx][month]['n_customers']), ''])
                data_list = data_list[-13:]
                data_table = [['', '# New cust.', img]] + data_list
                table = Table(data_table, hAlign='CENTER', vAlign='MIDDLE', rowHeights=30)
                table.setStyle(
                    [
                        ('BOX', (1, 1), (1, -1), 0.25, colors.lightgrey), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (1, -1), 'TOP'), ('SPAN', (2, 0), (2, -1)),
                        ('TOPPADDING', (2, 0), (2, -1), 8),
                        ('BOTTOMPADDING', (2, 0), (2, -1), 0), ('ALIGN', (2, 0), (2, -1), 'LEFT')]
                )
                Report.draw_table_left(report, table)

                text = 'This triangular chart shows the cohort retention rate over time. ' \
                       'We define a cohort as a group of customers who made their first purchase in the same ' \
                       'month. Each row shows one of these monthly cohorts: it first displays the number of ' \
                       'customers in the cohort, followed by the number of retained customers over subsequent ' \
                       'months in ' \
                       'their purchase lifecycle. Since this graphic ' \
                       'focuses on customers retention, we look only at the purchases and discard all the ' \
                       'returns. This way we identify the returning customers, even if they eventually ' \
                       'return all the goods that they purchased.'

                Report.draw_text_right(report, text, styles['Normal-White'])
